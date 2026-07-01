from django.contrib import admin
from .models import Profile, Course, Lesson, Question, Choice, TestResult, TaskSubmission

admin.site.register(Profile)
admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(TestResult)
admin.site.register(TaskSubmission)