from django.urls import path
from .views import register, signin, home, search, logout_view, forgot_password_view
from .views import tool_list, tool_create, tool_edit, tool_delete
from .views import get_api_key

urlpatterns = [
    path('', home, name='home'),
    path('signup/', register, name='signup'),
    path('signin/', signin, name='signin'),
    path('search/', search, name='search'),
    path('logout/', logout_view, name='logout'),
    path('forgot/', forgot_password_view, name='forgot'),
    
    # Tool URLs
    path('tools/', tool_list, name='tool_list'),
    path('tools/create/', tool_create, name='tool_create'),
    path('tools/<int:tool_id>/edit/', tool_edit, name='tool_edit'),
    path('tools/<int:tool_id>/delete/', tool_delete, name='tool_delete'),
    
    # API endpoints
    path('api/api-keys/', get_api_key, name='get_api_key'),
]
