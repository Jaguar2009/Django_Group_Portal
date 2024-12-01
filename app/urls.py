from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),

    path('group/<int:group_id>/admin/', views.admin_panel, name='admin_panel'),
    path('admin_surveys/<int:group_id>/', views.admin_survey_list, name='admin_survey_list'),
    path('admin_notifications/<int:group_id>/', views.admin_notification_list, name='admin_notification_list'),
    path('admin_events/<int:group_id>/', views.admin_event_list, name='admin_event_list'),
    path('admin_polls/<int:group_id>/', views.admin_poll_list, name='admin_poll_list'),

    path('logout/', views.logout_view, name='logout'),
    path('delete_profile/', views.delete_profile, name='delete_profile'),
    path('profile/', views.user_profile, name='profile'),

    path('groups/<int:group_id>/create-survey/', views.create_survey, name='create_survey'),
    path('survey/<int:survey_id>/create_questions/', views.create_questions, name='create_questions'),
    path('survey/<int:survey_id>/create_answers/', views.create_answers, name='create_answers'),

    path('surveys/<int:survey_id>/', views.take_survey, name='take_survey'),
    path('survey/<int:survey_id>/responses/', views.survey_responses, name='survey_responses'),
    path('survey/<int:survey_id>/user/<int:user_id>/answers/', views.user_survey_responses, name='user_survey_answers'),
    path('survey/<int:survey_id>/delete/', views.delete_survey, name='delete_survey'),

    path('group/<int:group_id>/create_notification/', views.create_notification, name='create_notification'),
    path('delete_notification/<int:notification_id>/', views.delete_notification, name='delete_notification'),

    path('forum/create/<int:group_id>/', views.create_forum_post, name='create_forum_post'),
    path('forum/<int:post_id>/', views.forum_post_detail, name='forum_post_detail'),
    path('forum/<int:post_id>/add_update/', views.create_forum_post_addition, name='create_forum_post_addition'),
    path('forum/<int:post_id>/edit/', views.forum_post_update, name='forum_post_edit'),
    path('forum/<int:post_id>/delete/', views.forum_post_delete, name='forum_post_delete'),
    path('forum/update/<int:update_id>/edit/', views.edit_forum_post_addition, name='edit_forum_post_addition'),
    path('forum_post/addition/delete/<int:addition_id>/', views.delete_addition, name='delete_forum_post_addition'),

    path('portfolio/<int:group_id>/', views.portfolio_view, name='portfolio_view'),

    path('group/<int:group_id>/create_event/', views.create_event, name='create_event'),
    path('group/<int:group_id>/calendar/', views.calendar_view, name='calendar_view'),
    path('events/events-json/<int:group_id>/', views.events_json, name='events_json'),
    path('events/by-date/<str:date>/', views.events_by_date_json, name='events_by_date'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('delete_event/<int:event_id>/', views.delete_event, name='delete_event'),
    path('edit_event/<int:event_id>/', views.edit_event, name='edit_event'),

    path('polls/create/<int:group_id>/step1/', views.create_poll_step_1, name='create_poll_step_1'),
    path('polls/create/step2/<int:poll_id>/', views.create_poll_step_2, name='create_poll_step_2'),
    path('polls/vote/<int:poll_id>/', views.vote_poll, name='vote_poll'),
    path('poll_results/<int:poll_id>/', views.poll_results, name='poll_results'),
    path('delete_poll/<int:poll_id>/', views.delete_poll, name='delete_poll'),

    path('gallery/create/<int:group_id>/', views.create_post_gallery, name='create_post_gallery'),
    path('gallery/delete/<int:item_id>/', views.delete_gallery_item, name='delete_gallery_item'),
    path('gallery/edit/<int:item_id>/', views.edit_gallery_item, name='edit_gallery_item'),
    path('gallery/delete/<int:item_id>/', views.delete_gallery_item, name='delete_gallery_item'),
    path('gallery/<int:item_id>/', views.gallery_item_detail, name='gallery_item_detail'),

    path('friends/', views.FriendsView.as_view(), name='friends_list'),
    path('delete_friend/<int:friend_id>/', views.delete_friend, name='delete_friend'),
    path('confirm_friend_request/<int:request_id>/', views.handle_friend_request, name='confirm_friend_request'),
    path('delete_friend_request/<int:request_id>/', views.delete_friend, name='delete_friend_request'),

    path('create_group/', views.create_group, name='create_group'),
    path('group_list/', views.group_list, name='group_list'),
    path('groups/<int:group_id>/', views.group_detail, name='group_detail'),
    path('join-group/<int:group_id>/', views.join_group, name='join_group'),

    path('groups/<int:group_id>/gallery/', views.gallery_view, name='group_gallery'),
    path('groups/<int:group_id>/polls/', views.poll_list, name='group_polls'),
    path('groups/<int:group_id>/forum/', views.forum_list, name='group_forum'),
    path('groups/<int:group_id>/notifications/', views.notification_list, name='group_notifications'),
    path('groups/<int:group_id>/surveys/', views.survey_list, name='group_surveys')
]
