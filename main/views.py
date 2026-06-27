from django.shortcuts import render
from .models import Course

def index(request):
    courses = Course.objects.all()  # Берем все записи из таблицы Course
    return render(request, 'main/index.html', {'courses': courses})