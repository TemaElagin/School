from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[
        ('student', 'Ученик'),
        ('teacher', 'Учитель'),
        ('super_teacher', 'СуперУчитель')
    ], default='student')


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

    title = models.CharField(max_length=200)
    type = models.CharField(max_length=10, choices=TYPES)
    status = models.CharField(max_length=10, choices=STATUSES, default='lock')

    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_lessons')

    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='course_lessons')

    allowed_students = models.ManyToManyField(User, blank=True, related_name='allowed_lessons')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.course is not None:
            self.status = 'public'
        super().save(*args, **kwargs)


class Course(models.Model):
    title = models.CharField(max_length=200)


    def __str__(self):
        return self.title


class Submission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    file = models.FileField(upload_to='solutions/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)