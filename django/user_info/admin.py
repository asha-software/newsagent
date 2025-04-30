from django.contrib import admin
from .models import UserQuery, UserTool, APIKey


class APIKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "key", "created_at", "last_used_at", "is_active")
    list_filter = ("is_active", "created_at", "last_used_at")
    search_fields = ("name", "key", "user__username", "user__email")
    readonly_fields = ("key", "created_at", "last_used_at")

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields
        return ()  # when creating a new object


admin.site.register(UserQuery)
admin.site.register(UserTool)
admin.site.register(APIKey, APIKeyAdmin)
