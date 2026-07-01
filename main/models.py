from django.db import models
from django.contrib.auth.models import User


def student_submission_path(instance, filename):
    return f'submissions/user_{instance.student.id}/{filename}'

def teacher_response_path(instance, filename):
    return f'teacher_responses/submission_{instance.id}/{filename}'



class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Ученик'),
        ('teacher', 'Учитель'),
        ('super_teacher', 'СуперУчитель'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')

    # Код учителя: заполняется вручную СуперУчителем для учителей и суперучителей
    teacher_code = models.CharField(max_length=15, unique=True, blank=True, null=True, verbose_name="Код учителя")

    # Привязка ученика к конкретному учителю (у ученика только ОДИН учитель)
    my_teacher = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='my_students',
                                   verbose_name="Мой преподаватель")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Course(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название курса")
    description = models.TextField(blank=True, verbose_name="Описание")

    def __str__(self):
        return self.title


class Lesson(models.Model):
    LESSON_TYPES = [
        ('text', 'Учебник'),
        ('task', 'Задачник'),
        ('test', 'Тест'),
    ]
    STATUS_CHOICES = [
        ('public', 'Публичный'),
        ('private', 'Приватный'),
        ('lock', 'Закрытый'),
        ('superlock', 'Суперзамок'),
    ]

    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='course_lessons')
    title = models.CharField(max_length=200, verbose_name="Название урока")
    content = models.TextField(verbose_name="Текст урока / Теория", blank=True)

    # Возможность загрузить файл вместо текста или как дополнение (скриншот, PDF, docx)
    lesson_file = models.FileField(upload_to='lesson_materials/', blank=True, null=True, verbose_name="Файл к уроку")

    type = models.CharField(max_length=10, choices=LESSON_TYPES, default='text')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='lock')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lessons')
    video_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на видео (YouTube/VK)")
    order = models.PositiveIntegerField(default=0)

    # Список студентов, которым открыт этот приватный урок (только из числа СВОИХ учеников)
    allowed_students = models.ManyToManyField(User, blank=True, related_name='allowed_lessons')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class Question(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField(verbose_name="Текст вопроса (поддерживает LaTeX)")
    correct_answer = models.CharField(max_length=255, verbose_name="Правильный ответ")

    def __str__(self):
        return f"Вопрос для {self.lesson.title}"


class TestResult(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    score = models.IntegerField()
    total_questions = models.IntegerField()
    attempts_count = models.IntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)


class TaskSubmission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    is_checked = models.BooleanField(default=False)
    grade = models.CharField(max_length=10, blank=True, null=True)
    teacher_comment = models.TextField(blank=True, null=True)
    teacher_file = models.FileField(upload_to='teacher_responses/', blank=True, null=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    checked_at = models.DateTimeField(blank=True, null=True)