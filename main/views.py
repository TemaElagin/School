import json
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Lesson, Course, Profile, TestResult, TaskSubmission, Question, SubmissionFile
from .forms import RegistrationForm, LessonCreateOrEditForm, CourseCreateForm, StudentSubmissionForm, TeacherCheckForm


def is_teacher(user):
    return user.is_authenticated and user.profile.role in ['teacher', 'super_teacher']


def is_super_teacher(user):
    return user.is_authenticated and user.profile.role == 'super_teacher'


def parse_video_url(url):
    if not url:
        return None, False
    url = url.strip()

    if 'youtube.com/watch?v=' in url:
        return f"https://www.youtube.com/embed/{url.split('v=')[1].split('&')[0]}", False
    if 'youtu.be/' in url:
        return f"https://www.youtube.com/embed/{url.split('youtu.be/')[1].split('?')[0]}", False
    if 'youtube.com/live/' in url:
        return f"https://www.youtube.com/embed/{url.split('youtube.com/live/')[1].split('?')[0]}", False

    if 'vk.com/video_ext.php' in url:
        return url, False

    vk_match = re.search(r'video(-?\d+_\d+)', url)
    if vk_match:
        video_id = vk_match.group(1)
        hash_match = re.search(r'hash=([a-f0-9]+)', url)
        v_hash = hash_match.group(1) if hash_match else '0'
        return f"https://vk.com/video_ext.php?oid={video_id.split('_')[0]}&id={video_id.split('_')[1]}&hash={v_hash}", False

    if url.endswith(('.mp4', '.webm', '.ogg')):
        return url, True

    return None, False


def index(request):
    if request.user.is_authenticated:
        if request.user.profile.role == 'student':
            allowed_lessons = Lesson.objects.filter(
                Q(status='public') |
                Q(status='private', allowed_students=request.user)
            )
        else:
            allowed_lessons = Lesson.objects.filter(status__in=['public', 'private'])
    else:
        allowed_lessons = Lesson.objects.filter(status='public')

    return render(request, 'main/index.html', {
        'lessons': allowed_lessons.filter(course__isnull=True).distinct(),
        'courses': Course.objects.all()
    })


