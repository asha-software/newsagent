from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from .models import UserTool, APIKey, SharedSearchResult
from .forms import UserToolForm
from .utils import get_builtin_tools
import json
import requests

# Helper functions for API operations
def get_user_api_key(request, redirect_url=None, redirect_kwargs=None):
    """
    Get the user's active API key.
    Returns (api_key, error_response)
    If there's an error, api_key will be None and error_response will be a redirect response.
    """
    api_key = APIKey.objects.filter(user=request.user, is_active=True).first()
    if not api_key:
        messages.error(request, "No active API key found. Please create an API key first.")
        if redirect_kwargs:
            return None, redirect(redirect_url, **redirect_kwargs)
        else:
            return None, redirect(redirect_url)
    return api_key, None

def prepare_tool_data_from_form(form):
    """
    Extract tool data from a form.
    """
    # Ensure param_mapping is a valid dictionary (not None)
    param_mapping = form.cleaned_data.get('param_mapping', {})
    if param_mapping is None:
        param_mapping = {}
    
    return {
        'name': form.cleaned_data['name'],
        'description': form.cleaned_data['description'],
        'method': form.cleaned_data['method'],
        'url_template': form.cleaned_data['url_template'],
        'headers': form.cleaned_data['headers'],
        'default_params': form.cleaned_data['default_params'],
        'data': form.cleaned_data['data'],
        'json_payload': form.cleaned_data['json_payload'],
        'docstring': form.cleaned_data['docstring'],
        'target_fields': form.cleaned_data['target_fields'],
        'param_mapping': param_mapping,
        'is_active': form.cleaned_data['is_active'],
        'is_preferred': form.cleaned_data['is_preferred']
    }

def api_request(method, endpoint, api_key, json_data=None):
    """
    Make an API request to the FastAPI backend.
    Returns (success, response_or_error)
    """
    url = f"{settings.API_URL}{endpoint}"
    headers = {'X-API-Key': api_key.key}
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, json=json_data, headers=headers)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            return False, f"Unsupported method: {method}"
        
        if response.status_code in [200, 201]:
            return True, response
        else:
            # Try to get the error detail from the response
            try:
                error_data = response.json()
                # Check if the error is about a duplicate tool name
                if response.status_code == 400 and 'detail' in error_data:
                    if 'already exists' in error_data['detail']:
                        return False, f"A tool with this name already exists."
                    else:
                        return False, error_data['detail']
                else:
                    return False, str(error_data)
            except Exception:
                return False, f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return False, str(e)

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
    shared_result = None
    has_cached_result = False
    
    if request.method == 'POST':
        # Get the search query
        query = request.POST.get('search')
        
        # If any query is submitted, show the results section
        if query:
            show_results = True
            
            # Check if this query already exists in the database
            existing_result = SharedSearchResult.objects.filter(
                user=request.user,
                query=query
            ).first()
            
            if existing_result:
                # If the query exists, use the cached result
                serialized_result_data = json.dumps(json.dumps(existing_result.result_data))
                
                # Create a modified shared result object with the serialized data
                shared_result = {
                    'id': str(existing_result.id),
                    'query': existing_result.query,
                    'result_data': serialized_result_data,
                    'created_at': existing_result.created_at,
                    'is_public': existing_result.is_public
                }
                
                # Set flag to indicate we have a cached result
                has_cached_result = True
                
                
                # If this is an AJAX request, return the cached result as JSON
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'has_cached_result': True,
                        'shared_result': shared_result
                    })
                
    # If this is an AJAX request but no cached result was found, return a JSON response
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'has_cached_result': False
        })
    
    # Get the user's active tools
    user_tools = UserTool.objects.filter(user=request.user, is_active=True).order_by('name')
    
    # Get the built-in tools
    builtin_tools = get_builtin_tools()
    
    # Pass API_URL from settings to the template
    context = {
        'show_results': show_results,
        'API_URL': settings.API_URL,
        'user_tools': user_tools,
        'builtin_tools': builtin_tools,
        'has_cached_result': has_cached_result
    }
    
    # If we have a cached result, add it to the context
    if shared_result:
        context['shared_result'] = shared_result
        context['is_shared_view'] = True
        
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
@login_required
def tool_list(request):
    tools = UserTool.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'user_info/tool_list.html', {'tools': tools})

@login_required
def tool_create(request):
    if request.method == 'POST':
        form = UserToolForm(request.POST)
        if form.is_valid():
            # Get the user's API key
            api_key, error_response = get_user_api_key(request, 'tool_create')
            if error_response:
                return error_response
            
            # Prepare the tool data
            tool_data = prepare_tool_data_from_form(form)
            
            # Make API call to create tool
            success, result = api_request('POST', '/tools/custom', api_key, tool_data)
            
            if success:
                messages.success(request, f"Tool '{tool_data['name']}' created successfully!")
                return redirect('tool_list')
            else:
                # Show the error message on the form page
                messages.error(request, f"Error creating tool: {result}")
                return render(request, 'user_info/tool_form.html', {
                    'form': form,
                    'title': 'Create New Tool'
                })
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
            # Get the user's API key
            api_key, error_response = get_user_api_key(request, 'tool_edit', {'tool_id': tool_id})
            if error_response:
                return error_response
            
            # Prepare the tool data
            tool_data = prepare_tool_data_from_form(form)
            
            # Delete the existing tool
            success, result = api_request('DELETE', f'/tools/custom/{tool_id}', api_key)
            if not success:
                # Show the error message on the form page
                messages.error(request, f"Error updating tool: {result}")
                return render(request, 'user_info/tool_form.html', {
                    'form': form,
                    'tool': tool,
                    'title': f"Edit Tool: {tool.name}"
                })
            
            # Create a new tool with the updated data
            success, result = api_request('POST', '/tools/custom', api_key, tool_data)
            if success:
                messages.success(request, f"Tool '{tool_data['name']}' updated successfully!")
                return redirect('tool_list')
            else:
                # Show the error message on the form page
                messages.error(request, f"Error updating tool: {result}")
                return render(request, 'user_info/tool_form.html', {
                    'form': form,
                    'tool': tool,
                    'title': f"Edit Tool: {tool.name}"
                })
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
        
        # Get the user's API key
        api_key, error_response = get_user_api_key(request, 'tool_list')
        if error_response:
            return error_response
        
        # Make API call to delete tool
        success, result = api_request('DELETE', f'/tools/custom/{tool_id}', api_key)
        
        if success:
            messages.success(request, f"Tool '{tool_name}' deleted successfully!")
        else:
            messages.error(request, f"Error deleting tool: {result}")
        
        return redirect('tool_list')
    
    return render(request, 'user_info/tool_confirm_delete.html', {'tool': tool})

# History view
@login_required
def history(request):
    # Get all shared search results for the current user
    user_queries = SharedSearchResult.objects.filter(user=request.user).order_by('-created_at')
    
    # Set up pagination
    paginator = Paginator(user_queries, 10)  # Show 10 queries per page
    page = request.GET.get('page')
    history_items = paginator.get_page(page)
    
    return render(request, 'user_info/history.html', {'history_items': history_items})

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
