from django.urls import path
from .views import register, signin, home, search, logout_view, forgot_password_view
from .views import tool_list, tool_create, tool_edit, tool_delete
from .views import get_api_key, apikey_list, apikey_create, apikey_delete
from .views import shared_search_result, save_shared_result

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
    
    # API Key URLs
    path('apikeys/', apikey_list, name='apikey_list'),
    path('apikeys/create/', apikey_create, name='apikey_create'),
    path('apikeys/<int:apikey_id>/delete/', apikey_delete, name='apikey_delete'),
    
    # API endpoints
    path('api/api-keys/', get_api_key, name='get_api_key'),
    path('api/save-shared-result/', save_shared_result, name='save_shared_result'),
    
    # Shared search results
    path('search/<uuid:result_id>/', shared_search_result, name='shared_search_result'),
]
