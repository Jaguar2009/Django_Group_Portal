from datetime import date

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from .forms import CustomUserCreationForm, LoginForm, AnswerForm, QuestionForm, SurveyForm, SurveyResponseForm, \
    NotificationForm, ForumPostForm, CommentForm, ForumPostAdditionForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Survey, Question, SurveyResult, Answer, Notification, ForumPost, Comment, ForumAddition, Event, \
    Vote, Poll, Question_Poll
from django.db import IntegrityError


def home(request):
    events = Event.objects.filter(date__gte=date.today()).order_by('date', 'time')
    return render(request, 'portal_html/home.html', {'events': events})

@login_required
def admin_panel(request):
    # Перевірка, чи користувач є адміністратором
    if request.user.status == 'admin':
        surveys = Survey.objects.all()  # Отримуємо всі опитування
        notifications = Notification.objects.all()  # Отримуємо всі оголошення
        return render(request, 'portal_html/admin_panel.html', {
            'surveys': surveys,
            'notifications': notifications  # Передаємо оголошення в шаблон
        })
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
def create_survey(request):
    if request.method == 'POST':
        survey_form = SurveyForm(request.POST, request.FILES)
        notification_form = NotificationForm(request.POST, request.FILES)

        # Перевіряємо валідність форм
        if survey_form.is_valid() and notification_form.is_valid():
            # Зберігаємо опитування
            survey = survey_form.save()

            # Зберігаємо новину
            notification = notification_form.save(commit=False)
            notification.save()

            # Перенаправляємо на сторінку для створення питань
            return redirect('create_questions', survey_id=survey.id)
    else:
        survey_form = SurveyForm()
        notification_form = NotificationForm()

    return render(request, 'portal_html/create_survey.html',
                  {'survey_form': survey_form, 'notification_form': notification_form})

def create_questions(request, survey_id):
    survey = Survey.objects.get(id=survey_id)
    question_forms = [QuestionForm(prefix=f'question_{i}') for i in range(survey.question_count)]

    if request.method == 'POST':
        question_forms = [QuestionForm(request.POST, request.FILES, prefix=f'question_{i}') for i in range(survey.question_count)]
        all_valid = True

        for i in range(survey.question_count):
            question_form = question_forms[i]
            if question_form.is_valid():
                question = question_form.save(commit=False)
                question.survey = survey
                question.save()
            else:
                all_valid = False

        if all_valid:
            return redirect('create_answers', survey_id=survey.id)

    return render(request, 'portal_html/create_questions.html', {'forms': question_forms, 'survey': survey})


def create_answers(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    questions = survey.questions.all()

    if request.method == 'POST':
        answer_forms = []
        for question in questions:
            for i in range(question.answer_count):
                form = AnswerForm(request.POST, request.FILES, prefix=f'answer_{question.id}_{i}')
                if form.is_valid():
                    answer = form.save(commit=False)
                    answer.question = question
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
    })

def survey_list(request):
    surveys = Survey.objects.filter(active_until__gt=timezone.now())
    return render(request, 'portal_html/survey_list.html', {'surveys': surveys})


@login_required(login_url='home')
def take_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)

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

    return render(request, 'portal_html/take_survey.html', {'survey': survey, 'form': form})


def survey_responses(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
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
    }
    return render(request, 'portal_html/survey_responses.html', context)


@login_required(login_url='home')
def user_survey_responses(request, survey_id, user_id):
    survey = get_object_or_404(Survey, id=survey_id)

    # Перевірка, чи користувач є власником відповіді
    if request.user.id != user_id and not request.user.is_staff:
        return redirect('home')  # Перенаправлення на домашню сторінку, якщо користувач не власник і не адмін

    user_responses = SurveyResult.objects.filter(survey=survey, user_id=user_id)

    return render(request, 'portal_html/user_survey_responses.html', {
        'survey': survey,
        'user_responses': user_responses,
    })

@login_required
def delete_survey(request, survey_id):
    if request.user.status == 'admin':
        survey = get_object_or_404(Survey, id=survey_id)
        survey.delete()
    return redirect('admin_panel')

