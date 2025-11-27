from django.urls import path
from . import views

app_name = "UserAuth"

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path('dashboard/', views.Dashboard_view, name='Dashboard'),
    path('todo/',views.todo_list, name="todo_list"),
    path('add/',views.add_task, name="add_task"),
    path('toggle-task/<int:pk>/',views.toggle_task,name="toggle_task"),
    path('start_session', views.start_session, name='start_session'),
    path('end_session', views.end_session, name='end_session'),
    path('delete_task/<int:pk>/', views.delete_task, name='delete_task'),
    path('Inbox/',views.Inbox_view, name='Inbox'),
    path('today/',views.Today_view, name='Today'),
    path('upcoming/',views.upcoming_view, name='Upcoming'),
    path('completed/',views.completed_view, name='Completed'),
]