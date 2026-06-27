from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('super-teacher/', views.super_teacher_dashboard, name='super_teacher_dashboard'),
]