@login_required
def profile_dashboard(request):
    profile = request.user.profile
    message = None

    if request.method == 'POST' and profile.role == 'student' and not profile.my_teacher:
        code = request.POST.get('teacher_code', '').strip()
        if code:
            try:
                teacher_profile = Profile.objects.get(teacher_code=code, role__in=['teacher', 'super_teacher'])
                profile.my_teacher = teacher_profile.user
                profile.save()
                return redirect('profile_dashboard')
            except Profile.DoesNotExist:
                message = "Учитель с таким кодом не найден."

    return render(request, 'main/profile.html', {
        'submissions': request.user.submissions.all().select_related('lesson'),
        'message': message
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
    if request.user.is_authenticated: return redirect('index')
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
    role = request.user.profile.role

    if request.method == 'POST':
        form = LessonCreateOrEditForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.author = request.user
            if role == 'teacher' and lesson.status == 'public':
                lesson.status = 'private'  # Страховка от подмены POST-данных
            lesson.save()
            form.save_m2m()

            if lesson.type == 'test':
                questions_text = request.POST.getlist('q_text[]')
                questions_ans = request.POST.getlist('q_ans[]')
                for text, ans in zip(questions_text, questions_ans):
                    if text.strip() and ans.strip():
                        Question.objects.create(lesson=lesson, text=text.strip(), correct_answer=ans.strip())

            return redirect('super_teacher_dashboard' if role == 'super_teacher' else 'teacher_dashboard')
    else:
        form = LessonCreateOrEditForm(user=request.user)

    my_lessons = Lesson.objects.filter(author=request.user).select_related('course')
    my_students = User.objects.filter(profile__my_teacher=request.user).select_related('profile')

    unchecked_submissions = TaskSubmission.objects.filter(student__profile__my_teacher=request.user,
                                                          is_checked=False).select_related('student', 'lesson')
    checked_submissions = TaskSubmission.objects.filter(student__profile__my_teacher=request.user,
                                                        is_checked=True).select_related('student', 'lesson')

    return render(request, 'main/teacher_dashboard.html', {
        'form': form,
        'lessons': my_lessons,
        'my_students': my_students,
        'unchecked_submissions': unchecked_submissions,
        'checked_submissions': checked_submissions,
    })


@user_passes_test(is_super_teacher)
def super_teacher_dashboard(request):
    if request.method == 'POST':
        if 'create_course' in request.POST:
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
        elif 'change_role_and_code' in request.POST:
            profile = get_object_or_404(Profile, id=request.POST.get('profile_id'))
            profile.role = request.POST.get('new_role')
            profile.teacher_code = request.POST.get('teacher_code', '').strip() or None
            profile.save()
        elif 'delete_lesson' in request.POST:
            get_object_or_404(Lesson, id=request.POST.get('lesson_id')).delete()
        elif 'delete_course' in request.POST:
            get_object_or_404(Course, id=request.POST.get('course_id')).delete()
        elif 'edit_course' in request.POST:
            course = get_object_or_404(Course, id=request.POST.get('course_id'))
            course.title = request.POST.get('title')
            course.save()
        return redirect('super_teacher_dashboard')

    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'mine':
        unchecked_submissions = TaskSubmission.objects.filter(student__profile__my_teacher=request.user,
                                                              is_checked=False)
    else:
        unchecked_submissions = TaskSubmission.objects.filter(is_checked=False)

    return render(request, 'main/super_teacher_dashboard.html', {
        'lesson_form': LessonCreateOrEditForm(user=request.user),
        'course_form': CourseCreateForm(),
        'lessons': Lesson.objects.all().select_related('course', 'author'),
        'courses': Course.objects.all().prefetch_related('course_lessons'),
        'profiles': Profile.objects.exclude(user=request.user).select_related('user'),
        'test_results': TestResult.objects.all().order_by('-updated_at'),
        'unchecked_submissions': unchecked_submissions,
        'checked_submissions': TaskSubmission.objects.filter(is_checked=True).select_related('student', 'lesson'),
    })


@user_passes_test(is_teacher)
def students_progress(request):
    is_super = request.user.profile.role == 'super_teacher'

    selected_teacher_id = request.GET.get('teacher_filter', '')
    teachers = None

    if is_super:
        teachers = User.objects.filter(profile__role__in=['teacher', 'super_teacher'])
        if selected_teacher_id:
            students = User.objects.filter(profile__my_teacher_id=selected_teacher_id,
                                           profile__role='student').select_related('profile')
        else:
            students = User.objects.filter(profile__role='student').select_related('profile')
    else:
        students = User.objects.filter(profile__my_teacher=request.user, profile__role='student').select_related(
            'profile')

    progress_data = []
    for student in students:
        results = TestResult.objects.filter(student=student).select_related('lesson')
        tasks = TaskSubmission.objects.filter(student=student).prefetch_related('submission_files').select_related(
            'lesson')
        progress_data.append({
            'student': student,
            'test_results': results,
            'task_submissions': tasks
        })

    return render(request, 'main/students_progress.html', {
        'progress_data': progress_data,
        'teachers': teachers,
        'selected_teacher_id': selected_teacher_id,
        'is_super': is_super
    })


@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    user_profile = request.user.profile

    if lesson.status == 'private' and user_profile.role == 'student':
        if not lesson.allowed_students.filter(id=request.user.id).exists():
            return HttpResponseForbidden("У вас нет доступа к этому приватному уроку.")

    if lesson.status in ['lock', 'superlock'] and user_profile.role == 'student':
        return HttpResponseForbidden("Урок закрыт.")

    questions = list(lesson.questions.all())
    embed_video_url, is_direct_file = parse_video_url(lesson.video_url)

    submission = TaskSubmission.objects.filter(student=request.user, lesson=lesson).first()

    if request.method == 'POST' and lesson.type == 'test':
        score = 0
        for q in questions:
            ans = request.POST.get(f'question_{q.id}', '').strip()
            is_correct = (ans.lower() == q.correct_answer.strip().lower())
            if is_correct: score += 1
            q.student_answer = ans
            q.is_correct = is_correct

        existing = TestResult.objects.filter(student=request.user, lesson=lesson).first()
        if existing:
            existing.score, existing.attempts_count = score, existing.attempts_count + 1
            existing.save()
        else:
            TestResult.objects.create(student=request.user, lesson=lesson, score=score, total_questions=len(questions),
                                      attempts_count=1)
        return render(request, 'main/lesson_detail.html', {
            'lesson': lesson, 'questions': questions, 'embed_video_url': embed_video_url,
            'is_direct_file': is_direct_file, 'test_submitted': True, 'score': score, 'total_questions': len(questions)
        })

    if lesson.type == 'task':
        if request.method == 'POST':
            form = StudentSubmissionForm(request.POST, request.FILES)
            if form.is_valid():
                if not submission:
                    submission = TaskSubmission.objects.create(student=request.user, lesson=lesson)

                submission.comment = form.cleaned_data['comment']
                submission.is_checked = False
                submission.grade = None
                submission.teacher_comment = None
                submission.save()

                files = request.FILES.getlist('uploaded_files')
                if files:
                    submission.submission_files.all().delete()  # Удаляем прошлые попытки
                    for f in files:
                        SubmissionFile.objects.create(submission=submission, file=f)

                return redirect('lesson_detail', lesson_id=lesson.id)
        else:
            form = StudentSubmissionForm()

    return render(request, 'main/lesson_detail.html', {
        'lesson': lesson,
        'questions': questions,
        'embed_video_url': embed_video_url,
        'is_direct_file': is_direct_file,
        'submission': submission,
        'submission_form': form if lesson.type == 'task' else None
    })


@user_passes_test(is_teacher)
def edit_lesson(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.user.profile.role != 'super_teacher' and lesson.author != request.user:
        return HttpResponseForbidden("Вы можете редактировать только свои уроки.")

    if request.method == 'POST':
        form = LessonCreateOrEditForm(request.POST, request.FILES, instance=lesson, user=request.user)
        if form.is_valid():
            saved_lesson = form.save(commit=False)
            if request.user.profile.role == 'teacher' and saved_lesson.status == 'public':
                saved_lesson.status = 'private'  # Пункт 2: Жесткий блок смены статуса на публичный
            saved_lesson.save()
            form.save_m2m()

            if lesson.type == 'test':
                lesson.questions.all().delete()
                questions_text = request.POST.getlist('q_text[]')
                questions_ans = request.POST.getlist('q_ans[]')
                for text, ans in zip(questions_text, questions_ans):
                    if text.strip() and ans.strip():
                        Question.objects.create(lesson=lesson, text=text.strip(), correct_answer=ans.strip())

            return redirect('lesson_detail', lesson_id=lesson.id)
    else:
        form = LessonCreateOrEditForm(instance=lesson, user=request.user)
    return render(request, 'main/edit_lesson.html', {'form': form, 'lesson': lesson})


@user_passes_test(is_teacher)
def check_submission(request, submission_id):
    sub = get_object_or_404(TaskSubmission, id=submission_id)
    if request.user.profile.role == 'teacher' and sub.student.profile.my_teacher != request.user:
        return HttpResponseForbidden("Это не ваш ученик.")

    if request.method == 'POST':
        form = TeacherCheckForm(request.POST, request.FILES, instance=sub)
        if form.is_valid():
            f = form.save(commit=False)
            f.is_checked = True
            f.checked_at = timezone.now()
            f.save()
            return redirect(
                'super_teacher_dashboard' if request.user.profile.role == 'super_teacher' else 'teacher_dashboard')
    return render(request, 'main/check_submission.html', {'form': TeacherCheckForm(instance=sub), 'submission': sub})


@user_passes_test(is_teacher)
@require_POST
def update_lesson_order(request):
    data = json.loads(request.body)
    for index, l_id in enumerate(data.get('new_order', [])):
        Lesson.objects.filter(id=l_id).update(order=index)
    return JsonResponse({'status': 'success'})


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    return render(request, 'main/course_detail.html', {'course': course, 'lessons': course.course_lessons.all()})