from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
    path('super-teacher/', views.super_teacher_dashboard, name='super_teacher_dashboard'),
    path('lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('lesson/<int:lesson_id>/manage-test/', views.manage_test, name='manage_test'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('lesson/<int:lesson_id>/edit/', views.edit_lesson, name='edit_lesson'),
    path('submission/<int:submission_id>/check/', views.check_submission, name='check_submission'),
    path('logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
]
