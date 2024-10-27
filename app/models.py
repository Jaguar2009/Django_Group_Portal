from django.db import models
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        """Створити звичайного користувача."""
        if not email:
            raise ValueError('Email необхідний для створення користувача')
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        """Створити суперкористувача."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперкористувач має бути адміністратором')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперкористувач має бути суперкористувачем')

        return self.create_user(email, first_name, last_name, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    STATUS_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('participant', 'Participant'),
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='participant')
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()  # Додайте цей рядок

    def __str__(self):
        return self.email





