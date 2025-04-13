import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class APIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    key = models.CharField(max_length=64, unique=True, editable=False)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        if not self.key:
            self.key = uuid.uuid4().hex
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"

class UserQuery(models.Model):
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)  # Use Django's password hashing in practice
    email = models.EmailField(unique=True)
    query = models.TextField()

    def __str__(self):
        return self.username

class UserTool(models.Model):
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tools')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    url_template = models.CharField(max_length=500)
    headers = models.JSONField(null=True, blank=True)
    default_params = models.JSONField(null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    json_payload = models.JSONField(null=True, blank=True)
    docstring = models.TextField(blank=True)
    target_fields = models.JSONField(null=True, blank=True)
    param_mapping = models.JSONField(null=True, blank=True)
    is_preferred = models.BooleanField(default=False)  # Boolean field to indicate user preference
    
    def __str__(self):
        return self.name

class SharedSearchResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_results')
    query = models.TextField()
    result_data = models.JSONField()
    created_at = models.DateTimeField(default=timezone.now)
    is_public = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Shared result by {self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
