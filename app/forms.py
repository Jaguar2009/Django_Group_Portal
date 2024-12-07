# forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError

from .models import User, Survey, Question, Answer, Notification, ForumPost, ForumAddition, Comment, Event, Poll, \
    Candidate, GalleryItem, Group


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        error_messages={'required': 'Це поле є обов\'язковим.'}
    )
    first_name = forms.CharField(
        max_length=30,
        error_messages={'required': 'Це поле є обов\'язковим.'}
    )
    last_name = forms.CharField(
        max_length=30,
        error_messages={'required': 'Це поле є обов\'язковим.'}
    )
    avatar = forms.ImageField(
        required=False
    )
    agree_to_terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'Ви повинні погодитись із умовами використання.'}
    )
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput,
        min_length=8,
        error_messages={'required': 'Це поле є обов\'язковим.',
                        'min_length': 'Пароль повинен містити щонайменше 8 символів.'
                        }

    )
    password2 = forms.CharField(
        label="Підтвердження пароля",
        widget=forms.PasswordInput,
        min_length=8,
        error_messages={'required': 'Це поле є обов\'язковим.',
                        'min_length': 'Пароль повинен містити щонайменше 8 символів.'
                        }
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2', 'avatar')


class LoginForm(forms.Form):
    email = forms.EmailField(required=True, error_messages={
        'required': 'Це поле є обов\'язковим.',
    })
    password = forms.CharField(widget=forms.PasswordInput, required=True, error_messages={
        'required': 'Це поле є обов\'язковим.',
    })


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = ['title', 'description', 'image', 'question_count', 'active_until']

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'image', 'answer_count']

class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['text', 'image']

class SurveyResponseForm(forms.Form):
    def __init__(self, questions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for question in questions:
            self.fields[str(question.id)] = forms.ModelChoiceField(
                queryset=question.answers.all(),
                widget=forms.RadioSelect,
                required=True,
                empty_label=None,
                label=question.text
            )
            self.fields[str(question.id)].question = question  # Додаємо питання для доступу в шаблоні

    def clean(self):
        cleaned_data = super().clean()
        for name, field in self.fields.items():
            if not cleaned_data.get(name):
                self.add_error(name, "Це питання обов'язкове для заповнення.")
        return cleaned_data


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['title', 'description', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'cols': 40}),
        }


