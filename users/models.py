from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('professor', 'Professor'),
    )

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=50)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    major = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)

    REQUIRED_FIELDS = ['email', 'role', 'name']

    def __str__(self):
        return f"{self.name} ({self.username})"