@login_required
def create_notification(request):
    if request.method == 'POST':
        form = NotificationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()  # Зберігаємо новину в базу даних
            return redirect('notification_list')  # Перенаправлення на сторінку новин
    else:
        form = NotificationForm()

    return render(request, 'portal_html/create_notification.html', {'form': form})


def notification_list(request):
    notifications = Notification.objects.all().order_by('-created_at')  # Відображаємо новини в порядку спадання
    return render(request, 'portal_html/notification_list.html', {'notifications': notifications})


@login_required
def delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id)

    # Перевіряємо, чи є у користувача права для видалення
    if request.user.is_staff or request.user == notification.created_by:
        notification.delete()
        return redirect('admin_panel')  # Перенаправляємо на список новин
    else:
        # Якщо у користувача немає прав, то редіректимо на домашню сторінку
        return redirect('home')


# Сторінка перегляду форумів
def forum_list(request):
    # Відображаються лише відкриті пости
    posts = ForumPost.objects.filter(access='open').order_by('-created_at')
    return render(request, 'portal_html/forum_list.html', {'posts': posts})



# Сторінка створення нового посту
@login_required
def create_forum_post(request):
    if request.method == 'POST':
        form = ForumPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user  # Призначаємо автора
            post.save()
            return redirect('forum_list')  # Після збереження перенаправляємо на сторінку перегляду
    else:
        form = ForumPostForm()
    return render(request, 'portal_html/create_forum_post.html', {'form': form})


def forum_post_update(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)

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
    })


@login_required
def create_forum_post_addition(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)

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

    return render(request, 'portal_html/create_addition.html', {'post': post, 'form': form})


@login_required
def edit_forum_post_addition(request, update_id):
    update = get_object_or_404(ForumAddition, id=update_id)

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

    return render(request, 'portal_html/edit_addition.html', {'form': form, 'update': update})


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
def portfolio_view(request):
    # Відображаються всі проекти незалежно від їхнього доступу
    projects = ForumPost.objects.filter(status='project', author=request.user)
    return render(request, 'portal_html/portfolio.html', {'projects': projects})



def poll_detail(request, poll_id):
    poll = get_object_or_404(Poll, id=poll_id)
    questions = Question_Poll.objects.filter(poll=poll)
    user = request.user
    user_votes = Vote.objects.filter(user=user, question__poll=poll)
    voted_question_ids = user_votes.values_list('question_id', flat=True)
    has_voted = user_votes.exists()

    if request.method == 'POST':

        if 'vote' in request.POST:
            question_id = int(request.POST.get('vote'))
            question = get_object_or_404(Question_Poll, id=question_id)

            if has_voted:

                old_vote = user_votes.first()
                old_vote.delete()

                old_question = old_vote.question
                old_question.votes -= 1
                old_question.save()

            Vote.objects.create(user=user, question=question)

            question.votes += 1
            question.save()

            return redirect('poll_detail', poll_id=poll.id)


        elif 'unvote' in request.POST:
            question_id = int(request.POST.get('unvote'))
            question = get_object_or_404(Question_Poll, id=question_id)

            vote = user_votes.filter(question=question).first()
            if vote:
                vote.delete()
                question.votes -= 1
                question.save()

            return redirect('poll_detail', poll_id=poll.id)

    return render(request, 'portal_html/poll_detail.html', {
        'poll': poll,
        'questions': questions,
        'voted_question_ids': voted_question_ids,
        'has_voted': has_voted,
    })


def poll_list(request):
    polls = Poll.objects.all()
    return render(request, 'portal_html/poll_list.html', {'polls': polls})


def event_detail(request, id):
    event = get_object_or_404(Event, id=id)
    return render(request, 'portal_html/event_detail.html', {'event': event})


def events_json(request):
    room_type = request.GET.get('room_type', None)
    events = Event.objects.all()


    events_list = []
    for event in events:
        events_list.append({
            'title': event.title,
            'start': event.date.isoformat(),
            'url': f'/events/{event.id}/'
        })

    return JsonResponse(events_list, safe=False)

def calendar_view(request):
    # Группируем события по дате
    events_by_date = Event.objects.all().order_by('date', 'time')
    return render(request, 'portal_html/calendar.html', {'events_by_date': events_by_date})

