from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Sum, Q
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, datetime, time, timedelta
from django.shortcuts import render
from .models import Task, FocusLog
from .forms import SignUpForm, LoginForm
from .reminders import parse_posted_datetime, local_due_parts, process_due_reminders, format_minutes
from .email_utils import reminder_delivery_message, scheduled_reminder_message, smtp_is_configured
import json


def Home_view(request):
    return render(request, "userauth/Home.html")


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect("UserAuth:Dashboard")
    else:
        form = SignUpForm()
    return render(request, "UserAuth/signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("UserAuth:Dashboard")
    else:
        form = LoginForm()
    return render(request, "UserAuth/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("home")

from django.utils import timezone
from django.db.models import Q

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from .models import Task

@login_required
def Dashboard_view(request):
    now = timezone.now()
    today = timezone.localdate()
    pending = Task.objects.filter(user=request.user, completed=False)

    overdue_tasks = list(pending.filter(due_time__date__lt=today).order_by('due_time'))
    today_tasks = list(pending.filter(due_time__date=today).order_by('due_time'))
    today_count = pending.filter(due_time__date=today).count()
    inbox_count = pending.count()
    completed_count = Task.objects.filter(user=request.user, completed=True).count()

    day_plan_tasks = list(
        Task.objects.filter(user=request.user, due_time__date=today).order_by('due_time', 'id')
    )
    plan_done_count = sum(1 for task in day_plan_tasks if task.completed)
    plan_total = len(day_plan_tasks)
    today_progress = int(round((plan_done_count / plan_total) * 100)) if plan_total else 0
    finished_today = Task.objects.filter(
        user=request.user, completed=True, completed_at__date=today,
    ).count()

    focus_minutes_today = (
        FocusLog.objects.filter(user=request.user, created_at__date=today)
        .aggregate(total=Sum('minutes'))['total'] or 0
    )

    week_days = []
    week_max = 1
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        done = Task.objects.filter(
            user=request.user, completed=True, completed_at__date=day,
        ).count()
        week_max = max(week_max, done)
        week_days.append({'label': day.strftime('%a'), 'done': done, 'is_today': day == today})
    for day in week_days:
        day['height'] = int(round((day['done'] / week_max) * 100)) if day['done'] else 6

    next_task = overdue_tasks[0] if overdue_tasks else None
    if next_task is None and today_tasks:
        next_task = today_tasks[0]
    if next_task is None:
        next_task = pending.filter(due_time__isnull=False).order_by('due_time').first()

    coming_up_task = pending.filter(due_time__date__gt=today).order_by('due_time').first()
    if coming_up_task and next_task and coming_up_task.id == next_task.id:
        coming_up_task = None

    hour = timezone.localtime(now).hour
    name = (request.user.first_name or request.user.username).strip()
    if hour < 12:
        greeting = f'Good morning, {name}'
    elif hour < 17:
        greeting = f'Good afternoon, {name}'
    else:
        greeting = f'Good evening, {name}'

    overdue_count = len(overdue_tasks)
    if overdue_count:
        label = 'task' if overdue_count == 1 else 'tasks'
        subtitle = f'{overdue_count} overdue {label}. Start with those.'
    elif today_count:
        label = 'task' if today_count == 1 else 'tasks'
        subtitle = f'{today_count} due today.'
    elif next_task:
        subtitle = 'Nothing due today — your next task is lined up.'
    else:
        subtitle = "You're all caught up."

    return render(request, 'UserAuth/dashboard.html', {
        'greeting': greeting,
        'subtitle': subtitle,
        'today': today,
        'overdue_tasks': overdue_tasks,
        'today_tasks': today_tasks,
        'tasks_remaining_count': overdue_count + len(today_tasks),
        'today_count': today_count,
        'inbox_count': inbox_count,
        'completed_count': completed_count,
        'next_task': next_task,
        'next_task_overdue': bool(next_task and next_task.due_time and next_task.due_time < now),
        'coming_up_task': coming_up_task,
        'day_plan_tasks': day_plan_tasks,
        'plan_done_count': plan_done_count,
        'plan_total': plan_total,
        'today_progress': today_progress,
        'finished_today': finished_today,
        'focus_minutes_today': focus_minutes_today,
        'focus_time_label': format_minutes(focus_minutes_today),
        'week_days': week_days,
    })

@login_required
def todo_list(request):
    tasks = Task.objects.filter(user=request.user).order_by('-due_time')

    # handle new task
    if request.method == 'POST': 
        title = request.POST.get('title')
        details = request.POST.get('details')
        due_time = request.POST.get('due_time')
        created_at = request.POST.get('start_time')
        category = request.POST.get('categories', 'inbox')
        
        if title:
            Task.objects.create(
                user=request.user,
                title=title,
                details=details,
                categories=category,
                due_time=due_time,
            ) 
        return redirect('UserAuth:todo_list')

    return render(request, 'UserAuth/todo_list.html', {'tasks': tasks})

@login_required
def Inbox_view(request):
    # Get all incomplete tasks for the logged-in user
    tasks = Task.objects.filter(user=request.user,
                                 completed=False).order_by('-due_time')


    return render(request, 'UserAuth/Inbox.html', {'tasks': tasks})


@login_required
def add_task(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        details = request.POST.get("details", "").strip()
        category = request.POST.get("category", "work")
        due_time = parse_posted_datetime(request.POST)

        task = Task.objects.create(
            user=request.user,
            title=title,
            details=details,
            categories=category,
            due_time=due_time,
        )

        if due_time and not request.user.email:
            messages.warning(
                request,
                'Add an email to your account to receive reminder notifications.',
            )
        elif due_time:
            if due_time > timezone.now():
                msg = scheduled_reminder_message(timezone.localtime(due_time))
                if smtp_is_configured():
                    messages.success(request, msg)
                else:
                    messages.warning(request, msg)
            else:
                sent = process_due_reminders()
                msg = reminder_delivery_message(sent)
                if msg:
                    if smtp_is_configured():
                        messages.success(request, msg)
                    else:
                        messages.warning(request, msg)

        return redirect('UserAuth:Inbox')

    return render(request, "UserAuth/add_task.html")

@login_required
@require_POST
def toggle_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.completed = not task.completed
    task.completed_at = timezone.now() if task.completed else None
    task.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'completed': task.completed})
    return redirect('UserAuth:Dashboard')


@login_required
@require_POST
def log_focus(request):
    try:
        payload = json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        payload = {}

    try:
        minutes = int(payload.get('minutes') or 0)
    except (TypeError, ValueError):
        minutes = 0
    if minutes < 1:
        return JsonResponse({'ok': False, 'error': 'too_short'}, status=400)
    minutes = min(minutes, 180)

    task = None
    task_id = payload.get('task_id')
    if task_id:
        task = Task.objects.filter(pk=task_id, user=request.user).first()
        if task:
            task.focused_minutes = (task.focused_minutes or 0) + minutes
            task.save(update_fields=['focused_minutes'])

    FocusLog.objects.create(user=request.user, task=task, minutes=minutes)
    today = timezone.localdate()
    total = (
        FocusLog.objects.filter(user=request.user, created_at__date=today)
        .aggregate(total=Sum('minutes'))['total'] or 0
    )
    return JsonResponse({
        'ok': True,
        'focus_minutes_today': total,
        'focus_label': f'{format_minutes(total)} focused today',
    })


# @login_required
# @require_POST
# def start_session(request):
#     payload = json.loads(request.body.decode() or '{}')
#     task_id = payload.get('task_id')
#     task = None

#     if task_id:
#         try:
#             task = Task.objects.get(pk=int(task_id), user=request.user)
#         except Task.DoesNotExist:
#             task = None

#     s = FocusSession.objects.create(
#         task=task,
#         user=request.user,
#         start_time=timezone.now()
#     )
#     return JsonResponse({'session_id': s.id, 'start_time': s.start_time.isoformat()})


# @login_required
# @require_POST
# def end_session(request, session_id):
#     session = get_object_or_404(FocusSession, pk=session_id, user=request.user)
#     session.end_session()
#     return JsonResponse({'ok': True, 'minutes': session.minutes or 0})


@login_required
@require_POST
def delete_task(request, pk): 
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.delete()
    return JsonResponse({'ok': True})

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .models import Task

@login_required
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        details = request.POST.get('details', '').strip()

        if title:
            task.title = title
            task.details = details

            due_date = request.POST.get('due_date', '').strip()
            due_time_str = request.POST.get('due_time', '').strip()

            if due_date and due_time_str:
                dt = parse_posted_datetime(request.POST)
                due_changed = task.due_time != dt
                if due_changed:
                    task.reminder_sent = False
                task.due_time = dt
            else:
                task.due_time = None
                task.reminder_sent = False

            task.save()
            sent = process_due_reminders()

            if task.due_time and not request.user.email:
                messages.warning(
                    request,
                    'Add an email to your account to receive reminder notifications.',
                )
            elif task.due_time:
                if task.due_time > timezone.now():
                    msg = scheduled_reminder_message(timezone.localtime(task.due_time))
                    if smtp_is_configured():
                        messages.success(request, msg)
                    else:
                        messages.warning(request, msg)
                else:
                    msg = reminder_delivery_message(sent)
                    if msg:
                        if smtp_is_configured():
                            messages.success(request, msg)
                        else:
                            messages.warning(request, msg)

            return redirect('UserAuth:Inbox')

    value_date, value_time = local_due_parts(task.due_time)
    return render(request, 'UserAuth/edit_task.html', {
        'task': task,
        'value_date': value_date,
        'value_time': value_time,
    })


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from .models import Task

@login_required
def today_view(request):
    today = timezone.localdate()

    tasks = Task.objects.filter(
        user=request.user,
        completed=False
    ).filter(due_time__date=today).order_by('-due_time')
    
    return render(
        request,
        "userauth/Today.html",
        {
            "tasks": tasks,
            "title": "Today"
        }
    )

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Task

def _day_heading(day, today):
    if day == today:
        return 'Today'
    if day == today + timedelta(days=1):
        return 'Tomorrow'
    return day.strftime('%A, %b %d')


def group_tasks_by_day(tasks, today):
    groups = []
    current_day = None
    bucket = []
    for task in tasks:
        day = timezone.localtime(task.due_time).date()
        if current_day is not None and day != current_day:
            groups.append({'label': _day_heading(current_day, today), 'tasks': bucket})
            bucket = []
        current_day = day
        bucket.append(task)
    if bucket:
        groups.append({'label': _day_heading(current_day, today), 'tasks': bucket})
    return groups


@login_required
def upcoming_view(request):
    today = timezone.localdate()
    tasks = list(
        Task.objects.filter(
            user=request.user,
            completed=False,
            due_time__gt=timezone.now(),
        ).order_by('due_time')
    )

    return render(
        request,
        "userauth/Upcoming.html",
        {
            "title": "Upcoming",
            "task_groups": group_tasks_by_day(tasks, today),
        }
    )

@login_required
def completed_view(request):
    tasks = Task.objects.filter(user=request.user, completed=True).order_by('-due_time')
    return render(request, 'UserAuth/Completed.html', {'tasks': tasks, 'title': 'Completed'})

@login_required
def dashboard(request):
    today = timezone.localdate()
    
    # Count tasks by category
    today_count = Task.objects.filter(user=request.user, completed=False).filter(
        Q(created_at__date=today) | Q(due_time__date=today)
    ).count()
    
    upcoming_count = Task.objects.filter(user=request.user, completed=False).filter(
        due_time__date__gt=today
    ).count()
    
    completed_count = Task.objects.filter(user=request.user, completed=True).count()
    
    inbox_count = today_count + upcoming_count  # or just pending tasks
    
    context = {
        'today_count': today_count,
        'upcoming_count': upcoming_count,
        'completed_count': completed_count,
        'inbox_count': inbox_count,
    }
    return render(request, 'userauth/dashboard.html', context)
