from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('admin_panel/', views.admin_panel, name='admin_panel'),
    path('logout/', views.logout_view, name='logout'),
    path('delete_account/', views.delete_account, name='delete_account'),

]