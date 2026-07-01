import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Lesson, Course, Profile, TestResult, TaskSubmission
from .forms import (
    RegistrationForm, TeacherLessonCreateForm, SuperLessonCreateForm,
    CourseCreateForm, LessonQuestionFormSet, LessonEditForm,
    StudentSubmissionForm, TeacherCheckForm
)


# --- Декораторы прав доступа ---
def is_teacher(user):
    return user.is_authenticated and user.profile.role in ['teacher', 'super_teacher']


def is_super_teacher(user):
    return user.is_authenticated and user.profile.role == 'super_teacher'


# --- Основные вьюхи ---

def index(request):
    if request.user.is_authenticated:
        allowed_lessons = Lesson.objects.filter(
            Q(status='public') | Q(status='private', allowed_students=request.user)
        )
    else:
        allowed_lessons = Lesson.objects.filter(status='public')

    return render(request, 'main/index.html', {
        'lessons': allowed_lessons.filter(course__isnull=True).distinct(),
        'courses': Course.objects.all()
    })


@login_required
def profile_dashboard(request):
    return render(request, 'main/profile.html', {
        'test_results': request.user.test_results.all(),
        'submissions': request.user.submissions.all().select_related('lesson')
    })


def register(request):
    if request.user.is_authenticated: return redirect('index')
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
                if user.profile.role == 'super_teacher': return redirect('super_teacher_dashboard')
                if user.profile.role == 'teacher': return redirect('teacher_dashboard')
            return redirect('index')
    return render(request, 'main/login.html', {'form': AuthenticationForm()})


@user_passes_test(is_teacher)
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
    return render(request, 'main/teacher_dashboard.html', {
        'form': TeacherLessonCreateForm(),
        'lessons': Lesson.objects.exclude(status='superlock')
    })


@user_passes_test(is_super_teacher)
def super_teacher_dashboard(request):
    if request.method == 'POST':
        if 'create_lesson' in request.POST:
            form = SuperLessonCreateForm(request.POST)
            if form.is_valid():
                lesson = form.save(commit=False)
                lesson.author = request.user
                lesson.save()
                form.save_m2m()
        elif 'create_course' in request.POST:
            form = CourseCreateForm(request.POST)
            if form.is_valid(): form.save()
        elif 'change_course' in request.POST:
            lesson = get_object_or_404(Lesson, id=request.POST.get('lesson_id'))
            c_id = request.POST.get('course_id')
            lesson.course = get_object_or_404(Course, id=c_id) if c_id else None
            lesson.save()
        elif 'change_status' in request.POST:
            lesson = get_object_or_404(Lesson, id=request.POST.get('lesson_id'))
            lesson.status = request.POST.get('new_status')
            lesson.save()
        elif 'change_allowed_students' in request.POST:
            lesson = get_object_or_404(Lesson, id=request.POST.get('lesson_id'))
            lesson.allowed_students.set(User.objects.filter(id__in=request.POST.getlist('allowed_students')))
        elif 'change_role' in request.POST:
            profile = get_object_or_404(Profile, id=request.POST.get('profile_id'))
            profile.role = request.POST.get('new_role')
            profile.save()
        elif 'delete_lesson' in request.POST:
            get_object_or_404(Lesson, id=request.POST.get('lesson_id')).delete()
        elif 'delete_course' in request.POST:
            get_object_or_404(Course, id=request.POST.get('course_id')).delete()
        return redirect('super_teacher_dashboard')

    return render(request, 'main/super_teacher_dashboard.html', {
        'lesson_form': SuperLessonCreateForm(),
        'course_form': CourseCreateForm(),
        'lessons': Lesson.objects.all().select_related('course', 'author'),
        'courses': Course.objects.all().prefetch_related('course_lessons'),
        'profiles': Profile.objects.exclude(user=request.user),
        'test_results': TestResult.objects.all().order_by('-updated_at'),
        'unchecked_submissions': TaskSubmission.objects.filter(is_checked=False)
    })


@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if lesson.status == 'private' and not lesson.allowed_students.filter(
            id=request.user.id).exists() and request.user.profile.role == 'student':
        return HttpResponseForbidden("У вас нет доступа")

    questions = lesson.questions.all()
    context = {'lesson': lesson, 'questions': questions}

    # Логика тестов
    if request.method == 'POST' and lesson.type == 'test':
        score = 0
        for q in questions:
            ans = request.POST.get(f'question_{q.id}', '').strip()
            if ans.lower() == q.correct_answer.strip().lower(): score += 1
            q.student_answer = ans

        existing = TestResult.objects.filter(student=request.user, lesson=lesson).first()
        if existing:
            existing.score, existing.attempts_count = score, existing.attempts_count + 1
            existing.save()
        else:
            TestResult.objects.create(student=request.user, lesson=lesson, score=score,
                                      total_questions=questions.count(), attempts_count=1)
        context.update({'test_submitted': True, 'score': score, 'total_questions': questions.count()})

    # Логика задач
    if lesson.type == 'task':
        sub = TaskSubmission.objects.filter(student=request.user, lesson=lesson).first()
        if request.method == 'POST':
            form = StudentSubmissionForm(request.POST, request.FILES, instance=sub)
            if form.is_valid():
                s = form.save(commit=False)
                s.student, s.lesson, s.is_checked = request.user, lesson, False
                s.save()
                return redirect('lesson_detail', lesson_id=lesson.id)
        context.update({'submission': sub, 'submission_form': StudentSubmissionForm(instance=sub)})

    return render(request, 'main/lesson_detail.html', context)


@user_passes_test(is_teacher)
def manage_test(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, type='test')
    if request.user.profile.role != 'super_teacher' and lesson.author != request.user:
        return HttpResponseForbidden("Нет прав")
    if request.method == 'POST':
        formset = LessonQuestionFormSet(request.POST, instance=lesson)
        if formset.is_valid(): formset.save()
    return render(request, 'main/manage_test.html',
                  {'lesson': lesson, 'formset': LessonQuestionFormSet(instance=lesson)})


@user_passes_test(is_teacher)
def edit_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.user.profile.role != 'super_teacher' and lesson.author != request.user:
        return HttpResponseForbidden("Нет прав")
    if request.method == 'POST':
        form = LessonEditForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            return redirect('lesson_detail', lesson_id=lesson.id)
    return render(request, 'main/edit_lesson.html', {'form': LessonEditForm(instance=lesson), 'lesson': lesson})


@user_passes_test(is_teacher)
def check_submission(request, submission_id):
    sub = get_object_or_404(TaskSubmission, id=submission_id)
    if request.method == 'POST':
        form = TeacherCheckForm(request.POST, request.FILES, instance=sub)
        if form.is_valid():
            form.save(commit=False).is_checked = True
            form.save()
            return redirect(
                'super_teacher_dashboard' if request.user.profile.role == 'super_teacher' else 'teacher_dashboard')
    return render(request, 'main/check_submission.html', {'form': TeacherCheckForm(instance=sub), 'submission': sub})


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    lessons = course.course_lessons.all()
    return render(request, 'main/course_detail.html', {
        'course': course,
        'lessons': lessons
    })


@user_passes_test(is_teacher)
@require_POST
def update_lesson_order(request):
    data = json.loads(request.body)
    for index, l_id in enumerate(data.get('new_order', [])):
        Lesson.objects.filter(id=l_id).update(order=index)
    return JsonResponse({'status': 'success'})