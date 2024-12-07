from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.views.generic import ListView

from .forms import LoginForm, AnswerForm, QuestionForm, SurveyForm, SurveyResponseForm, \
    NotificationForm, ForumPostForm, CommentForm, ForumPostAdditionForm, EventForm, EventEditForm, PollForm, \
    CandidateForm, CandidateEditForm, PollEditForm, GalleryItemForm, AddFriendForm, GroupForm, RegistrationForm, \
    GroupEditForm, ForumEditPostForm, ForumEditPostAdditionForm, CommentEditForm, GalleryEditItemForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Survey, Question, SurveyResult, Answer, Notification, ForumPost, Comment, ForumAddition, Event, \
    Poll, Vote, Candidate, User, Ban, GalleryItem, FriendRequest, GroupMembership, Group, UserNews
from django.db import IntegrityError
from datetime import datetime
from collections import defaultdict
from django.utils.timezone import now
import random
import os
from django.conf import settings


def search_groups(request):
    query = request.GET.get('q', '')  # Отримуємо строку пошуку
    groups = Group.objects.filter(name__icontains=query) if query else []  # Пошук груп

    # Додаємо інформацію про членство для кожної групи
    for group in groups:
        group.is_member = GroupMembership.objects.filter(user=request.user, group=group).exists()

    return render(request, 'portal_html/group_search_results.html', {'query': query, 'groups': groups})


@login_required(login_url='/login/')
def group_list(request):
    groups = Group.objects.all()
    user_groups = {membership.group.id for membership in GroupMembership.objects.filter(user=request.user)}
    for group in groups:
        group.is_member = group.id in user_groups
    return render(request, 'portal_html/group_list.html', {'groups': groups})


def is_group_admin(user, group):
    membership = GroupMembership.objects.get(user=user, group=group)
    if membership.role == "admin":
        return True
    return False


def is_group_moderator(user, group):
    membership = GroupMembership.objects.get(user=user, group=group)
    if membership.role == "moderator":
        return True
    return False


def is_user_admin_or_moderator(user, group):
    return is_group_admin(user, group) or is_group_moderator(user, group)


def check_user_ban_in_group(user, group):
    if Ban.objects.filter(user=user, group=group).exists():
        return redirect('group_detail', group_id=group.id)
    return


def home(request):
    return render(request, 'portal_html/home.html')


