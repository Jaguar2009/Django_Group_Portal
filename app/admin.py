from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Survey, Question, Answer, Notification, ForumPost, Event, Candidate, GroupMembership, Group, \
    Vote


class UserAdmin(BaseUserAdmin):
    list_display = (
    'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'avatar')  # Додаємо статус і аватар

    fieldsets = (
        (None, {'fields': ('email', 'first_name', 'last_name', 'password', 'status', 'avatar')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
            'email', 'first_name', 'last_name', 'password1', 'password2', 'avatar', 'is_staff', 'is_active')}
         ),
    )

    ordering = ('email',)


# Реєструємо кастомного користувача
admin.site.register(User, UserAdmin)
admin.site.register(Survey)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Notification)
admin.site.register(ForumPost)
admin.site.register(Event)
admin.site.register(Candidate)
admin.site.register(Group)
admin.site.register(GroupMembership)
admin.site.register(Vote)