class ForumPostForm(forms.ModelForm):
    # Створюємо кастомні поля з перевірками
    title = forms.CharField(
        label="Назва",
        max_length=100,
        error_messages={
            'required': 'Це поле є обов\'язковим.',
            'max_length': 'Назва не може перевищувати 100 символів.',
        },
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    image = forms.ImageField(
        label="Картинка (необов'язково)",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    files = forms.FileField(
        label="Файли (не більше 300 MB)",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        error_messages={
            'invalid': 'Невірний формат файлу.',
        }
    )
    content = forms.CharField(
        label="Текст",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        required=True,
        error_messages = {
                'required': 'Це поле є обов\'язковим.'}
    )
    status = forms.ChoiceField(
        choices=ForumPost.STATUS_CHOICES,
        label="Статус",
        widget=forms.Select(attrs={'class': 'form-control'}),
        error_messages={
            'required': 'Це поле є обов\'язковим.'}

    )
    access = forms.ChoiceField(
        choices=ForumPost.ACCESS_CHOICES,
        label="Доступність",
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        error_messages={
            'required': 'Це поле є обов\'язковим.'}
    )

    class Meta:
        model = ForumPost
        fields = ['title', 'image', 'files', 'content', 'status', 'access']

    # Валідація логіки для обов'язкових полів залежно від статусу
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        access = cleaned_data.get('access')
        files = cleaned_data.get('files')

        # Перевірка обов'язковості поля доступність, якщо статус = "project"
        # Якщо статус == "проект", доступність обов'язкова
        if status == 'project':
            if not access:
                self.add_error('access', 'Доступність є обов\'язковим полем, коли статус обрано як "проект".')

        # Якщо статус == "пост", доступність повинна бути лише 'open'
        if status == 'post' and access != 'open':
            self.add_error('access', 'Для статусу "пост" доступність повинна бути лише "open".')

        # Перевірка обмежень розміру файлів
        if files:
            if files.size > 300 * 1024 * 1024:  # Перевірка на 300 MB
                self.add_error('files', 'Файл не може перевищувати 300 MB.')

        return cleaned_data


class ForumEditPostForm(forms.ModelForm):
    title = forms.CharField(
        label="Назва",
        max_length=100,
        error_messages={
            'required': 'Це поле є обов\'язковим.',
            'max_length': 'Назва не може перевищувати 100 символів.'
        },
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    content = forms.CharField(
        label="Текст",
        error_messages={'required': 'Це поле є обов\'язковим.'},
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5})
    )

    files = forms.FileField(
        label="Файл (не більше 300MB)",
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        error_messages={'required': 'Це поле є обов\'язковим.'}
    )

    status = forms.ChoiceField(
        label="Статус",
        choices=ForumPost.STATUS_CHOICES,
        error_messages={'required': 'Це поле є обов\'язковим.'},
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    access = forms.ChoiceField(
        label="Доступність",
        choices=ForumPost.ACCESS_CHOICES,
        error_messages={'required': 'Це поле є обов\'язковим.'},
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    image = forms.ImageField(
        label="Картинка (необов’язково)",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = ForumPost
        fields = ['title', 'image', 'content', 'files', 'status', 'access']

    def clean_files(self):
        files = self.cleaned_data.get('files')
        if files and files.size > 300 * 1024 * 1024:  # 300MB
            raise forms.ValidationError("Розмір файлу не може перевищувати 300MB.")
        return files


class ForumPostAdditionForm(forms.ModelForm):
    title = forms.CharField(
        label="Назва",
        max_length=100,
        error_messages={
            'required': 'Це поле є обов\'язковим.',
            'max_length': 'Назва не може перевищувати 100 символів.'
        },
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    content = forms.CharField(
        label="Зміст",
        error_messages={
            'required': 'Це поле є обов\'язковим.',
        },
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    image = forms.ImageField(
        label="Картинка (необов’язково)",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    files = forms.FileField(
        label="Файл (не більше 300MB)",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        error_messages={'invalid': 'Невірний файл. Будь ласка, завантажте правильний файл.'}
    )

    class Meta:
        model = ForumAddition
        fields = ['title', 'content', 'image', 'files']

    def clean_files(self):
        files = self.cleaned_data.get('files')
        if files and files.size > 300 * 1024 * 1024:  # 300MB
            raise forms.ValidationError("Розмір файлу не може перевищувати 300MB.")
        return files


class ForumEditPostAdditionForm(forms.ModelForm):
    title = forms.CharField(
        label="Назва",
        max_length=100,
        error_messages={
            'required': 'Це поле є обов\'язковим.',
            'max_length': 'Назва не може перевищувати 100 символів.'
        },
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    content = forms.CharField(
        label="Зміст",
        error_messages={
            'required': 'Це поле є обов\'язковим.',
        },
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    image = forms.ImageField(
        label="Картинка (необов’язково)",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    files = forms.FileField(
        label="Файл (не більше 300MB)",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        error_messages={'invalid': 'Невірний файл. Будь ласка, завантажте правильний файл.'}
    )

    class Meta:
        model = ForumAddition
        fields = ['title', 'content', 'image', 'files']

    def clean_files(self):
        files = self.cleaned_data.get('files')
        if files and files.size > 300 * 1024 * 1024:  # 300MB
            raise forms.ValidationError("Розмір файлу не може перевищувати 300MB.")
        return files


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        labels = {
            'content': 'Текст коментаря',
        }


class CommentEditForm(forms.ModelForm):
    content = forms.CharField(
        label="Текст коментаря",
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Введіть текст коментаря'}),
        required=True,
        error_messages={
            'required': 'Поле тексту коментаря є обов’язковим.'
        }
    )

    class Meta:
        model = Comment
        fields = ['content']


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'image', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class EventEditForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'image', 'start_time', 'end_time']


class PollForm(forms.ModelForm):
    class Meta:
        model = Poll
        fields = ['title', 'description', 'end_date', 'image', 'candidate_count']


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['name', 'description', 'image']


class PollEditForm(forms.ModelForm):
    class Meta:
        model = Poll
        fields = ['title', 'description', 'end_date', 'candidate_count', 'image']


class CandidateEditForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['name', 'description', 'image']


class GalleryItemForm(forms.ModelForm):
    class Meta:
        model = GalleryItem
        fields = ['file_type', 'file', 'title', 'description']

    # Назва
    title = forms.CharField(
        label="Назва",
        max_length=100,
        error_messages={
            'required': 'Це поле є обов\'язковим.',
            'max_length': 'Назва не може перевищувати 100 символів.',
        },
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # Опис
    description = forms.CharField(
        label="Опис",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        error_messages={
                'required': 'Це поле є обов\'язковим.'
            },
    )

    # Перевірка типу файлу
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Перевірка розміру файлу
            if file.size > 300 * 1024 * 1024:  # 300 MB
                raise forms.ValidationError("Файл не може бути більшим за 300 МБ.")

            # Перевірка на тип файлу
            file_type = self.cleaned_data.get('file_type')
            if file_type == 'image' and not file.name.lower().endswith(('.png', '.jpg')):
                raise forms.ValidationError("Для картинки допустимі тільки розширення png або jpg.")
            if file_type == 'video' and not file.name.lower().endswith('.mp4'):
                raise forms.ValidationError("Для відео допустимі тільки розширення mp4.")

        return file


class GalleryEditItemForm(forms.ModelForm):
    class Meta:
        model = GalleryItem
        fields = ['file_type', 'file', 'title', 'description']

    # Назва
    title = forms.CharField(
        label="Назва",
        max_length=100,
        error_messages={
            'required': 'Це поле є обов\'язковим.',
            'max_length': 'Назва не може перевищувати 100 символів.',
        },
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # Опис
    description = forms.CharField(
        label="Опис",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )

    # Перевірка типу файлу
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Перевірка розміру файлу
            if file.size > 300 * 1024 * 1024:  # 300 MB
                raise forms.ValidationError("Файл не може бути більшим за 300 МБ.")

            # Перевірка на тип файлу
            file_type = self.cleaned_data.get('file_type')
            if file_type == 'image' and not file.name.lower().endswith(('.png', '.jpg')):
                raise forms.ValidationError("Для картинки допустимі тільки розширення png або jpg.")
            if file_type == 'video' and not file.name.lower().endswith('.mp4'):
                raise forms.ValidationError("Для відео допустимі тільки розширення mp4.")

        return file


class AddFriendForm(forms.Form):
    identifier = forms.CharField(
        max_length=255,  # Максимальна довжина повинна підходити як для телефону, так і для email
        label="Email",
        widget=forms.TextInput(attrs={'placeholder': 'Введіть Email'})
    )


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'description', 'image']

    # Вказуємо, що поля є обов'язковими, крім зображення
    name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введіть назву групи'}))
    description = forms.CharField(required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Введіть опис групи'}))
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    # Перевизначаємо метод валідації для полів
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name) < 3:
            raise forms.ValidationError("Назва групи повинна бути довшою за 3 символи.")
        return name

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if len(description) < 5:
            raise forms.ValidationError("Опис групи має бути довший за 5 символів.")
        return description


class GroupEditForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'description', 'image']

    # Вказуємо, що поля є обов'язковими, крім зображення
    name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введіть назву групи'}))
    description = forms.CharField(required=True, widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Введіть опис групи'}))
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    # Перевизначаємо метод валідації для полів
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name) < 3:
            raise forms.ValidationError("Назва групи повинна бути довшою за 3 символи.")
        return name

    def clean_description(self):
        description = self.cleaned_data.get('description')
        if len(description) < 5:
            raise forms.ValidationError("Опис групи має бути довший за 5 символів.")
        return description