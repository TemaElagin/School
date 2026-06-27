from django.shortcuts import render, redirect
from .forms import RegistrationForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from .decorators import teacher_only, super_teacher_only
from django.http import HttpResponse

def index(request):
    return HttpResponse("Интерфейс Студента / Главная страница")

@teacher_only
def teacher_dashboard(request):
    return HttpResponse("Интерфейс Учителя: тут будет форма добавления уроков и список на проверку")

@super_teacher_only
def super_teacher_dashboard(request):
    return HttpResponse("Интерфейс СуперУчителя: полный доступ")

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = RegistrationForm()
    return render(request, 'main/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Проверяем роль в профиле и редиректим на соответствующие страницы
            if hasattr(user, 'profile'):
                role = user.profile.role
                if role == 'super_teacher':
                    return redirect('super_teacher_dashboard')
                elif role == 'teacher':
                    return redirect('teacher_dashboard')
                elif role == 'student':
                    return redirect('index')  # Студента кидает на главную

            return redirect('index')  # На всякий случай, если профиля нет
    else:
        form = AuthenticationForm()
    return render(request, 'main/login.html', {'form': form})

