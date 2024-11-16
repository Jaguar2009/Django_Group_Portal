from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('admin_panel/', views.admin_panel, name='admin_panel'),
    path('logout/', views.logout_view, name='logout'),
    path('delete_profile/', views.delete_profile, name='delete_profile'),
    path('profile/', views.user_profile, name='profile'),
    path('create_survey/', views.create_survey, name='create_survey'),
    path('create_questions/<int:survey_id>/', views.create_questions, name='create_questions'),
    path('create_answers/<int:survey_id>/', views.create_answers, name='create_answers'),
    path('surveys/', views.survey_list, name='survey_list'),
    path('surveys/<int:survey_id>/', views.take_survey, name='take_survey'),
    path('survey/<int:survey_id>/responses/', views.survey_responses, name='survey_responses'),
    path('survey/<int:survey_id>/user/<int:user_id>/answers/', views.user_survey_responses, name='user_survey_answers'),
    path('survey/<int:survey_id>/delete/', views.delete_survey, name='delete_survey'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/create/', views.create_notification, name='create_notification'),
    path('delete_notification/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('forum/', views.forum_list, name='forum_list'),
    path('forum/create/', views.create_forum_post, name='create_forum_post'),
    path('forum/<int:post_id>/', views.forum_post_detail, name='forum_post_detail'),
    path('forum/<int:post_id>/add_update/', views.create_forum_post_addition, name='create_forum_post_addition'),
    path('forum/<int:post_id>/edit/', views.forum_post_update, name='forum_post_edit'),
    path('forum/<int:post_id>/delete/', views.forum_post_delete, name='forum_post_delete'),
    path('forum/update/<int:update_id>/edit/', views.edit_forum_post_addition, name='edit_forum_post_addition'),
    path('forum_post/addition/delete/<int:addition_id>/', views.delete_addition, name='delete_forum_post_addition'),
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('poll', views.poll_list, name='poll_list'),
    path('<int:poll_id>/', views.poll_detail, name='poll_detail'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('reservations/events-json/', views.events_json, name='events_json'),
    path('events/<int:id>/', views.event_detail, name='event_detail'),



]
