import base64
from datetime import date, timedelta
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.urls import reverse
from django.views.generic import ListView

from .forms import CustomUserCreationForm, LoginForm, AnswerForm, QuestionForm, SurveyForm, SurveyResponseForm, \
    NotificationForm, ForumPostForm, CommentForm, ForumPostAdditionForm, EventForm, EventEditForm, PollForm, \
    CandidateForm, CandidateEditForm, PollEditForm, GalleryItemForm, AddFriendForm, GroupForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Survey, Question, SurveyResult, Answer, Notification, ForumPost, Comment, ForumAddition, Event, \
    Poll, Vote, Candidate, User, Ban, GalleryItem, FriendRequest, GroupMembership, Group
from django.db import IntegrityError
from datetime import datetime
import calendar
from collections import defaultdict
from django.utils.timezone import now


def home(request):
    return render(request, 'portal_html/home.html')


@login_required
def admin_panel(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    # Перевірка, чи користувач є адміністратором цієї групи
    membership = GroupMembership.objects.filter(user=request.user, group=group, role='admin').first()
    if not membership:
        return redirect('home')  # Перенаправлення для неадмінів

    # Отримання списків користувачів у межах групи
    admins = GroupMembership.objects.filter(group=group, role='admin').select_related('user')
    moderators = GroupMembership.objects.filter(group=group, role='moderator').select_related('user')
    banned_users = User.objects.filter(is_active=False, group_memberships__group=group)

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
                    # Отримання деталей бана
                    message_text = request.POST.get('message')
                    end_date = request.POST.get('end_date')

                    # Створення бану
                    Ban.objects.create(user=user, message=message_text, end_date=end_date)
                    user.is_active = False
                    user.save()
                    message = f"Користувач {user.email} заблокований до {end_date}."

                elif action == 'unban_user':
                    Ban.objects.filter(user=user).delete()  # Видалення бана
                    user.is_active = True
                    user.save()
                    message = f"Користувач {user.email} розблокований."

        except User.DoesNotExist:
            message = "Користувача з такою поштою не знайдено."

    return render(request, 'portal_html/admin_panel.html', {
        'group': group,
        'admins': admins,
        'moderators': moderators,
        'banned_users': banned_users,
        'message': message,
    })


@login_required
def admin_survey_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    membership = GroupMembership.objects.filter(user=request.user, group=group, role='admin').first()
    if not membership:
        return redirect('home')

    surveys = Survey.objects.filter(group=group)
    return render(request, 'portal_html/admin_survey_list.html', {'surveys': surveys, 'group': group, 'is_admin': is_admin})


@login_required
def admin_notification_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    membership = GroupMembership.objects.filter(user=request.user, group=group, role='admin').first()
    if not membership:
        return redirect('home')

    notifications = Notification.objects.filter(group=group)
    return render(request, 'portal_html/admin_notification_list.html', {'notifications': notifications, 'group': group, 'is_admin': is_admin})


@login_required
def admin_event_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    membership = GroupMembership.objects.filter(user=request.user, group=group, role='admin').first()
    if not membership:
        return redirect('home')

    events = Event.objects.filter(group=group)
    return render(request, 'portal_html/admin_event_list.html', {'events': events, 'group': group, 'is_admin': is_admin})


@login_required
def admin_poll_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    membership = GroupMembership.objects.filter(user=request.user, group=group, role='admin').first()
    if not membership:
        return redirect('home')

    polls = Poll.objects.filter(group=group)
    return render(request, 'portal_html/admin_poll_list.html', {'polls': polls, 'group': group, 'is_admin': is_admin})


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
def delete_profile(request):
    if request.method == 'POST':
        request.user.delete()  # Видалення акаунта
        return redirect('home')  # Перенаправлення на головну сторінку
    return redirect('user_profile')

@login_required
def user_profile(request):
    user = request.user
    context = {
        'user': user,
    }
    return render(request, 'portal_html/user_profile.html', context)


@login_required
def create_survey(request, group_id):
    # Отримуємо групу за переданим ID
    group = get_object_or_404(Group, id=group_id)

    # Перевірка, чи є користувач членом групи
    if not GroupMembership.objects.filter(user=request.user, group=group).exists():
        return HttpResponseForbidden("Ви не є членом цієї групи!")

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


@login_required
def create_questions(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    group = survey.group

    # Перевірка, чи користувач є членом групи, до якої належить опитування
    if not GroupMembership.objects.filter(user=request.user, group=survey.group).exists():
        return HttpResponseForbidden("Ви не є членом цієї групи!")

    # Створення форм для кожного питання
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


@login_required
def create_answers(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    group = survey.group
    questions = survey.questions.all()

    # Перевірка, чи користувач є членом групи, до якої належить опитування
    if not GroupMembership.objects.filter(user=request.user, group=survey.group).exists():
        return HttpResponseForbidden("Ви не є членом цієї групи!")

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
        return redirect('home')  # Перенаправлення на домашню сторінку

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


@login_required(login_url='home')
def take_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    group = survey.group # Отримуємо групу через опитування
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

    # Перевірка, чи термін дії опитування ще не завершився
    if survey.active_until < timezone.now():
        return redirect('home')

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
            return redirect('home')
    else:
        form = SurveyResponseForm(questions=questions, initial=initial_answers)

    return render(request, 'portal_html/take_survey.html', {
        'survey': survey,
        'form': form,
        'group': group,
        'is_admin': is_admin# Передаємо групу в контекст
    })


@login_required(login_url='home')
def survey_responses(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    group = survey.group  # Отримуємо групу через опитування
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    survey_results = SurveyResult.objects.filter(survey=survey)

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


@login_required(login_url='home')
def user_survey_responses(request, survey_id, user_id):
    survey = get_object_or_404(Survey, id=survey_id)
    group = survey.group  # Отримуємо групу через опитування
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

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

@login_required
def delete_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    survey.delete()
    return redirect('home')


@login_required
def create_notification(request, group_id):
    group = get_object_or_404(Group, id=group_id)  # Отримуємо групу за ID
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

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


@login_required
def delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)

    # Перевіряємо, чи є у користувача права для видалення
    if request.user.is_staff or request.user == notification.created_by:
        notification.delete()
        return redirect('home')  # Перенаправляємо на список новин
    else:
        # Якщо у користувача немає прав, то редіректимо на домашню сторінку
        return redirect('home')


# Сторінка створення нового посту
@login_required
def create_forum_post(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()# Отримуємо групу за переданим ID

    if request.method == 'POST':
        form = ForumPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user  # Призначаємо автора
            post.group = group  # Прив’язуємо до групи
            post.save()
            return redirect('home')  # Після збереження перенаправляємо на список постів
    else:
        form = ForumPostForm()

    return render(request, 'portal_html/create_forum_post.html', {'form': form, 'group': group, 'is_admin': is_admin})


def forum_post_update(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    group = post.group
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

    # Перевірка, чи користувач є автором посту
    if request.user != post.author:
        return redirect('home')

    if request.method == 'POST':
        form = ForumPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('forum_post_detail', post_id=post.id)
    else:
        form = ForumPostForm(instance=post)

    return render(request, 'portal_html/forum_post_edit.html', {
        'form': form,
        'group': group,
        'is_admin': is_admin,
    })


def forum_post_delete(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)

    # Перевірка, чи користувач є автором посту
    if request.user != post.author:
        return redirect('home')

    if request.method == 'POST':
        post.delete()
        return redirect('forum_list')  # Переходимо на список форумів після видалення


@login_required
def forum_post_detail(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    group = post.group
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    comments = post.comments.filter(parent_comment__isnull=True)
    comment_form = CommentForm()

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
            comment.content = request.POST.get("content")
            comment.save()
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


@login_required
def create_forum_post_addition(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    group = post.group
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

    # Перевірка, чи користувач є автором посту
    if request.user != post.author:
        return redirect('forum_post_detail', post_id=post.id)

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


@login_required
def edit_forum_post_addition(request, update_id):
    update = get_object_or_404(ForumAddition, id=update_id)
    post = update.forum_post
    group = post.group
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

    # Перевірка, чи користувач є автором апдейту
    if request.user != update.forum_post.author:
        return redirect('forum_post_detail', post_id=update.forum_post.id)

    if request.method == 'POST':
        form = ForumPostAdditionForm(request.POST, request.FILES, instance=update)
        if form.is_valid():
            form.save()
            return redirect('forum_post_detail', post_id=update.forum_post.id)
    else:
        form = ForumPostAdditionForm(instance=update)

    return render(request, 'portal_html/edit_addition.html', {'form': form, 'update': update, 'group': group, 'is_admin': is_admin})


@login_required
def delete_addition(request, addition_id):
    addition = get_object_or_404(ForumAddition, id=addition_id)
    post_id = addition.forum_post.id
    post = addition.forum_post

    # Перевірка, чи користувач є автором посту
    if request.user != post.author:
        return redirect('home')

    if request.method == 'POST':
        addition.delete()
        return redirect('forum_post_detail', post_id=post_id)


@login_required
def portfolio_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    projects = ForumPost.objects.filter(status='project', author=request.user, group=group)
    return render(request, 'portal_html/portfolio.html', {'projects': projects, 'group': group, 'is_admin': is_admin})


@login_required
def create_event(request, group_id):
    group = get_object_or_404(Group, id=group_id)  # Отримуємо групу за ID
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

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



@login_required
def calendar_view(request, group_id):
    # Отримуємо групу за ID
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

    # Фільтруємо події, пов'язані з цією групою
    events = Event.objects.filter(group=group, end_time__gte=timezone.now())

    return render(request, 'portal_html/calendar.html', {
        'group': group,
        'events': events,
        'is_admin': is_admin,
    })


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
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

    # Відображаємо список подій
    return render(request, 'portal_html/events_by_date.html', {
        'events': events,
        'date': selected_date,
        'group': group,  # Додаємо групу в контекст
        'is_admin': is_admin,
    })


def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    group = event.group
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    return render(request, 'portal_html/event_detail.html', {'event': event, 'group': group, 'is_admin': is_admin})


@login_required
def delete_event(request, event_id):
    if request.user.is_staff:  # Перевірка, чи користувач є адміністратором
        event = get_object_or_404(Event, id=event_id)
        event.delete()
    return redirect('home')


@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    group = event.group
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

    # Якщо форма була надіслана
    if request.method == 'POST':
        form = EventEditForm(request.POST, instance=event)
        if form.is_valid():
            form.save()  # Зберігаємо зміни
            return redirect('home')  # Перенаправляємо назад до адмін панелі
    else:
        form = EventEditForm(instance=event)  # Заповнюємо форму на основі існуючих даних події

    return render(request, 'portal_html/edit_event.html', {'form': form, 'event': event, 'group': group, 'is_admin': is_admin})


def create_poll_step_1(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

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


def create_poll_step_2(request, poll_id):
    poll = Poll.objects.get(id=poll_id)
    group = poll.group
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    candidates_count = poll.candidate_count

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
            return redirect('home')  # Перенаправляємо на список голосувань

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


@login_required
def vote_poll(request, poll_id):
    poll = get_object_or_404(Poll, id=poll_id)
    group = poll.group
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

    # Перевірка, чи голосування ще не завершилось
    if poll.end_date < timezone.now().date():  # Порівнюємо дати
        return redirect('home')  # Якщо голосування закінчилось, показуємо повідомлення

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

        return redirect('home')  # Після голосування перенаправляємо на список голосувань

    return render(request, 'portal_html/vote_poll.html', {'poll': poll, 'candidates': candidates, 'group': group, 'is_admin': is_admin})


@login_required
def poll_results(request, poll_id):
    poll = Poll.objects.get(id=poll_id)
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
    })


@login_required
def delete_poll(request, poll_id):
    poll = get_object_or_404(Poll, id=poll_id)

    if request.method == 'POST':  # Перевіряємо, що це POST запит
        poll.delete()  # Видаляємо голосування
        return redirect('home')  # Переходимо на адмін панель після видалення

    return redirect('home')



@login_required
def gallery_item_detail(request, item_id):
    gallery_item = get_object_or_404(GalleryItem, id=item_id)
    group = gallery_item.group
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    comments = gallery_item.comments.filter(parent_comment__isnull=True)
    comment_form = CommentForm()

    if request.method == 'POST':

        # Видалення коментаря
        delete_comment_id = request.POST.get("delete_comment_id")
        if delete_comment_id:
            comment_to_delete = get_object_or_404(Comment, id=delete_comment_id, author=request.user)
            comment_to_delete.delete()
            return redirect('gallery_item_detail', item_id=gallery_item.id)

        # Редагування коментаря
        comment_id = request.POST.get("comment_id")
        if comment_id:
            comment = get_object_or_404(Comment, id=comment_id, author=request.user)
            comment.content = request.POST.get("content")
            comment.save()
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


@login_required
def delete_gallery_item(request, item_id):
    item = get_object_or_404(GalleryItem, id=item_id)
    item.delete()
    return redirect('home')


@login_required
def edit_gallery_item(request, item_id):
    item = get_object_or_404(GalleryItem, id=item_id, author=request.user)  # Заміна uploaded_by на author
    group = item.group
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()

    if request.method == 'POST':
        form = GalleryItemForm(request.POST, instance=item)
        if form.is_valid():
            item.title = form.cleaned_data['title']
            item.description = form.cleaned_data['description']
            item.save(update_fields=['title', 'description'])
            return redirect('gallery')
    else:
        form = GalleryItemForm(instance=item)
        form.fields.pop('file')  # При редагуванні файл не можна змінювати

    return render(request, 'portal_html/edit_gallery_item.html', {'form': form, 'item': item, 'group': group, 'is_admin': is_admin})


@login_required
def create_post_gallery(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()# Отримуємо групу за ID

    if request.method == 'POST':
        form = GalleryItemForm(request.POST, request.FILES)
        if form.is_valid():
            gallery_item = form.save(commit=False)
            gallery_item.author = request.user  # Призначаємо автора
            gallery_item.group = group  # Прив’язуємо до групи
            gallery_item.save()
            return redirect('gallery')  # Після збереження перенаправляємо на список галереї
    else:
        form = GalleryItemForm()

    return render(request, 'portal_html/upload_gallery_item.html', {'form': form, 'group': group, 'is_admin': is_admin})


class FriendsView(ListView):
    model = User
    template_name = 'portal_html/friends_list.html'
    context_object_name = 'friends'

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


def delete_friend(request, friend_id):
    if request.method == "POST":
        friend = get_object_or_404(User, id=friend_id)
        request.user.friends.remove(friend)  # Видаляємо друга зі списку друзів
        return redirect('friends_list')


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


@login_required
def create_group(request):
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            # Створюємо нову групу
            group = form.save()

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


@login_required
def group_list(request):
    groups = Group.objects.all()
    user_groups = {membership.group.id for membership in GroupMembership.objects.filter(user=request.user)}
    for group in groups:
        group.is_member = group.id in user_groups
    return render(request, 'portal_html/group_list.html', {'groups': groups})


@login_required
def join_group(request, group_id):
    if request.method == "POST":
        group = get_object_or_404(Group, id=group_id)
        if not GroupMembership.objects.filter(user=request.user, group=group).exists():
            GroupMembership.objects.create(user=request.user, group=group)
        return JsonResponse({"message": "Приєднання успішне"}, status=200)
    return JsonResponse({"error": "Неправильний метод запиту"}, status=400)


def group_detail(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    return render(request, 'portal_html/group_detail.html', {'group': group, 'is_admin': is_admin})


def gallery_view(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
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


def poll_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    polls = Poll.objects.filter(group=group)  # Фільтруємо за групою
    return render(request, 'portal_html/poll_list.html', {'group': group, 'polls': polls, 'is_admin': is_admin})


def forum_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    posts = ForumPost.objects.filter(group=group, access='open').order_by('-created_at')  # Фільтруємо за групою
    return render(request, 'portal_html/forum_list.html', {'group': group, 'posts': posts, 'is_admin': is_admin})


def notification_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    notifications = Notification.objects.filter(group=group).order_by('-created_at')  # Фільтруємо за групою
    return render(request, 'portal_html/notification_list.html', {'group': group, 'notifications': notifications, 'is_admin': is_admin})


def survey_list(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    is_admin = GroupMembership.objects.filter(user=request.user, group=group, role='admin').exists()
    surveys = Survey.objects.filter(group=group, active_until__gt=timezone.now())  # Фільтруємо за групою
    return render(request, 'portal_html/survey_list.html', {'group': group, 'surveys': surveys, 'is_admin': is_admin})



