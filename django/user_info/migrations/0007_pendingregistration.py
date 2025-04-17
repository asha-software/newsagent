# Generated by Django 5.1.7 on 2025-04-17 01:07

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("user_info", "0006_emailverification"),
    ]

    operations = [
        migrations.CreateModel(
            name="PendingRegistration",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("username", models.CharField(max_length=150, unique=True)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("password", models.CharField(max_length=128)),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
            ],
        ),
    ]
