from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from .models import Lesson, Course, Profile
from .forms import RegistrationForm, TeacherLessonCreateForm, SuperLessonCreateForm, CourseCreateForm, \
    EditAllowedStudentsForm
from .decorators import teacher_only, super_teacher_only


def index(request):
    if request.user.is_authenticated:
        allowed_lessons = Lesson.objects.filter(
            Q(status='public') |
            Q(status='private', allowed_students=request.user)
        )
    else:
        allowed_lessons = Lesson.objects.filter(status='public')

    lessons = allowed_lessons.filter(course__isnull=True).distinct()
    courses = Course.objects.all()

    return render(request, 'main/index.html', {
        'lessons': lessons,
        'courses': courses
    })


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

            if hasattr(user, 'profile'):
                role = user.profile.role
                if role == 'super_teacher':
                    return redirect('super_teacher_dashboard')
                elif role == 'teacher':
                    return redirect('teacher_dashboard')
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'main/login.html', {'form': form})


# 2. ИНТЕРФЕЙС ОБЫЧНОГО УЧИТЕЛЯ
@teacher_only
def teacher_dashboard(request):
    if request.method == 'POST':
        form = TeacherLessonCreateForm(request.POST)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.author = request.user
            lesson.status = 'lock'
            lesson.save()
            form.save_m2m()
            return redirect('teacher_dashboard')
    else:
        form = TeacherLessonCreateForm()

    lessons = Lesson.objects.all().exclude(status='superlock')

    return render(request, 'main/teacher_dashboard.html', {
        'form': form,
        'lessons': lessons
    })


@super_teacher_only
def super_teacher_dashboard(request):
    lesson_form = SuperLessonCreateForm()
    course_form = CourseCreateForm()

    if request.method == 'POST':
        if 'create_lesson' in request.POST:
            lesson_form = SuperLessonCreateForm(request.POST)
            if lesson_form.is_valid():
                lesson = lesson_form.save(commit=False)
                lesson.author = request.user
                lesson.save()
                lesson_form.save_m2m()
                return redirect('super_teacher_dashboard')

        elif 'create_course' in request.POST:
            course_form = CourseCreateForm(request.POST)
            if course_form.is_valid():
                course_form.save()
                return redirect('super_teacher_dashboard')

        elif 'delete_lesson' in request.POST:
            lesson_id = request.POST.get('lesson_id')
            try:
                Lesson.objects.get(id=lesson_id).delete()
            except Lesson.DoesNotExist:
                pass
            return redirect('super_teacher_dashboard')

        elif 'change_status' in request.POST:
            lesson_id = request.POST.get('lesson_id')
            new_status = request.POST.get('new_status')
            try:
                lesson = Lesson.objects.get(id=lesson_id)
                lesson.status = new_status
                lesson.save()
            except Lesson.DoesNotExist:
                pass
            return redirect('super_teacher_dashboard')

        elif 'change_course' in request.POST:
            lesson_id = request.POST.get('lesson_id')
            course_id = request.POST.get('course_id')
            try:
                lesson = Lesson.objects.get(id=lesson_id)
                if course_id:
                    lesson.course = Course.objects.get(id=course_id)
                else:
                    lesson.course = None
                lesson.save()
            except (Lesson.DoesNotExist, Course.DoesNotExist):
                pass
            return redirect('super_teacher_dashboard')

        elif 'change_allowed_students' in request.POST:
            lesson_id = request.POST.get('lesson_id')
            try:
                lesson = Lesson.objects.get(id=lesson_id)
                form = EditAllowedStudentsForm(request.POST, instance=lesson)
                if form.is_valid():
                    form.save()
            except Lesson.DoesNotExist:
                pass
            return redirect('super_teacher_dashboard')

        elif 'change_role' in request.POST:
            profile_id = request.POST.get('profile_id')
            new_role = request.POST.get('new_role')
            try:
                profile = Profile.objects.get(id=profile_id)
                if profile.user != request.user:
                    profile.role = new_role
                    profile.save()
            except Profile.DoesNotExist:
                pass
            return redirect('super_teacher_dashboard')

        elif 'delete_course' in request.POST:
            course_id = request.POST.get('course_id')
            try:
                course = Course.objects.get(id=course_id)
                linked_lessons = Lesson.objects.filter(course=course)
                for lesson in linked_lessons:
                    lesson.course = None
                    lesson.status = 'public'
                    lesson.save()

                course.delete()
            except Course.DoesNotExist:
                pass
            return redirect('super_teacher_dashboard')

    all_lessons = Lesson.objects.all()
    all_courses = Course.objects.all()
    all_profiles = Profile.objects.exclude(user=request.user)

    return render(request, 'main/super_teacher_dashboard.html', {
        'lesson_form': lesson_form,
        'course_form': course_form,
        'lessons': all_lessons,
        'courses': all_courses,
        'profiles': all_profiles,
    })