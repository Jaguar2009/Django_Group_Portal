from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from .forms import CustomUserCreationForm, LoginForm
from django.contrib.auth.decorators import login_required


def home(request):
    return render(request, 'portal_html/home.html')

@login_required
def admin_panel(request):
    # Перевірте, чи користувач - адміністратор
    if request.user.status == 'admin':
        return render(request, 'portal_html/admin_panel.html')  # ваша HTML-сторінка для адмін панелі
    else:
        return redirect('home')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')  # Змініть на вашу домашню сторінку
    else:
        form = CustomUserCreationForm()
    return render(request, 'portal_html/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  # Змініть на вашу домашню URL-адресу
            else:
                # Неправильний логін або пароль
                form.add_error(None, 'Неправильний логін або пароль')
    else:
        form = LoginForm()

    return render(request, 'portal_html/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')  # Перенаправлення на головну сторінку

@login_required
def delete_account(request):
    if request.method == 'POST':
        request.user.delete()  # Видалення акаунта
        return redirect('home')  # Перенаправлення на головну сторінку
    return render(request, 'portal_html/delete_account.html')
