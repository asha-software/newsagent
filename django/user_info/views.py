from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.core.exceptions import ValidationError
from .models import UserTool, APIKey, SharedSearchResult
from .forms import UserToolForm
from .utils import get_builtin_tools
import json
import uuid

def signin(request): 
    if request.user.is_authenticated:
        return redirect('search')  # Redirect to search page if already logged in
    if request.method == 'POST':
        username = request.POST.get('user_name')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('search')  # Redirect to search page after login
        else:
            return render(request, 'signin.html', {'error': 'Invalid username or password.'})

    return render(request, 'signin.html')

def home(request):
    if request.user.is_authenticated:
        return redirect('search')  # Redirect to search page if already logged in
    return render(request, 'signin.html')  # Render the signin page

def logout_view(request):
    logout(request)
    return redirect('home')  # Redirect to home page after logout

def register(request):
    if request.user.is_authenticated:
        return redirect('search')  # Redirect to search page if already logged in
    
    if request.method == 'POST':
        username = request.POST.get('user_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error': 'Username already exists.'})
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'Email already exists.'})
        
        # Create new user
        user = User.objects.create_user(username=username, email=email, password=password)
        
        # Redirect to signin page with success message
        return render(request, 'signin.html', {'success': 'Account created successfully! Please sign in.'})
    
    return render(request, 'signup.html')  # Render the signup page

@login_required
def search(request):
    show_results = False
    
    if request.method == 'POST':
        # Get the search query
        query = request.POST.get('search')
        
        # If any query is submitted, show the results section
        if query:
            show_results = True
    
    # Get the user's active tools
    user_tools = UserTool.objects.filter(user=request.user, is_active=True).order_by('name')
    
    # Get the built-in tools
    builtin_tools = get_builtin_tools()
    
    
    # Pass API_URL from settings to the template
    context = {
        'show_results': show_results,
        'API_URL': settings.API_URL,
        'user_tools': user_tools,
        'builtin_tools': builtin_tools
    }
        
    return render(request, 'search.html', context)  # Render the search page with context

def shared_search_result(request, result_id):
    try:
        # Try to get the shared result by ID
        shared_result = get_object_or_404(SharedSearchResult, id=result_id)
        
        # Check if the result is public or if the user is the owner
        if not shared_result.is_public and (not request.user.is_authenticated or request.user != shared_result.user):
            raise Http404("This shared result is not public")
        
        # Get the built-in tools (for the search form)
        builtin_tools = get_builtin_tools()
        
        # If user is authenticated, get their tools
        user_tools = None
        if request.user.is_authenticated:
            user_tools = UserTool.objects.filter(user=request.user, is_active=True).order_by('name')
        
        # Double serialize the result data to match the JavaScript's expectation
        # The JavaScript code expects a JSON string containing another JSON string
        serialized_result_data = json.dumps(json.dumps(shared_result.result_data))
        
        # Create a modified shared result object with the serialized data
        shared_result_dict = {
            'id': str(shared_result.id),
            'query': shared_result.query,
            'result_data': serialized_result_data,
            'created_at': shared_result.created_at,
            'is_public': shared_result.is_public
        }
        
        # Prepare context for the template
        context = {
            'API_URL': settings.API_URL,
            'shared_result': shared_result_dict,
            'builtin_tools': builtin_tools,
            'user_tools': user_tools,
            'is_shared_view': True
        }
        
        return render(request, 'search.html', context)
    
    except (ValueError, Http404):
        # Handle invalid UUID or not found
        if request.user.is_authenticated:
            return redirect('search')
        else:
            return redirect('signin')

@login_required
def save_shared_result(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query', '')
            result_data = data.get('result_data', {})
            is_public = data.get('is_public', False)
            
            # Check if a shared result already exists for this user and query
            existing_result = SharedSearchResult.objects.filter(
                user=request.user,
                query=query
            ).first()
            
            if existing_result:
                # Update the existing result if needed
                if existing_result.is_public != is_public:
                    existing_result.is_public = is_public
                    existing_result.save()
                
                # Return the URL for the existing shared result
                return JsonResponse({
                    'success': True,
                    'shared_url': f"/search/{existing_result.id}",
                    'message': 'Existing shared link retrieved!'
                })
            else:
                # Create a new shared result
                shared_result = SharedSearchResult(
                    user=request.user,
                    query=query,
                    result_data=result_data,
                    is_public=is_public
                )
                shared_result.save()
                
                # Return the URL for the new shared result
                return JsonResponse({
                    'success': True,
                    'shared_url': f"/search/{shared_result.id}",
                    'message': 'New shared link created!'
                })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error saving result: {str(e)}'
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=405)

def forgot_password_view(request):
    return render(request, 'forgot.html')  # Render the forgot password page

