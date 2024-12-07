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
    friends = models.ManyToManyField('self', symmetrical=False, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    # Додайте ці поля
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return self.email


# Модель для груп
class Group(models.Model):
    name = models.CharField(max_length=255)  # Назва групи
    description = models.TextField()  # Опис групи
    created_at = models.DateTimeField(default=timezone.now)  # Час створення групи
    image = models.ImageField(upload_to='group_images/', blank=True, null=True)  # Картинка для групи

    def __str__(self):
        return self.name


# Модель для ролей користувачів в групах
class GroupMembership(models.Model):
    ROLE_CHOICES = [
        ('member', 'Учасник'),
        ('moderator', 'Модератор'),
        ('admin', 'Адмін'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')  # Роль користувача
    joined_at = models.DateTimeField(default=timezone.now)  # Час приєднання до групи

    class Meta:
        unique_together = ('user', 'group')  # Забезпечуємо, що один користувач не може бути в групі більше одного разу

    def __str__(self):
        return f'{self.user.email} - {self.group.name} ({self.role})'


class Survey(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='surveys/', blank=True, null=True)
    question_count = models.PositiveIntegerField()
    participant_count = models.PositiveIntegerField(default=0)
    active_until = models.DateTimeField(default=timezone.now, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="surveys", null=True, blank=True)  # Додано

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


class UserNews(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='news')  # Прив'язка до користувача
    title = models.CharField(max_length=255)  # Заголовок новини
    description = models.TextField()  # Опис новини
    image = models.ImageField(upload_to='user_news_images/', blank=True, null=True)  # Картинка для новини
    created_at = models.DateTimeField(default=timezone.now)  # Час створення новини

    def __str__(self):
        return f"Новина для {self.user.email}: {self.title}"


class Notification(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='notifications/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)  # Додано

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
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="forum_posts", null=True,blank=True)  # Додано

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
    forum_post = models.ForeignKey(
        ForumPost,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Пост на форумі",
        null=True,
        blank=True
    )
    gallery_item = models.ForeignKey(
        'GalleryItem',
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Об'єкт галереї",
        null=True,
        blank=True
    )
    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
        verbose_name="Батьківський коментар"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Автор коментаря"
    )
    content = models.TextField(verbose_name="Текст коментаря")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення")

    def __str__(self):
        if self.forum_post:
            return f"Коментар від {self.author} до '{self.forum_post.title}'"
        elif self.gallery_item:
            return f"Коментар від {self.author} до '{self.gallery_item.title}'"
        return f"Коментар від {self.author}"


class Event(models.Model):
    title = models.CharField(max_length=255, verbose_name="Назва події")
    description = models.TextField(verbose_name="Опис події")
    image = models.ImageField(upload_to='event_images/', blank=True, null=True, verbose_name="Картинка події")
    start_time = models.DateTimeField(verbose_name="Час початку події")
    end_time = models.DateTimeField(verbose_name="Час закінчення події")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="events", null=True, blank=True)  # Додано

    def __str__(self):
        return self.title


class Poll(models.Model):
    title = models.CharField(max_length=255)  # Назва голосування
    description = models.TextField()  # Опис голосування
    end_date = models.DateField()  # Дата завершення голосування
    candidate_count = models.PositiveIntegerField(default=0)  # Кількість кандидатів
    image = models.ImageField(upload_to='polls/', null=True, blank=True)  # Картинка для голосування
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='polls', null=True,
                              blank=True)  # Зв'язок з групою

    def __str__(self):
        return self.title


class Candidate(models.Model):
    poll = models.ForeignKey(Poll, related_name='candidates', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)  # Ім'я кандидата
    description = models.TextField()  # Опис кандидата
    image = models.ImageField(upload_to='candidates/')  # Зображення кандидата
    votes = models.PositiveIntegerField(default=0)  # Кількість голосів за кандидата

    def __str__(self):
        return self.name


class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Користувач, який голосує
    poll = models.ForeignKey(Poll, related_name='votes', on_delete=models.CASCADE)  # Голосування
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)  # Кандидат
    date = models.DateTimeField(auto_now_add=True)  # Дата голосування

    def __str__(self):
        return f'{self.user.first_name} voted for {self.candidate.name}'


class Ban(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bans')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='bans')
    end_date = models.DateTimeField()  # Дата завершення бану
    created_at = models.DateTimeField(default=timezone.now)  # Час створення бану

    def __str__(self):
        return f"Ban for {self.user.email} in group {self.group.name} until {self.end_date}"

    def is_active(self):
        return timezone.now() < self.end_date  # Перевірка, чи бан ще активний


class GalleryItem(models.Model):
    FILE_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    file_type = models.CharField(max_length=10, choices=FILE_TYPES, default='image')
    file = models.FileField(upload_to='gallery/')
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gallery_items')  # Заміна uploaded_by на author
    uploaded_at = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='gallery_items', null=True, blank=True)  # Додано зв’язок з групою

    def __str__(self):
        return self.title or f'Gallery Item #{self.id}'


class FriendRequest(models.Model):
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_friend_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_friend_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)



