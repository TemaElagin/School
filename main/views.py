import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from .models import Lesson, Course, Profile, Question, TestResult, TaskSubmission
from .forms import (
    RegistrationForm, TeacherLessonCreateForm, SuperLessonCreateForm,
    CourseCreateForm, LessonQuestionFormSet, LessonEditForm,
    StudentSubmissionForm, TeacherCheckForm
)
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
    if not request.user.is_authenticated or request.user.profile.role != 'super_teacher':
        return redirect('index')

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

        elif 'change_course' in request.POST:
            lesson = get_object_or_404(Lesson, id=request.POST.get('lesson_id'))
            course_id = request.POST.get('course_id')
            lesson.course = get_object_or_404(Course, id=course_id) if course_id else None
            lesson.save()
            return redirect('super_teacher_dashboard')

        elif 'change_status' in request.POST:
            lesson = get_object_or_404(Lesson, id=request.POST.get('lesson_id'))
            lesson.status = request.POST.get('new_status')
            lesson.save()
            return redirect('super_teacher_dashboard')

        elif 'change_allowed_students' in request.POST:
            lesson = get_object_or_404(Lesson, id=request.POST.get('lesson_id'))
            selected_student_ids = request.POST.getlist('allowed_students')
            lesson.allowed_students.set(User.objects.filter(id__in=selected_student_ids))
            return redirect('super_teacher_dashboard')

        elif 'change_role' in request.POST:
            profile = get_object_or_404(Profile, id=request.POST.get('profile_id'))
            profile.role = request.POST.get('new_role')
            profile.save()
            return redirect('super_teacher_dashboard')

        elif 'delete_lesson' in request.POST:
            get_object_or_404(Lesson, id=request.POST.get('lesson_id')).delete()
            return redirect('super_teacher_dashboard')

        elif 'delete_course' in request.POST:
            get_object_or_404(Course, id=request.POST.get('course_id')).delete()
            return redirect('super_teacher_dashboard')

    # Выборка данных для дашборда
    all_lessons = Lesson.objects.all().select_related('course', 'author')
    all_courses = Course.objects.all().prefetch_related('course_lessons')
    all_profiles = Profile.objects.exclude(user=request.user).select_related('user')
    all_test_results = TestResult.objects.all().select_related('student', 'lesson').order_by('-updated_at')

    unchecked_submissions = TaskSubmission.objects.filter(is_checked=False).select_related('student',
                                                                                           'lesson').order_by(
        '-submitted_at')
    checked_submissions = TaskSubmission.objects.filter(is_checked=True).select_related('student', 'lesson').order_by(
        '-checked_at')

    return render(request, 'main/super_teacher_dashboard.html', {
        'lesson_form': lesson_form,
        'course_form': course_form,
        'lessons': all_lessons,
        'courses': all_courses,
        'profiles': all_profiles,
        'test_results': all_test_results,
        'unchecked_submissions': unchecked_submissions,
        'checked_submissions': checked_submissions,
    })