# Tool views
def validate_tool_name(user, tool_name):
    # Check for collision with built-in tools
    builtin_tools = ["wikipedia", "web_search", "calculator", "wolframalpha"]
    if tool_name in builtin_tools:
        raise ValidationError(f"The tool name '{tool_name}' is reserved for built-in tools.")

    # Check for collision with user's existing tools
    if UserTool.objects.filter(user=user, name=tool_name).exists():
        raise ValidationError(f"You already have a tool named '{tool_name}'. Please choose a different name.")

@login_required
def tool_list(request):
    tools = UserTool.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'user_info/tool_list.html', {'tools': tools})

@login_required
def tool_create(request):
    if request.method == 'POST':
        form = UserToolForm(request.POST)
        if form.is_valid():
            tool = form.save(commit=False)
            tool.user = request.user

            # Validate the tool name
            try:
                validate_tool_name(request.user, tool.name)
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('tool_create')

            tool.save()
            messages.success(request, f"Tool '{tool.name}' created successfully!")
            return redirect('tool_list')
    else:
        form = UserToolForm()

    return render(request, 'user_info/tool_form.html', {
        'form': form,
        'title': 'Create New Tool'
    })

@login_required
def tool_edit(request, tool_id):
    tool = get_object_or_404(UserTool, id=tool_id, user=request.user)

    if request.method == 'POST':
        form = UserToolForm(request.POST, instance=tool)
        if form.is_valid():
            updated_tool = form.save(commit=False)

            # Validate the updated tool name
            try:
                if updated_tool.name != tool.name:  # Only validate if the name is being changed
                    validate_tool_name(request.user, updated_tool.name)
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('tool_edit', tool_id=tool_id)

            updated_tool.save()
            messages.success(request, f"Tool '{updated_tool.name}' updated successfully!")
            return redirect('tool_list')
    else:
        # Convert JSON fields to strings for the form
        initial_data = {
            field: json.dumps(getattr(tool, field), indent=2) if getattr(tool, field) else ''
            for field in ['headers', 'default_params', 'data', 'json_payload', 'target_fields', 'param_mapping']
        }
        form = UserToolForm(instance=tool, initial=initial_data)

    return render(request, 'user_info/tool_form.html', {
        'form': form,
        'tool': tool,
        'title': f"Edit Tool: {tool.name}"
    })

@login_required
def tool_delete(request, tool_id):
    tool = get_object_or_404(UserTool, id=tool_id, user=request.user)
    
    if request.method == 'POST':
        tool_name = tool.name
        tool.delete()
        messages.success(request, f"Tool '{tool_name}' deleted successfully!")
        return redirect('tool_list')
    
    return render(request, 'user_info/tool_confirm_delete.html', {'tool': tool})

# API Key views
@login_required
def apikey_list(request):
    apikeys = APIKey.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'user_info/apikey_list.html', {'apikeys': apikeys})

@login_required
def apikey_create(request):
    if request.method == 'POST':
        # Check if the user already has 3 or more API keys
        existing_keys_count = APIKey.objects.filter(user=request.user).count()
        if existing_keys_count >= 3:
            messages.error(request, "You can only have a maximum of 3 API keys per account.")
            return redirect('apikey_list')
            
        # Generate a name with a timestamp to make it unique
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        name = f"API Key - {timestamp}"
        
        # Create a new API key
        apikey = APIKey(user=request.user, name=name)
        apikey.save()
        
        messages.success(request, f"API key created successfully!")
        return redirect('apikey_list')
    
    # If not a POST request, redirect to the list view
    return redirect('apikey_list')

@login_required
def apikey_delete(request, apikey_id):
    apikey = get_object_or_404(APIKey, id=apikey_id, user=request.user)
    
    if request.method == 'POST':
        apikey_name = apikey.name
        apikey.delete()
        messages.success(request, f"API key '{apikey_name}' deleted successfully!")
        return redirect('apikey_list')
    
    return render(request, 'user_info/apikey_confirm_delete.html', {'apikey': apikey})

@login_required
def get_api_key(request):
    """
    Returns the current user's API key.
    This endpoint is used by the FastAPI backend to authenticate users.
    """
    # Get the user's first active API key
    api_key = APIKey.objects.filter(user=request.user, is_active=True).first()
    
    if not api_key:
        # Check if the user already has 3 or more API keys (including inactive ones)
        existing_keys_count = APIKey.objects.filter(user=request.user).count()
        if existing_keys_count >= 3:
            # If the user has reached the limit, return an error
            return JsonResponse({
                'error': 'You have reached the maximum limit of 3 API keys. Please delete an existing key before creating a new one.'
            }, status=400)
        
        # Create a new API key
        api_key = APIKey(user=request.user, name="Auto-generated API Key")
        api_key.save()
    
    return JsonResponse({
        'api_key': api_key.key,
        'username': request.user.username
    })
