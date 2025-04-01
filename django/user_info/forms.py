from django import forms
from .models import UserQuery, UserTool
import json

class UserQueryForm(forms.ModelForm):
    class Meta:
        model = UserQuery
        fields = ['username', 'password', 'email']  # Removed 'query' field
        widgets = {
            'password': forms.PasswordInput(),
        }

class UserToolForm(forms.ModelForm):
    class Meta:
        model = UserTool
        fields = [
            'name', 'description', 'is_active', 'method', 'url_template',
            'headers', 'default_params', 'data', 'json_payload',
            'docstring', 'target_fields', 'param_mapping', 'is_preferred',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'docstring': forms.Textarea(attrs={'rows': 5}),
            'headers': forms.Textarea(attrs={'rows': 3, 'class': 'json-field'}),
            'default_params': forms.Textarea(attrs={'rows': 3, 'class': 'json-field'}),
            'data': forms.Textarea(attrs={'rows': 3, 'class': 'json-field'}),
            'json_payload': forms.Textarea(attrs={'rows': 3, 'class': 'json-field'}),
            'target_fields': forms.Textarea(attrs={'rows': 3, 'class': 'json-field'}),
            'param_mapping': forms.Textarea(attrs={'rows': 3, 'class': 'json-field'}),
        }
    
    def clean_headers(self):
        return self._clean_json_field('headers')
    
    def clean_default_params(self):
        return self._clean_json_field('default_params')
    
    def clean_data(self):
        return self._clean_json_field('data')
    
    def clean_json_payload(self):
        return self._clean_json_field('json_payload')
    
    def clean_target_fields(self):
        return self._clean_json_field('target_fields')
    
    def clean_param_mapping(self):
        return self._clean_json_field('param_mapping')
    
    def _clean_json_field(self, field_name):
        value = self.cleaned_data.get(field_name)
        if not value:
            return None
        
        # If value is already a dict, return it as is
        if isinstance(value, dict):
            return value
        
        # Otherwise, try to parse it as JSON
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise forms.ValidationError(f"Invalid JSON format in {field_name.replace('_', ' ')}")