@login_required(login_url='/login/')
def admin_panel(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    # Отримання списків користувачів у межах групи
    admins = GroupMembership.objects.filter(group=group, role='admin').select_related('user')
    moderators = GroupMembership.objects.filter(group=group, role='moderator').select_related('user')
    members = GroupMembership.objects.filter(group=group, role='member').select_related('user')
    user_friends = request.user.friends.all()
    banned_users = User.objects.filter(bans__group=group).distinct()
    is_moderators = is_group_moderator(request.user, group)


    for ban in banned_users:
        if ban.end_date <= timezone.now():
            # Розблокування користувача
            UserNews.objects.create(
                user=ban.user,
                title=f"Вас розблоковано у групі {group.name}",
                description=f"Тепер ви можете знову взаємодіяти з групою {group.name}."
            )
            # Видалення запису бана
            ban.delete()


    message = None

    if request.method == 'POST':
        action = request.POST.get('action')
        email = request.POST.get('email')

        try:
            user = User.objects.get(email=email)
            user_membership = GroupMembership.objects.filter(user=user, group=group).first()

            if not user_membership:
                message = "Користувач не є членом цієї групи."
            else:
                if action == 'add_moderator':
                    if user_membership.role == 'admin':
                        message = "Адміністратор не може бути модератором."
                    else:
                        user_membership.role = 'moderator'
                        user_membership.save()
                        message = f"Користувач {user.email} оновлений до модератора."

                elif action == 'demote_moderator':
                    if user_membership.role == 'moderator':
                        user_membership.role = 'member'
                        user_membership.save()
                        message = f"Користувач {user.email} знижений до учасника."
                    else:
                        message = "Тільки модератори можуть бути знижені до учасників."

                elif action == 'ban_user':
                    end_date = request.POST.get('end_date')
                    news_title = request.POST.get('news_title')
                    news_description = request.POST.get('news_description')
                    image = request.FILES.get('image')

                    if not end_date:
                        message = "Необхідно вказати дату завершення бану."
                    else:
                        # Створення бана
                        Ban.objects.create(user=user, group=group, end_date=end_date)

                        # Створення новини
                        UserNews.objects.create(
                            user=user,
                            title=news_title,
                            description=news_description,
                            image=image,
                        )
                        message = f"Користувач {user.email} заблокований до {end_date}."

                elif action == 'unban_user':
                    Ban.objects.filter(user=user, group=group).delete()
                    UserNews.objects.create(
                        user=user,
                        title=f"Вас розблоковано у групі {group.name}",
                        description=f"Тепер ви можете знову взаємодіяти з групою {group.name}.",
                    )
                    message = f"Користувач {user.email} розблокований."

        except User.DoesNotExist:
            message = "Користувача з такою поштою не знайдено."

    return render(request, 'portal_html/admin_panel.html', {
        'group': group,
        'admins': admins,
        'moderators': moderators,
        'banned_users': banned_users,
        'members': members,
        "user_friends": user_friends,
        'is_moderators': is_moderators,
        'message': message,
    })


@login_required(login_url='/login/')
def admin_survey_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    surveys = Survey.objects.filter(group=group)
    return render(request, 'portal_html/admin_survey_list.html', {'surveys': surveys, 'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def admin_notification_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    notifications = Notification.objects.filter(group=group)
    return render(request, 'portal_html/admin_notification_list.html', {'notifications': notifications, 'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def admin_event_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    events = Event.objects.filter(group=group)
    return render(request, 'portal_html/admin_event_list.html', {'events': events, 'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def admin_poll_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    polls = Poll.objects.filter(group=group)
    return render(request, 'portal_html/admin_poll_list.html', {'polls': polls, 'group': group, 'is_admin': is_admin})


def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')  # Замініть 'home' на ім'я вашої домашньої сторінки
    else:
        form = RegistrationForm()
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


@login_required(login_url='/login/')
def logout_view(request):
    logout(request)
    return redirect('home')  # Перенаправлення на головну сторінку


@login_required(login_url='/login/')
def delete_profile(request):
    if request.method == 'POST':
        request.user.delete()  # Видалення акаунта
        return redirect('home')  # Перенаправлення на головну сторінку
    return redirect('user_profile')


@login_required(login_url='/login/')
def user_profile(request):
    user = request.user
    context = {
        'user': user,
    }
    return render(request, 'portal_html/user_profile.html', context)


@login_required(login_url='/login/')
def user_profile_by_icon(request, user_id):
    user = get_object_or_404(User, id=user_id)
    return render(request, 'portal_html/user_profile_by_icon.html', {'user': user})


@login_required(login_url='/login/')
def create_survey(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    if request.method == 'POST':
        survey_form = SurveyForm(request.POST, request.FILES)
        if survey_form.is_valid():
            # Прив'язуємо опитування до групи перед збереженням
            survey = survey_form.save(commit=False)
            survey.group = group
            survey.save()
            return redirect('create_questions', survey_id=survey.id)
    else:
        survey_form = SurveyForm()

    return render(request, 'portal_html/create_survey.html', {
        'survey_form': survey_form,
        'group': group
    })


@login_required(login_url='/login/')
def create_questions(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    group = survey.group

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    question_forms = [QuestionForm(prefix=f'question_{i}') for i in range(survey.question_count)]

    if request.method == 'POST':
        question_forms = [QuestionForm(request.POST, request.FILES, prefix=f'question_{i}') for i in
                          range(survey.question_count)]
        all_valid = True

        for i in range(survey.question_count):
            question_form = question_forms[i]
            if question_form.is_valid():
                question = question_form.save(commit=False)
                question.survey = survey  # Прив'язуємо питання до опитування
                question.save()
            else:
                all_valid = False

        if all_valid:
            return redirect('create_answers', survey_id=survey.id)

    return render(request, 'portal_html/create_questions.html', {
        'forms': question_forms,
        'survey': survey,
        'group': group,
    })


@login_required(login_url='/login/')
def create_answers(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    group = survey.group
    questions = survey.questions.all()

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    if request.method == 'POST':
        answer_forms = []
        for question in questions:
            for i in range(question.answer_count):
                form = AnswerForm(request.POST, request.FILES, prefix=f'answer_{question.id}_{i}')
                if form.is_valid():
                    answer = form.save(commit=False)
                    answer.question = question  # Прив'язуємо відповідь до питання
                    answer.save()
                answer_forms.append(form)
        return redirect('group_surveys', group_id=group.id)  # Перенаправлення на домашню сторінку

    else:
        answer_forms = []
        for question in questions:
            for i in range(question.answer_count):
                answer_forms.append(AnswerForm(prefix=f'answer_{question.id}_{i}'))

    return render(request, 'portal_html/create_answers.html', {
        'survey': survey,
        'forms': answer_forms,
        'group': group,
    })


@login_required(login_url='/login/')
def take_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    group = survey.group # Отримуємо групу через опитування
    is_admin = is_user_admin_or_moderator(request.user, group)

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    # Перевірка, чи термін дії опитування ще не завершився
    if survey.active_until < timezone.now():
        return redirect('group_surveys', group_id=group.id)

    questions = survey.questions.all()
    initial_answers = {
        str(result.question.id): result.selected_answer.id
        for result in SurveyResult.objects.filter(user=request.user, survey=survey)
    }

    if request.method == 'POST':
        form = SurveyResponseForm(questions=questions, data=request.POST)
        if form.is_valid():
            SurveyResult.objects.filter(user=request.user, survey=survey).delete()
            for question in questions:
                selected_answer = form.cleaned_data.get(str(question.id))
                SurveyResult.objects.create(
                    user=request.user,
                    survey=survey,
                    question=question,
                    selected_answer=selected_answer
                )
            survey.participant_count += 1
            survey.save()
            return redirect('group_surveys', group_id=group.id)
    else:
        form = SurveyResponseForm(questions=questions, initial=initial_answers)

    return render(request, 'portal_html/take_survey.html', {
        'survey': survey,
        'form': form,
        'group': group,
        'is_admin': is_admin# Передаємо групу в контекст
    })


@login_required(login_url='/login/')
def survey_responses(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    group = survey.group  # Отримуємо групу через опитування
    is_admin = is_user_admin_or_moderator(request.user, group)
    survey_results = SurveyResult.objects.filter(survey=survey)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    # Отримати унікальних користувачів, які пройшли це опитування
    unique_users = {}
    for result in survey_results:
        unique_users[result.user.id] = result.user
    users = unique_users.values()  # Перетворити словник на список унікальних користувачів

    # Підрахунок відповідей
    question_data = {}
    for result in survey_results:
        question = result.question
        selected_answer = result.selected_answer

        if question not in question_data:
            question_data[question] = {}

        if selected_answer in question_data[question]:
            question_data[question][selected_answer] += 1
        else:
            question_data[question][selected_answer] = 1

    # Створити структуру даних для графіка
    chart_data = {}
    for question, answers in question_data.items():
        chart_data[question.text] = {
            'labels': [answer.text for answer in answers.keys()],
            'data': [count for count in answers.values()]
        }

    context = {
        'survey': survey,
        'users': users,
        'chart_data': chart_data,
        'group': group,  # Передаємо групу в контекст
        'is_admin': is_admin
    }
    return render(request, 'portal_html/survey_responses.html', context)


@login_required(login_url='/login/')
def user_survey_responses(request, survey_id, user_id):
    survey = get_object_or_404(Survey, id=survey_id)
    group = survey.group  # Отримуємо групу через опитування
    is_admin = is_user_admin_or_moderator(request.user, group)

    # Перевірка, чи користувач є власником відповіді або адміністратором
    if request.user.id != user_id and not request.user.is_staff:
        return redirect('home')  # Перенаправлення на домашню сторінку, якщо доступ заборонено

    user_responses = SurveyResult.objects.filter(survey=survey, user_id=user_id)

    return render(request, 'portal_html/user_survey_responses.html', {
        'survey': survey,
        'user_responses': user_responses,
        'group': group,
        'is_admin': is_admin# Передаємо групу в контекст
    })

@login_required(login_url='/login/')
def delete_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    group = survey.group

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    survey.delete()
    return redirect('group_surveys', group_id=group.id)


@login_required(login_url='/login/')
def create_notification(request, group_id):
    group = get_object_or_404(Group, id=group_id)  # Отримуємо групу за ID
    is_admin = is_user_admin_or_moderator(request.user, group)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    if request.method == 'POST':
        form = NotificationForm(request.POST, request.FILES)
        if form.is_valid():
            notification = form.save(commit=False)  # Створюємо об'єкт, але не зберігаємо його
            notification.group = group  # Прив'язуємо оголошення до групи
            notification.save()  # Зберігаємо в базу даних
            return redirect('group_notifications', group_id=group.id)  # Перенаправлення на список оголошень групи
    else:
        form = NotificationForm()

    return render(request, 'portal_html/create_notification.html', {
        'form': form,
        'group': group,
        'is_admin': is_admin, # Передаємо групу в шаблон
    })


@login_required(login_url='/login/')
def notification_detail(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    group = notification.group
    is_admin = is_user_admin_or_moderator(request.user, group)

    return render(request, "portal_html/notification_detail.html", {"notification": notification, 'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)
    group = notification.group

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    notification.delete()
    return redirect('group_notifications', group_id=group.id)


# Сторінка створення нового посту
@login_required(login_url='/login/')
def create_forum_post(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    if request.method == 'POST':
        form = ForumPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user  # Призначаємо автора
            post.group = group  # Прив’язуємо до групи
            post.save()
            return redirect('group_forum', group_id=group.id)  # Після створення перенаправляємо на головну сторінку
    else:
        form = ForumPostForm()

    return render(request, 'portal_html/create_forum_post.html', {'form': form, 'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def forum_post_update(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    group = post.group
    is_admin = is_user_admin_or_moderator(request.user, group)

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    # Перевірка, чи користувач є автором посту
    if request.user != post.author:
        return redirect('group_forum', group_id=group.id)

    if request.method == 'POST':
        form = ForumEditPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('forum_post_detail', post_id=post.id)
    else:
        form = ForumEditPostForm(instance=post)

    return render(request, 'portal_html/forum_post_edit.html', {
        'form': form,
        'group': group,
        'is_admin': is_admin,
    })


@login_required(login_url='/login/')
def forum_post_delete(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    group = post.group

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    # Перевірка, чи користувач є автором посту
    if request.user != post.author:
        return redirect('group_forum', group_id=group.id)

    if request.method == 'POST':
        post.delete()
        return redirect('group_forum', group_id=group.id)  # Переходимо на список форумів після видалення


@login_required(login_url='/login/')
def forum_post_detail(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    group = post.group
    is_admin = is_user_admin_or_moderator(request.user, group)
    comments = post.comments.filter(parent_comment__isnull=True)
    comment_form = CommentForm()

    user_ban = check_user_ban_in_group(request.user, group)

    if user_ban:
        # Вивести лише сторінку з повідомленням, що користувач заблокований, без можливості взаємодії
        return render(request, 'portal_html/forum_post_detail.html', {
            'post': post,
            'comments': comments,
            'comment_form': comment_form,
            'group': group,
            'is_admin': is_admin,
            'user_banned': True,  # Відправляємо прапор, що користувач заблокований
        })


    if request.method == 'POST':
        # Перевірка, чи це редагування коментаря
        delete_comment_id = request.POST.get("delete_comment_id")
        if delete_comment_id:
            comment_to_delete = get_object_or_404(Comment, id=delete_comment_id, author=request.user)
            comment_to_delete.delete()
            return redirect('forum_post_detail', post_id=post.id)

        comment_id = request.POST.get("comment_id")
        if comment_id:
            comment = get_object_or_404(Comment, id=comment_id, author=request.user)
            edit_comment_form = CommentEditForm(request.POST, instance=comment)
            if edit_comment_form.is_valid():
                edit_comment_form.save()
                return redirect('forum_post_detail', post_id=post.id)

        # Обробка додавання нового коментаря
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.forum_post = post
            new_comment.author = request.user
            parent_comment_id = request.POST.get("parent_comment_id")
            if parent_comment_id:
                parent_comment = Comment.objects.get(id=parent_comment_id)
                if not parent_comment.replies.filter(author=request.user, content=new_comment.content).exists():
                    new_comment.parent_comment = parent_comment
            new_comment.save()
            return redirect('forum_post_detail', post_id=post.id)


    return render(request, 'portal_html/forum_post_detail.html', {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'group': group,
        'is_admin': is_admin,
    })


@login_required(login_url='/login/')
def create_forum_post_addition(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    group = post.group
    is_admin = is_user_admin_or_moderator(request.user, group)

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    # Перевірка, чи користувач є автором посту
    if request.user != post.author:
        return redirect('group_forum', group_id=group.id)

    if request.method == 'POST':
        form = ForumPostAdditionForm(request.POST, request.FILES)
        if form.is_valid():
            update = form.save(commit=False)  # Зберігаємо без запису
            update.forum_post = post  # Прив'язуємо до посту, щоб уникнути помилки
            try:
                update.save()  # Зберігаємо з прив'язкою до parent_post
                return redirect('forum_post_detail', post_id=post.id)
            except IntegrityError:
                form.add_error(None, "Помилка при збереженні апдейту. Спробуйте ще раз.")
    else:
        form = ForumPostAdditionForm()

    return render(request, 'portal_html/create_addition.html', {'post': post, 'form': form, 'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def edit_forum_post_addition(request, update_id):
    update = get_object_or_404(ForumAddition, id=update_id)
    post = update.forum_post
    group = post.group
    is_admin = is_user_admin_or_moderator(request.user, group)

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    # Перевірка, чи користувач є автором апдейту
    if request.user != update.forum_post.author:
        return redirect('group_forum', group_id=group.id)

    if request.method == 'POST':
        form = ForumEditPostAdditionForm(request.POST, request.FILES, instance=update)
        if form.is_valid():
            form.save()
            return redirect('forum_post_detail', post_id=update.forum_post.id)
    else:
        form = ForumEditPostAdditionForm(instance=update)

    return render(request, 'portal_html/edit_addition.html', {'form': form, 'update': update, 'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def delete_addition(request, addition_id):
    addition = get_object_or_404(ForumAddition, id=addition_id)
    post_id = addition.forum_post.id
    post = addition.forum_post
    group = post.group

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    # Перевірка, чи користувач є автором посту
    if request.user != post.author:
        return redirect('group_forum', group_id=group.id)

    if request.method == 'POST':
        addition.delete()
        return redirect('forum_post_detail', post_id=post.id)


@login_required(login_url='/login/')
def portfolio_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)
    projects = ForumPost.objects.filter(status='project', author=request.user, group=group)
    return render(request, 'portal_html/portfolio.html', {'projects': projects, 'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def create_event(request, group_id):
    group = get_object_or_404(Group, id=group_id)  # Отримуємо групу за ID
    is_admin = is_user_admin_or_moderator(request.user, group)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)  # Створюємо об'єкт, але не зберігаємо його
            event.group = group  # Прив'язуємо подію до групи
            event.save()  # Зберігаємо в базу даних
            return redirect('calendar_view', group_id=group.id)  # Перенаправлення на календар групи
    else:
        form = EventForm()

    return render(request, 'portal_html/create_event.html', {
        'form': form,
        'group': group,
        'is_admin': is_admin, # Передаємо групу в шаблон
    })



@login_required(login_url='/login/')
def calendar_view(request, group_id):
    # Отримуємо групу за ID
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)

    # Фільтруємо події, пов'язані з цією групою
    events = Event.objects.filter(group=group, end_time__gte=timezone.now())

    return render(request, 'portal_html/calendar.html', {
        'group': group,
        'events': events,
        'is_admin': is_admin,
    })


@login_required(login_url='/login/')
def events_json(request, group_id):
    # Отримуємо групу за ID
    group = get_object_or_404(Group, id=group_id)

    # Фільтруємо лише активні події для конкретної групи
    events = Event.objects.filter(group=group, end_time__gte=now())
    events_by_date = defaultdict(list)

    # Розбиваємо події на окремі дні
    for event in events:
        current_date = event.start_time.date()
        end_date = event.end_time.date()

        while current_date <= end_date:
            events_by_date[current_date].append(event)
            current_date += timedelta(days=1)

    # Формуємо дані для календаря
    data = []
    for date, events_list in events_by_date.items():
        if len(events_list) > 1:
            # Якщо подій більше однієї, показуємо кількість подій
            data.append({
                "title": f"{len(events_list)} подій",
                "start": date.isoformat(),
                "url": f"/events/by-date/{date}/",
            })
        else:
            # Якщо одна подія, показуємо її назву
            event = events_list[0]
            data.append({
                "title": event.title,
                "start": date.isoformat(),
                "url": f"/events/{event.id}/",
            })

    return JsonResponse(data, safe=False)


@login_required(login_url='/login/')
def events_by_date_json(request, date):
    # Перетворюємо отриману дату у формат datetime
    selected_date = datetime.strptime(date, "%Y-%m-%d").date()

    # Шукаємо події, що перетинаються з вибраною датою
    events = Event.objects.filter(
        start_time__date__lte=selected_date,  # Подія почалася до або на цю дату
        end_time__date__gte=selected_date    # Подія закінчилася після або на цю дату
    )

    # Знаходимо групу для першої події (припускаємо, що всі події належать одній групі)
    group = events.first().group if events.exists() else None
    is_admin = is_user_admin_or_moderator(request.user, group)

    # Відображаємо список подій
    return render(request, 'portal_html/events_by_date.html', {
        'events': events,
        'date': selected_date,
        'group': group,  # Додаємо групу в контекст
        'is_admin': is_admin,
    })


@login_required(login_url='/login/')
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    group = event.group
    is_admin = is_user_admin_or_moderator(request.user, group)
    return render(request, 'portal_html/event_detail.html', {'event': event, 'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    group = event.group

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    event.delete()
    return redirect('calendar_view', group_id=group.id)


@login_required(login_url='/login/')
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    group = event.group
    is_admin = is_user_admin_or_moderator(request.user, group)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    # Якщо форма була надіслана
    if request.method == 'POST':
        form = EventEditForm(request.POST, instance=event)
        if form.is_valid():
            form.save()  # Зберігаємо зміни
            return redirect('home')  # Перенаправляємо назад до адмін панелі
    else:
        form = EventEditForm(instance=event)  # Заповнюємо форму на основі існуючих даних події

    return render(request, 'portal_html/edit_event.html', {'form': form, 'event': event, 'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def create_poll_step_1(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    if request.method == 'POST':
        poll_form = PollForm(request.POST, request.FILES)
        if poll_form.is_valid():
            poll = poll_form.save(commit=False)  # Не зберігаємо ще в базу
            poll.group = group  # Прив'язуємо голосування до групи
            poll.save()  # Зберігаємо голосування в базу

            # Перенаправляємо на наступний етап, передаючи ID створеного голосування
            return redirect('create_poll_step_2', poll_id=poll.id)
    else:
        poll_form = PollForm()

    return render(request, 'portal_html/create_poll_step_1.html', {
        'poll_form': poll_form,
        'group': group,
        'is_admin': is_admin  # Передаємо групу для контексту шаблону (якщо потрібно)
    })


@login_required(login_url='/login/')
def create_poll_step_2(request, poll_id):
    poll = Poll.objects.get(id=poll_id)
    group = poll.group
    is_admin = is_user_admin_or_moderator(request.user, group)
    candidates_count = poll.candidate_count

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    if request.method == 'POST':
        # Обробляємо дані для кожної форми
        candidate_forms = [
            CandidateForm(request.POST, request.FILES, prefix=f'candidate_{i}')
            for i in range(candidates_count)
        ]
        all_valid = True
        for form in candidate_forms:
            if form.is_valid():
                candidate = form.save(commit=False)
                candidate.poll = poll
                candidate.save()
            else:
                all_valid = False

        if all_valid:
            return redirect('group_polls', group_id=group.id)  # Перенаправляємо на список голосувань

    else:
        # Створюємо список порожніх форм для кандидатів
        candidate_forms = [
            CandidateForm(prefix=f'candidate_{i}')
            for i in range(candidates_count)
        ]

    return render(request, 'portal_html/create_poll_step_2.html', {
        'poll': poll,
        'candidate_forms': candidate_forms,
        'group': group,
        'is_admin': is_admin,
    })


@login_required(login_url='/login/')
def vote_poll(request, poll_id):
    poll = get_object_or_404(Poll, id=poll_id)
    group = poll.group
    is_admin = is_user_admin_or_moderator(request.user, group)

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    # Перевірка, чи голосування ще не завершилось
    if poll.end_date < timezone.now().date():  # Порівнюємо дати
        return redirect('group_polls', group_id=group.id)  # Якщо голосування закінчилось, показуємо повідомлення

    # Отримуємо кандидатів
    candidates = poll.candidates.all()[:2]  # Вибираємо два кандидати

    # Перевіряємо, чи користувач уже проголосував
    try:
        existing_vote = Vote.objects.get(user=request.user, poll=poll)
        # Якщо є старий голос, видаляємо його
        existing_vote.delete()
    except Vote.DoesNotExist:
        pass

    if request.method == 'POST':
        # Отримуємо кандидата, за якого користувач хоче проголосувати
        candidate_id = request.POST.get('candidate_id')
        candidate = get_object_or_404(Candidate, id=candidate_id)

        # Створюємо новий голос
        Vote.objects.create(user=request.user, candidate=candidate, poll=poll)

        return redirect('group_polls', group_id=group.id)  # Після голосування перенаправляємо на список голосувань

    return render(request, 'portal_html/vote_poll.html', {'poll': poll, 'candidates': candidates, 'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def poll_results(request, poll_id):
    poll = Poll.objects.get(id=poll_id)
    group = poll.group
    is_admin = is_user_admin_or_moderator(request.user, group)
    candidates = Candidate.objects.filter(poll=poll)
    chart_data = {}

    # Збираємо дані для графіка
    for candidate in candidates:
        votes = Vote.objects.filter(candidate=candidate)
        chart_data[candidate.name] = votes.count()

    chart_data = {
        'labels': list(chart_data.keys()),
        'data': list(chart_data.values())
    }

    return render(request, 'portal_html/poll_results.html', {
        'poll': poll,
        'chart_data': chart_data,
        'group': group,
        'is_admin': is_admin,
    })


@login_required(login_url='/login/')
def delete_poll(request, poll_id):
    poll = get_object_or_404(Poll, id=poll_id)
    group = poll.group

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    poll.delete()
    return redirect('group_polls', group_id=group.id)




@login_required(login_url='/login/')
def gallery_item_detail(request, item_id):
    gallery_item = get_object_or_404(GalleryItem, id=item_id)
    group = gallery_item.group
    is_admin = is_user_admin_or_moderator(request.user, group)
    comments = gallery_item.comments.filter(parent_comment__isnull=True)
    comment_form = CommentForm()

    user_ban = check_user_ban_in_group(request.user, group)

    if user_ban:
        # Вивести лише сторінку з повідомленням, що користувач заблокований, без можливості взаємодії
        return render(request, 'portal_html/gallery_item_detail.html', {
            'gallery_item': gallery_item,
            'comments': comments,
            'comment_form': comment_form,
            'group': group,
            'is_admin': is_admin,
            'user_banned': True,  # Відправляємо прапор, що користувач заблокований
        })

    if request.method == 'POST':

        # Видалення коментаря
        delete_comment_id = request.POST.get("delete_comment_id")
        if delete_comment_id:
            comment_to_delete = get_object_or_404(Comment, id=delete_comment_id, author=request.user)
            comment_to_delete.delete()
            return redirect('gallery_item_detail', item_id=gallery_item.id)

        comment_id = request.POST.get("comment_id")
        if comment_id:
            comment = get_object_or_404(Comment, id=comment_id, author=request.user)
            edit_comment_form = CommentEditForm(request.POST, instance=comment)
            if edit_comment_form.is_valid():
                edit_comment_form.save()
                return redirect('gallery_item_detail', item_id=gallery_item.id)

        # Додавання нового коментаря
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.gallery_item = gallery_item
            new_comment.author = request.user

            # Додавання відповідей на коментар
            parent_comment_id = request.POST.get("parent_comment_id")
            if parent_comment_id:
                parent_comment = get_object_or_404(Comment, id=parent_comment_id)
                new_comment.parent_comment = parent_comment

            new_comment.save()
            return redirect('gallery_item_detail', item_id=gallery_item.id)

    return render(request, 'portal_html/gallery_item_detail.html', {
        'gallery_item': gallery_item,
        'comments': comments,
        'comment_form': comment_form,
        'group': group,
        'is_admin': is_admin,
    })


@login_required(login_url='/login/')
def delete_gallery_item(request, item_id):
    item = get_object_or_404(GalleryItem, id=item_id)
    group = item.group

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    if request.user != item.author:
        return redirect('group_gallery', group_id=group.id)

    item.delete()
    return redirect('group_gallery', group_id=group.id)


@login_required(login_url='/login/')
def edit_gallery_item(request, item_id):
    item = get_object_or_404(GalleryItem, id=item_id)
    group = item.group
    is_admin = is_user_admin_or_moderator(request.user, group)

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    if request.user != item.author:
        return redirect('group_gallery', group_id=group.id)

    if request.method == 'POST':
        form = GalleryEditItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('gallery_item_detail', item_id=item.id)
    else:
        form = GalleryEditItemForm(instance=item)

    return render(request, 'portal_html/edit_gallery_item.html', {
        'form': form,
        'item': item,
        'group': group,
        'is_admin': is_admin
    })


@login_required(login_url='/login/')
def create_post_gallery(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)

    user_ban = check_user_ban_in_group(request.user, group)
    if user_ban:
        return user_ban

    if request.method == 'POST':
        form = GalleryItemForm(request.POST, request.FILES)
        if form.is_valid():
            gallery_item = form.save(commit=False)
            gallery_item.author = request.user  # Призначаємо автора
            gallery_item.group = group  # Прив’язуємо до групи
            gallery_item.save()
            return redirect('group_detail', group_id=group.id)  # Після збереження перенаправляємо на список галереї
    else:
        form = GalleryItemForm()

    return render(request, 'portal_html/upload_gallery_item.html', {'form': form, 'group': group, 'is_admin': is_admin})



class FriendsView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'portal_html/friends_list.html'
    context_object_name = 'friends'
    login_url = '/login/'

    def get_queryset(self):
        user = self.request.user
        # Отримуємо список друзів
        queryset = user.friends.all()

        # Отримуємо значення параметра пошуку
        search_query = self.request.GET.get('search', '')

        if search_query:
            # Фільтруємо список друзів за іменем, прізвищем, поштою або номером телефону
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            ).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AddFriendForm()
        context['friend_requests'] = self.request.user.received_friend_requests.filter(status='pending')
        context['sent_requests'] = self.request.user.sent_friend_requests.filter(
            status='pending')  # Додаємо надіслані запити
        context['search_query'] = self.request.GET.get('search', '')  # Додаємо пошуковий запит до контексту
        return context

    def post(self, request, *args, **kwargs):
        form = AddFriendForm(request.POST)
        friends = self.get_queryset()  # Отримуємо список друзів для контексту
        friend_requests = self.request.user.received_friend_requests.filter(status='pending')  # Отримуємо запити дружби
        sent_requests = self.request.user.sent_friend_requests.filter(status='pending')  # Отримуємо надіслані запити

        if form.is_valid():
            identifier = form.cleaned_data['identifier']
            friend = None

            # Шукаємо користувача за телефоном або email
            try:
                if "@" in identifier:
                    friend = User.objects.get(email=identifier)
            except User.DoesNotExist:
                form.add_error('identifier', 'Користувача з такою інформацією не знайдено.')

            if friend:
                # Перевіряємо, чи не намагається користувач надіслати запит самому собі
                if friend == request.user:
                    form.add_error('identifier', 'Ви не можете надіслати запит самому собі.')
                else:
                    # Шукаємо існуючий запит на дружбу
                    friend_request, created = FriendRequest.objects.get_or_create(from_user=request.user,
                                                                                  to_user=friend)
                    if friend_request.status in ['rejected', 'accepted']:
                        # Якщо запит був прийнятий або відхилений, дозволяємо надіслати його знову
                        friend_request.status = 'pending'  # Оновлюємо статус
                        friend_request.save()

                    return redirect('friends_list')

        # У разі помилки, залишаємо форму та відображаємо запити
        return render(request, self.template_name, {
            'form': form,
            'friends': friends,
            'friend_requests': friend_requests,
            'sent_requests': sent_requests,
        })


@login_required(login_url='/login/')
def delete_friend(request, friend_id):
    if request.method == "POST":
        friend = get_object_or_404(User, id=friend_id)
        request.user.friends.remove(friend)  # Видаляємо друга зі списку друзів
        return redirect('friends_list')


@login_required(login_url='/login/')
def handle_friend_request(request, request_id):
    # Шукаємо запит на дружбу
    friend_request = get_object_or_404(FriendRequest, id=request_id)

    # Перевіряємо, чи користувач є тим, хто надіслав або отримав запит
    if friend_request.to_user == request.user:
        # Обробляємо прийняття або відхилення запиту
        if request.method == 'POST':
            action = request.POST.get('action')

            if action == 'accept':
                # Додаємо у друзі
                request.user.friends.add(friend_request.from_user)
                friend_request.from_user.friends.add(request.user)
                friend_request.status = 'accepted'
            elif action == 'reject':
                friend_request.status = 'rejected'

            friend_request.save()
    elif friend_request.from_user == request.user:
        # Скасовуємо запит
        if request.method == 'POST':
            friend_request.delete()

    return redirect('friends_list')


@login_required(login_url='/login/')
def create_group(request):
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            # Створюємо нову групу
            group = form.save(commit=False)

            # Якщо зображення не вибрано, встановлюємо випадкове зображення з 5 доступних
            if not group.image:
                # Папка з резервними зображеннями
                image_folder = os.path.join(settings.MEDIA_ROOT, 'default_group_images')

                # Отримуємо всі файли з папки
                available_images = os.listdir(image_folder)

                # Вибір випадкового зображення
                random_image = random.choice(available_images)
                group.image = os.path.join('default_group_images', random_image)

            group.save()

            # Додаємо користувача як адміністратора групи
            GroupMembership.objects.create(
                user=request.user,
                group=group,
                role='admin'  # Статус "Адмін"
            )

            return redirect('group_list')  # Перенаправляємо на список груп
    else:
        form = GroupForm()

    return render(request, 'portal_html/create_group.html', {'form': form})


@login_required(login_url='/login/')
def group_list(request):
    groups = Group.objects.all()
    user_groups = {membership.group.id for membership in GroupMembership.objects.filter(user=request.user)}
    for group in groups:
        group.is_member = group.id in user_groups
    return render(request, 'portal_html/group_list.html', {'groups': groups})


@login_required(login_url='/login/')
def join_group(request, group_id):
    if request.method == "POST":
        group = get_object_or_404(Group, id=group_id)
        if not GroupMembership.objects.filter(user=request.user, group=group).exists():
            GroupMembership.objects.create(user=request.user, group=group)
        return JsonResponse({"message": "Приєднання успішне"}, status=200)
    else:
        return JsonResponse({"error": "Неправильний метод запиту"}, status=400)


@login_required(login_url='/login/')
def leave_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    membership = GroupMembership.objects.filter(user=request.user, group=group).first()

    if not membership:
        return redirect('group_detail', group_id=group.id)

    elif membership.role == 'admin':
        return redirect('group_detail', group_id=group.id)

    else:
        # Видаляємо членство
        membership.delete()
        return redirect('group_list')


@login_required(login_url='/login/')
def group_detail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)
    return render(request, 'portal_html/group_detail.html', {'group': group, 'is_admin': is_admin})


@login_required(login_url='/login/')
def delete_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if not is_group_admin(request.user, group):
        return redirect('group_detail', group_id=group.id)

    group.delete()
    return redirect("group_list")  # Редирект на список груп після видалення



@login_required(login_url='/login/')
def edit_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    membership = group.memberships.filter(user=request.user, role='admin').first()

    # Перевірка, чи є користувач адміністратором
    if not is_group_admin(request.user, group):
        return redirect('group_detail', group_id=group.id)

    if request.method == 'POST':
        form = GroupEditForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            form.save()
            return redirect('group_detail', group_id=group.id)
    else:
        form = GroupEditForm(instance=group)

    return render(request, 'portal_html/edit_group.html', {'form': form, 'group': group})


@login_required(login_url='/login/')
def gallery_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)
    query = request.GET.get('search', '')
    file_type = request.GET.get('file_type', '')

    gallery_items = GalleryItem.objects.filter(group=group)  # Фільтруємо за групою

    if file_type:
        gallery_items = gallery_items.filter(file_type=file_type)

    if query:
        gallery_items = gallery_items.filter(title__icontains=query)

    return render(request, 'portal_html/gallery.html', {
        'group': group,
        'gallery_items': gallery_items,
        'query': query,
        'file_type': file_type,
        'is_admin': is_admin
    })


@login_required(login_url='/login/')
def poll_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)
    search_query = request.GET.get('search', '')
    polls = Poll.objects.filter(group=group)

    if search_query:
        polls = polls.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    return render(request, 'portal_html/poll_list.html', {
        'group': group,
        'polls': polls,
        'is_admin': is_admin
    })


@login_required(login_url='/login/')
def forum_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)
    search_query = request.GET.get('search', '')

    # Початковий queryset постів
    posts = ForumPost.objects.filter(group=group, access='open').order_by('-created_at')

    # Фільтруємо пости за пошуковим запитом
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) | Q(author__first_name__icontains=search_query)
        )

    return render(request, 'portal_html/forum_list.html', {
        'group': group,
        'posts': posts,
        'is_admin': is_admin
    })


@login_required(login_url='/login/')
def notification_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)
    search_query = request.GET.get('q', '')  # Получаем параметр "q" из строки запроса
    notifications = Notification.objects.filter(group=group)

    if search_query:
        notifications = notifications.filter(Q(title__icontains=search_query))

    notifications = notifications.order_by('-created_at')  # Сортируем по дате создания

    return render(request, 'portal_html/notification_list.html', {
        'group': group,
        'notifications': notifications,
        'is_admin': is_admin,
        'search_query': search_query,  # Передаем строку запроса в шаблон
    })


@login_required(login_url='/login/')
def survey_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = is_user_admin_or_moderator(request.user, group)
    search_query = request.GET.get('search', '')
    surveys = Survey.objects.filter(group=group, active_until__gt=timezone.now())
    if search_query:
        surveys = surveys.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    return render(request, 'portal_html/survey_list.html', {
        'group': group,
        'surveys': surveys,
        'is_admin': is_admin
    })


@login_required(login_url='/login/')
def user_news_list(request):
    user_news = UserNews.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'portal_html/user_news_list.html', {'user_news': user_news})


@login_required(login_url='/login/')
def delete_user_news(request, news_id):
    news = get_object_or_404(UserNews, id=news_id)
    if request.user != news.user:
        return redirect('home')
    news.delete()
    return redirect('user_news_list')


@login_required(login_url='/login/')
def delete_member(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    user_to_remove = get_object_or_404(User, id=user_id)
    user_membership = GroupMembership.objects.filter(user=user_to_remove, group=group).first()

    if not user_membership:
        return redirect('admin_panel', group_id=group.id)  # Якщо користувач не є учасником групи, перенаправляємо
    user_membership.delete()
    return redirect('admin_panel', group_id=group.id)


@login_required(login_url='/login/')
def add_members_to_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if not is_user_admin_or_moderator(request.user, group):
        return redirect('group_detail', group_id=group.id)

    if request.method == "POST":
        user_ids = request.POST.getlist('user_ids')
        if user_ids:
            for user_id in user_ids:
                user = get_object_or_404(User, id=user_id)
                GroupMembership.objects.get_or_create(user=user, group=group)
            return redirect('admin_panel', group_id=group.id)

    return redirect('admin_panel', group_id=group.id)








