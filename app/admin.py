from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User  # Замініть на вашу модель користувача


class UserAdmin(BaseUserAdmin):
    list_display = (
    'email', 'first_name', 'last_name', 'status', 'is_staff', 'is_active', 'avatar')  # Додаємо статус і аватар

    fieldsets = (
        (None, {'fields': ('email', 'first_name', 'last_name', 'password', 'status', 'avatar')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
            'email', 'first_name', 'last_name', 'password1', 'password2', 'status', 'avatar', 'is_staff', 'is_active')}
         ),
    )

    ordering = ('email',)


# Реєструємо кастомного користувача
admin.site.register(User, UserAdmin)