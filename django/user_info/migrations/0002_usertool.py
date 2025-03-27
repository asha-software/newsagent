# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('user_info', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserTool',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('method', models.CharField(choices=[('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('DELETE', 'DELETE'), ('PATCH', 'PATCH')], max_length=10)),
                ('url_template', models.CharField(max_length=500)),
                ('headers', models.JSONField(blank=True, null=True)),
                ('default_params', models.JSONField(blank=True, null=True)),
                ('data', models.JSONField(blank=True, null=True)),
                ('json_payload', models.JSONField(blank=True, null=True)),
                ('docstring', models.TextField(blank=True)),
                ('target_fields', models.JSONField(blank=True, null=True)),
                ('param_mapping', models.JSONField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tools', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
