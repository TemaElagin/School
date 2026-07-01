from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[
        ('student', 'Ученик'),
        ('teacher', 'Учитель'),
        ('super_teacher', 'СуперУчитель')
    ], default='student')

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class Course(models.Model):
    title = models.CharField(max_length=200, verbose_name="Название курса")
    description = models.TextField(blank=True, null=True, verbose_name="Описание курса")

    def __str__(self):
        return self.title


class Lesson(models.Model):
    TYPES = [
        ('test', 'Тест'),
        ('task', 'Задачник'),
        ('video', 'Видео'),
        ('text', 'Учебник')
    ]
    STATUSES = [
        ('public', 'Открытый'),
        ('private', 'Приватный'),
        ('lock', 'Закрытый'),
        ('superlock', 'Скрыт от всех')
    ]

    title = models.CharField(max_length=200, verbose_name="Название урока")
    type = models.CharField(max_length=10, choices=TYPES, verbose_name="Тип урока")
    status = models.CharField(max_length=10, choices=STATUSES, default='lock', verbose_name="Статус")
    order = models.IntegerField(default=0, verbose_name="Порядок в курсе")

    content_text = models.TextField(blank=True, null=True, verbose_name="Текст лекции / Задания")
    video_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на видео")
    correct_answer = models.CharField(max_length=200, blank=True, null=True,
                                      verbose_name="Правильный ответ (для задач/тестов)")

    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_lessons')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='course_lessons')
    allowed_students = models.ManyToManyField(User, blank=True, related_name='allowed_lessons')

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.course is not None and self.status == 'lock':
            self.status = 'public'
        super().save(*args, **kwargs)


class Question(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions', verbose_name="Урок-Тест")
    text = models.TextField(verbose_name="Текст вопроса (можно использовать LaTeX)")
    correct_answer = models.CharField(max_length=200, verbose_name="Правильный ответ")

    def __str__(self):
        return f"Вопрос: {self.text[:50]}..."


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices', verbose_name="Вопрос")
    text = models.CharField(max_length=200, verbose_name="Текст варианта ответа")
    is_correct = models.BooleanField(default=False, verbose_name="Это правильный ответ?")

    def __str__(self):
        return self.text


class TestResult(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results', verbose_name="Ученик")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='test_results', verbose_name="Урок-Тест")
    score = models.IntegerField(verbose_name="Набранные баллы")
    total_questions = models.IntegerField(verbose_name="Всего вопросов")
    attempts_count = models.IntegerField(default=0, verbose_name="Количество попыток")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата последней попытки")

    class Meta:
        unique_together = ('student', 'lesson')

    def __str__(self):
        return f"{self.student.username} -> {self.lesson.title} (Попыток: {self.attempts_count}): {self.score}/{self.total_questions}"


def student_submission_path(instance, filename):
    return f'submissions/student_{instance.student.id}/lesson_{instance.lesson.id}/{filename}'


def teacher_response_path(instance, filename):
    return f'submissions/student_{instance.student.id}/lesson_{instance.lesson.id}/teacher_{filename}'


class TaskSubmission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions', verbose_name="Ученик")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='submissions', verbose_name="Урок-Задача")
    file = models.FileField(upload_to=student_submission_path, verbose_name="Файл с решением")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отправки")

    is_checked = models.BooleanField(default=False, verbose_name="Проверено")
    grade = models.CharField(max_length=50, blank=True, null=True, verbose_name="Оценка/Балл")
    teacher_comment = models.TextField(blank=True, null=True, verbose_name="Комментарий учителя")
    teacher_file = models.FileField(upload_to=teacher_response_path, blank=True, null=True,
                                    verbose_name="Проверенный файл от учителя")
    checked_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата проверки")

    class Meta:
        unique_together = ('student', 'lesson')

    def __str__(self):
        return f"Решение: {self.student.username} по {self.lesson.title}"