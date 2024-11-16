from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import BaseUserManager, PermissionsMixin
from django.conf import settings


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


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    # Додайте ці поля
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    STATUS_CHOICES = [
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('participant', 'Participant'),
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='participant')
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return self.email


class Survey(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='surveys/', blank=True, null=True)
    question_count = models.PositiveIntegerField()
    participant_count = models.PositiveIntegerField(default=0)
    active_until = models.DateTimeField(default=timezone.now, null=True, blank=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    answer_count = models.PositiveIntegerField()
    image = models.ImageField(upload_to='questions/', blank=True, null=True)  # Поле для зображення в питанні

    def __str__(self):
        return self.text

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=255)
    image = models.ImageField(upload_to='answers/', blank=True, null=True)

    def __str__(self):
        return self.text


class SurveyResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'survey', 'question')


class Notification(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='notifications/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title


class ForumPost(models.Model):
    STATUS_CHOICES = [
        ('post', 'Пост'),
        ('project', 'Проект'),
    ]
    ACCESS_CHOICES = [
        ('open', 'Відкрите'),
        ('closed', 'Закрите'),
    ]

    title = models.CharField(max_length=255, verbose_name="Назва")
    image = models.ImageField(upload_to='forum_post_images/', blank=True, null=True, verbose_name="Картинка")
    content = models.TextField(verbose_name="Текст")
    files = models.FileField(upload_to='forum_post_files/', blank=True, null=True, verbose_name="Файли")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='post', verbose_name="Статус")
    access = models.CharField(max_length=10, choices=ACCESS_CHOICES, default='open', verbose_name="Доступність")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_posts", verbose_name="Автор")

    def __str__(self):
        return self.title


class ForumAddition(models.Model):
    forum_post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="updates", verbose_name="Пост на форумі")
    title = models.CharField(max_length=255, verbose_name="Назва оновлення")
    image = models.ImageField(upload_to='forum_addition_images/', blank=True, null=True, verbose_name="Картинка оновлення")
    content = models.TextField(verbose_name="Текст оновлення")
    files = models.FileField(upload_to='forum_addition_files/', blank=True, null=True, verbose_name="Файли оновлення")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")

    def __str__(self):
        return f"Оновлення до: {self.forum_post.title} - {self.title}"


# Модель коментаря
class Comment(models.Model):
    forum_post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="comments", verbose_name="Пост на форумі")
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, related_name="replies", null=True, blank=True, verbose_name="Батьківський коментар")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments", verbose_name="Автор коментаря")
    content = models.TextField(verbose_name="Текст коментаря")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")

    def __str__(self):
        return f"Коментар від {self.author} до '{self.forum_post.title}'"


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField()
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Poll(models.Model):
    title = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')

    def __str__(self):
        return self.title

class Question_Poll(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    question_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.question_text

class Vote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey(Question_Poll, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'question')  # Ограничение: один пользователь может голосовать за один вопрос только один раз
