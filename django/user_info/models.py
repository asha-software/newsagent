from django.db import models


class UserQuery(models.Model):
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(
        max_length=128
    )  # Use Django's password hashing in practice
    email = models.EmailField(unique=True)
    query = models.TextField()

    def __str__(self):
        return self.username
