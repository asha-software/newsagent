from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from .models import UserTool
from .forms import UserToolForm
import json
from django.views.decorators.csrf import csrf_exempt

def signin(request): 
    if request.user.is_authenticated:
        return redirect('search')  # Redirect to search page if already logged in
    if request.method == 'POST':
        username = request.POST.get('user_name')
        password = request.POST.get('password')

        print(f"Attempting to authenticate user: {username} with password: {password}")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            print("User authenticated successfully!")
            return redirect('search')  # Redirect to search page after login
        else:
            print("Authentication failed: Invalid credentials")
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
    
    # Pass API_URL from settings to the template
    context = {
        'show_results': show_results,
        'API_URL': settings.API_URL
    }
        
    return render(request, 'search.html', context)  # Render the search page with context

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
            tool = form.save(commit=False)
            tool.user = request.user
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
            form.save()
            messages.success(request, f"Tool '{tool.name}' updated successfully!")
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

@login_required
def get_session_id(request):
    """
    Returns the current user's session ID.
    This endpoint is used by the FastAPI backend to authenticate users.
    """
    return JsonResponse({
        'session_id': request.session.session_key,
        'username': request.user.username
    })

def validate_is_preferred(value):
    """
    Validates and normalizes the is_preferred value.
    """
    if isinstance(value, bool):
        return value
    elif isinstance(value, str) and value.lower() in ['true', 'false']:
        return value.lower() == 'true'
    elif isinstance(value, int) and value in [0, 1]:
        return bool(value)
    else:
        raise ValueError('is_preferred must be a boolean, 0/1, or "true"/"false".')

@csrf_exempt
@login_required
def set_tool_preference(request):
    """
    API endpoint to allow users to specify whether they prefer a tool.
    """
    if request.method == 'POST':
        try:
            # Parse the JSON body
            data = json.loads(request.body)
            tool_id = data.get('tool_id')
            is_preferred = data.get('is_preferred')

            if tool_id is None or is_preferred is None:
                return JsonResponse({'error': 'tool_id and is_preferred are required.'}, status=400)

            # Validate and normalize is_preferred
            try:
                is_preferred = validate_is_preferred(is_preferred)
            except ValueError as e:
                return JsonResponse({'error': str(e)}, status=400)

            # Fetch the tool for the current user
            tool = get_object_or_404(UserTool, id=tool_id, user=request.user)

            # Update the tool's preference
            tool.is_preferred = is_preferred
            tool.save()

            return JsonResponse({'message': f"Preference for tool '{tool.name}' updated successfully!"})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format.'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)
