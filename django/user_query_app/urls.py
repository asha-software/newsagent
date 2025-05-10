from django.contrib import admin
from django.urls import path, include  # Include the include function

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("user_info.urls")),  # Include user_info app URLs
]
