from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('super-teacher/', views.super_teacher_dashboard, name='super_teacher_dashboard'),
    path('lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('lesson/<int:lesson_id>/manage-test/', views.manage_test, name='manage_test')
]