def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    questions = lesson.questions.all()

    # Логика тестов
    submitted = False
    score = 0
    total_questions = questions.count()
    existing_result = None

    if request.user.is_authenticated and lesson.type == 'test':
        existing_result = TestResult.objects.filter(student=request.user, lesson=lesson).first()

    if request.method == 'POST' and lesson.type == 'test':
        submitted = True
        for question in questions:
            student_ans = request.POST.get(f'question_{question.id}', '').strip()
            is_correct = student_ans.lower() == question.correct_answer.strip().lower()
            if is_correct:
                score += 1
            question.student_answer = student_ans
            question.is_correct = is_correct

        if request.user.is_authenticated:
            if existing_result:
                existing_result.score = score
                existing_result.total_questions = total_questions
                existing_result.attempts_count += 1
                existing_result.save()
            else:
                existing_result = TestResult.objects.create(
                    student=request.user, lesson=lesson, score=score, total_questions=total_questions, attempts_count=1
                )

    # Логика задачников
    submission = None
    submission_form = None
    if request.user.is_authenticated and lesson.type == 'task':
        submission = TaskSubmission.objects.filter(student=request.user, lesson=lesson).first()

        if request.method == 'POST':
            submission_form = StudentSubmissionForm(request.POST, request.FILES, instance=submission)
            if submission_form.is_valid():
                sub = submission_form.save(commit=False)
                sub.student = request.user
                sub.lesson = lesson
                sub.is_checked = False
                sub.save()
                return redirect('lesson_detail', lesson_id=lesson.id)
        else:
            submission_form = StudentSubmissionForm(instance=submission)

    # Умный парсинг видео ссылок
    embed_video_url = None
    is_direct_file = False

    if lesson.video_url:
        url = lesson.video_url.strip()
        if 'youtube.com/watch?v=' in url:
            embed_video_url = f"https://www.youtube.com/embed/{url.split('v=')[1].split('&')[0]}"
        elif 'youtu.be/' in url:
            embed_video_url = f"https://www.youtube.com/embed/{url.split('youtu.be/')[1].split('?')[0]}"
        elif 'youtube.com/live/' in url:
            embed_video_url = f"https://www.youtube.com/embed/{url.split('youtube.com/live/')[1].split('?')[0]}"
        elif 'vk.com/video_ext.php' in url:
            embed_video_url = url
        elif 'vk.com/video' in url or 'vkvideo.ru/video' in url:
            try:
                video_part = url.split('/video')[1].split('?')[0]
                if '_' in video_part:
                    oid, vid = video_part.split('_')
                    embed_video_url = f"https://vk.com/video_ext.php?oid={oid}&id={vid}&hash=0"
            except (IndexError, ValueError):
                pass
        elif url.endswith(('.mp4', '.webm', '.ogg')):
            is_direct_file = True

    return render(request, 'main/lesson_detail.html', {
        'lesson': lesson,
        'questions': questions,
        'submitted': submitted,
        'score': score,
        'total_questions': total_questions,
        'existing_result': existing_result,
        'test_submitted': submitted,
        'submission': submission,
        'submission_form': submission_form,
        'embed_video_url': embed_video_url,
        'is_direct_file': is_direct_file,
    })


def manage_test(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id, type='test')

    if request.user.profile.role not in ['teacher', 'super_teacher']:
        return redirect('index')
    if request.user.profile.role == 'teacher' and lesson.author != request.user:
        return redirect('index')

    if request.method == 'POST':
        formset = LessonQuestionFormSet(request.POST, instance=lesson)
        if formset.is_valid():
            formset.save()
            return redirect('manage_test', lesson_id=lesson.id)
    else:
        formset = LessonQuestionFormSet(instance=lesson)

    return render(request, 'main/manage_test.html', {
        'lesson': lesson,
        'formset': formset
    })


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    lessons = course.course_lessons.all()
    return render(request, 'main/course_detail.html', {
        'course': course,
        'lessons': lessons
    })


def edit_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if request.user.profile.role not in ['teacher', 'super_teacher']:
        return redirect('index')
    if request.user.profile.role == 'teacher' and lesson.author != request.user:
        return redirect('index')

    if request.method == 'POST':
        form = LessonEditForm(request.POST, instance=lesson)
        if form.is_valid():
            form.save()
            return redirect('lesson_detail', lesson_id=lesson.id)
    else:
        form = LessonEditForm(instance=lesson)

    return render(request, 'main/edit_lesson.html', {'form': form, 'lesson': lesson})


def check_submission(request, submission_id):
    submission = get_object_or_404(TaskSubmission, id=submission_id)

    if request.user.profile.role not in ['teacher', 'super_teacher']:
        return redirect('index')

    if request.method == 'POST':
        form = TeacherCheckForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.is_checked = True
            sub.checked_at = timezone.now()
            sub.save()
            return redirect(
                'super_teacher_dashboard' if request.user.profile.role == 'super_teacher' else 'teacher_dashboard')
    else:
        form = TeacherCheckForm(instance=submission)

    return render(request, 'main/check_submission.html', {
        'form': form,
        'submission': submission
    })


# --- API Эндпоинты ---
@login_required
@require_POST
def update_lesson_order(request):
    if request.user.profile.role not in ['super_teacher', 'teacher']:
        return JsonResponse({'error': 'Access denied'}, status=403)

    try:
        data = json.loads(request.body)
        new_order = data.get('new_order', [])

        for index, lesson_id in enumerate(new_order):
            Lesson.objects.filter(id=lesson_id).update(order=index)

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)