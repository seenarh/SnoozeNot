from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Sum, Q
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from datetime import date, datetime, time
from django.shortcuts import render
from .models import Task
from .forms import SignUpForm, LoginForm
import json


def Home_view(request):
    return render(request, "UserAuth/home.html")


def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
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
    return redirect("UserAuth:login")

from django.utils import timezone
from django.db.models import Q

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from .models import Task

@login_required
def Dashboard_view(request):
    today = timezone.localdate()
    
    # Include tasks due today OR tasks with no due_time
    today_tasks = Task.objects.filter(
        user=request.user,
        completed=False
    ).filter(
        Q(due_time__date=today) | Q(due_time__isnull=True)
    ).order_by('due_time')

    tasks_remaining_count = today_tasks.count()
    
    inbox_count = Task.objects.filter(user=request.user, completed=False).count()
    
    return render(request, 'UserAuth/dashboard.html', {
        'today_tasks': today_tasks,
        'tasks_remaining_count': tasks_remaining_count,
        'inbox_count': inbox_count,
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
        due_time = request.POST.get("end_datetime")

        # 1️⃣ Create the Task
        task = Task.objects.create(
            user=request.user,
            title=title,
            details=details,
            categories=category,
            due_time=due_time,
        )

        
        return redirect('UserAuth:Inbox')

    return render(request, "UserAuth/add_task.html")

@login_required
@require_POST
def toggle_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.completed = not task.completed
    task.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'completed': task.completed})
    return redirect('UserAuth:Dashboard')


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
from django.utils.dateparse import parse_datetime  # <- import this
from .models import Task

@login_required
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        details = request.POST.get('details', '').strip()
        end_datetime_str = request.POST.get('end_datetime')

        if title:
            task.title = title
            task.details = details

            if end_datetime_str:
                dt = parse_datetime(end_datetime_str)
                task.due_time = dt

            task.save()
            return redirect('UserAuth:Inbox')  # redirect to inbox or task list

    return render(request, 'UserAuth/edit_task.html', {'task': task})


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

@login_required
def upcoming_view(request):
    today = timezone.localdate()

    tasks = Task.objects.filter(
        user=request.user,
        completed=False,
        due_time__isnull=False,
        due_time__date__gt=today
    ).order_by('due_time')

    return render(
        request,
        "userauth/Upcoming.html",
        {
            "tasks": tasks,
            "title": "Upcoming"
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
