from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from datetime import date 
from django.shortcuts import render


from .models import Task, FocusSession
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

@login_required
def Dashboard_view(request):
    user_tasks = Task.objects.filter(user=request.user)
    
    # 1. Base Statistics Calculations
    total_tasks = user_tasks.count()
    tasks_done = user_tasks.filter(completed=True).count()
    
    # Time/Distraction (Aggregating across ALL tasks, consider focusing only on recent/relevant ones)
    time_focused = user_tasks.aggregate(total=Sum('focused_minutes'))['total'] or 0
    distraction_count = user_tasks.aggregate(total=Sum('distraction_count'))['total'] or 0

    # 2. Focus Streak & Sessions Logic
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    sessions = FocusSession.objects.filter(
        user=request.user,
        start_time__gte=thirty_days_ago,
        minutes__gt=0
    )
    streak_days = sessions.dates('start_time', 'day').count()

    # 3. WIDGET-SPECIFIC DATA FOR YOUR DESIGNED WIDGETS
    
    # a) Inbox Item Counter Data
    inbox_count = user_tasks.filter(categories='inbox', completed=False).count()
    
    # b) Today's Task Quick View Data
    # Get active tasks due today/overdue
    today_tasks_list = user_tasks.filter(
        completed=False,
        due_time__lte=timezone.now().date() # Due today or overdue
    ).order_by('due_time')[:5]
    
    tasks_remaining_count = user_tasks.filter(completed=False).count() # Total active tasks

    # 4. Create and Pass the FULL Context
    context = {
        # Base Data
        'Username': request.user.username,
        'total_tasks': total_tasks,
        'tasks_done': tasks_done,
        'time_focused': time_focused,
        'distraction_count': distraction_count,
        'streak_days': streak_days,
        
        # Widget Data
        'inbox_count': inbox_count,
        'sprints_completed': sessions.count(), # Total sessions completed in the last 30 days
        'total_focus_time_30_days': sessions.aggregate(total=Sum('minutes'))['total'] or 0,
        
        # Quick View Data
        'today_tasks': today_tasks_list,
        'tasks_remaining_count': tasks_remaining_count,
    }
    
    # CORRECT RENDER CALL: Pass the single 'context' dictionary
    return render(request, 'UserAuth/Dashboard.html', context)

@login_required
def todo_list(request):
    tasks = Task.objects.filter(user=request.user).order_by('-created_at')

    # handle new task
    if request.method == 'POST':
        title = request.POST.get('title')
        details = request.POST.get('details')
        due_time = request.POST.get('due_time')
        category = request.POST.get('categories', 'inbox')
        
        if title:
            Task.objects.create(
                user=request.user,
                title=title,
                details=details,
                categories=category,
                due_time=due_time if due_time else None,
            ) 
        return redirect('UserAuth:todo_list')

    return render(request, 'UserAuth/todo_list.html', {'tasks': tasks})

@login_required
def Inbox_view(request):
    # Get all incomplete tasks for the logged-in user
    tasks = Task.objects.filter(user=request.user, completed=False).order_by('-created_at')

    # Attach the latest session (if any) to each task
    for task in tasks:
        latest_session = task.sessions.order_by('-start_time').first()  # could be None
        task.latest_session = latest_session

    return render(request, 'UserAuth/Inbox.html', {'tasks': tasks})


@login_required
def add_task(request):
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        details = request.POST.get("details", "").strip()
        category = request.POST.get("category", "work")
        
        start_time = request.POST.get("start_datetime")
        end_time = request.POST.get("end_datetime")

        # 1️⃣ Create the Task
        task = Task.objects.create(
            user=request.user,
            title=title,
            details=details,
            categories=category,
        )

        # 2️⃣ Create a FocusSession using chosen start/end time
        if start_time:
            FocusSession.objects.create(
                user=request.user,
                task=task,
                start_time=start_time,
                end_time=end_time
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


@login_required
@require_POST
def start_session(request):
    payload = json.loads(request.body.decode() or '{}')
    task_id = payload.get('task_id')
    task = None

    if task_id:
        try:
            task = Task.objects.get(pk=int(task_id), user=request.user)
        except Task.DoesNotExist:
            task = None

    s = FocusSession.objects.create(
        task=task,
        user=request.user,
        start_time=timezone.now()
    )
    return JsonResponse({'session_id': s.id, 'start_time': s.start_time.isoformat()})


@login_required
@require_POST
def end_session(request, session_id):
    session = get_object_or_404(FocusSession, pk=session_id, user=request.user)
    session.end_session()
    return JsonResponse({'ok': True, 'minutes': session.minutes or 0})


@login_required
@require_POST
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.delete()
    return JsonResponse({'ok': True})

@login_required
@require_POST
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    title = request.POST.get('title', '').strip()
    details = request.POST.get('details', '').strip()   
    return render(request, 'UserAuth/edit_task.html', {'task': task})
    
# views.py
from django.shortcuts import render
from django.utils import timezone
from datetime import datetime, time
from .models import Task
from django.contrib.auth.decorators import login_required

@login_required
def Today_view(request):
    # get the current local date
    today = timezone.localdate()

    # define start and end of today in local time
    start_of_day = datetime.combine(today, time.min)  # 00:00:00
    end_of_day = datetime.combine(today, time.max)    # 23:59:59.999999

    # make them timezone-aware
    start_of_day = timezone.make_aware(start_of_day)
    end_of_day = timezone.make_aware(end_of_day)

    # filter tasks due anytime today
    tasks = Task.objects.filter(
        user=request.user,
        due_time__range=(start_of_day, end_of_day)
    ).order_by('due_time')

    return render(request, 'UserAuth/Today.html', {'tasks': tasks})

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Task

@login_required
def today_view(request):
    today = timezone.localdate()
    tasks = Task.objects.filter(
        user=request.user,
        completed=False,
        due_time__date=today
    ).order_by('due_time')
    return render(request, 'UserAuth/Today.html', {'tasks': tasks, 'title': 'Today'})

@login_required
def upcoming_view(request):
    today = timezone.localdate()
    tasks = Task.objects.filter(user=request.user, due_time__date__gt=today, completed=False).order_by('due_time')
    return render(request, "userauth/Upcoming.html", {"tasks": tasks})

@login_required
def completed_view(request):
    tasks = Task.objects.filter(user=request.user, completed=True).order_by('-created_at')
    return render(request, "userauth/Completed.html", {"tasks": tasks})
# ...existing code...