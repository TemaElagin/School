from django.contrib import admin
from .models import Profile, Course, Lesson, Question, TestResult, TaskSubmission

admin.site.register(Profile)
admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Question)
admin.site.register(TestResult)
admin.site.register(TaskSubmission)