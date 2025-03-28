from django.db import models
from django.contrib.auth.models import User


class UserQuery(models.Model):
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(
        max_length=128
    )  # Use Django's password hashing in practice
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
    
    def __str__(self):
        return self.name
