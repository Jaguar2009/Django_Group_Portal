# forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Survey, Question, Answer, Notification, ForumPost, ForumAddition, Comment


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2', 'avatar')


class LoginForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)


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
    class Meta:
        model = ForumPost
        fields = ['title', 'image', 'content', 'files', 'status', 'access']  # Додано поле для файлів та статусу

    # Додавання валідації для файлів, якщо потрібно
    def clean_files(self):
        files = self.cleaned_data.get('files')
        if files and files.size > 300 * 1024 * 1024:  # 300MB
            raise forms.ValidationError("Розмір файлу не може перевищувати 300MB.")
        return files



class ForumPostAdditionForm(forms.ModelForm):
    class Meta:
        model = ForumAddition
        fields = ['title', 'content', 'image', 'files']  # Додано поле для файлів

    # Додавання валідації для файлів, якщо потрібно
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


class VoteForm(forms.Form):
    question_id = forms.IntegerField(widget=forms.HiddenInput())