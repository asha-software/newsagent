import requests
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.models import User

def get_builtin_tools():
    """
    Get the list of built-in tools from the API container.
    If the API call fails, fall back to hardcoded tools.
    
    Returns:
        list: A list of dictionaries containing tool information (name, value).
    """
    tools = []
    
    # Define a list of hardcoded tools to use as a fallback
    hardcoded_tools = [
        {"name": "calculator", "display_name": "Calculator"},
        {"name": "wikipedia", "display_name": "Wikipedia"},
        {"name": "web_search", "display_name": "Web Search"},
        {"name": "wolfram_alpha", "display_name": "Wolfram Alpha"}
    ]
    
    # Try to get the list of built-in tools from the API container
    try:
        # Get the API URL from settings
        api_url = settings.API_URL
        if not api_url:
            raise ValueError("API_URL is not set in settings")
        
        # First, let's try to make a simple API call to check if the API is available
        try:
            health_response = requests.get(f"{api_url}/health", timeout=5)
            health_response.raise_for_status()
        except Exception as e:
            raise ValueError(f"API health check failed: {e}")
        
        # Now, let's make an API call to get the list of built-in tools
        try:
            tools_response = requests.get(f"{api_url}/tools/builtins", timeout=5)
            tools_response.raise_for_status()
            tools_data = tools_response.json()
            
            if "tools" in tools_data and tools_data["tools"]:
                tools = tools_data["tools"]
            else:
                raise ValueError("No tools found in API response")
        except Exception as e:
            raise ValueError(f"Error getting built-in tools from API: {e}")
        
        if tools:
            return tools
        else:
            raise ValueError("No tools found in API container")
    except Exception:
        # Fall back to hardcoded tools if there's any error
        return hardcoded_tools

def send_password_reset_email(user, reset_token, request):
    """
    Send a password reset email to the user.
    
    Args:
        user: The User object
        reset_token: The reset token (UUID)
        request: The HTTP request object (to get the domain)
    
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    # Check if email verification is enabled
    if not settings.EMAIL_VERIFICATION_ENABLED:
        # If email verification is disabled, just return True without sending email
        return True
        
    try:
        # Get the domain from the request
        domain = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'
        
        # Create the reset URL
        reset_url = f"{protocol}://{domain}/reset-password/{reset_token}/"
        
        # Create the email content
        subject = 'Reset your password for Asha Software'
        html_message = render_to_string('user_info/password_reset_email.html', {
            'user': {'username': user.username},  # Pass a dict with username to template
            'reset_url': reset_url,
            'expiry_hours': 24,  # Token expires after 24 hours
        })
        plain_message = strip_tags(html_message)
        
        # Send the email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending password reset email: {str(e)}")
        # Re-raise the exception so it can be caught and handled by the view
        raise

def send_verification_email(user_or_pending, verification_token, request):
    """
    Send an email verification link to the user.
    
    Args:
        user_or_pending: The User object or PendingRegistration object
        verification_token: The verification token (UUID)
        request: The HTTP request object (to get the domain)
    
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    # Check if email verification is enabled
    if not settings.EMAIL_VERIFICATION_ENABLED:
        # If email verification is disabled, just return True without sending email
        return True
        
    try:
        # Get the domain from the request
        domain = request.get_host()
        protocol = 'https' if request.is_secure() else 'http'
        
        # Create the verification URL
        verification_url = f"{protocol}://{domain}/verify-email/{verification_token}/"
        
        # Determine if this is a User or PendingRegistration
        is_user = isinstance(user_or_pending, User)
        
        # Get the username and email
        if is_user:
            username = user_or_pending.username
            email = user_or_pending.email
        else:
            username = user_or_pending.username
            email = user_or_pending.email
        
        # Create the email content
        subject = 'Verify your email address for Asha Software'
        html_message = render_to_string('user_info/email_verification.html', {
            'user': {'username': username},  # Pass a dict with username to template
            'verification_url': verification_url,
            'expiry_hours': 24,  # Token expires after 24 hours
        })
        plain_message = strip_tags(html_message)
        
        # Send the email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending verification email: {str(e)}")
        # Re-raise the exception so it can be caught and handled by the view
        raise
