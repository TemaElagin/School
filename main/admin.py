from django.contrib import admin
from .models import Profile, Lesson, Course, Submission

admin.site.register(Profile)
admin.site.register(Lesson)
admin.site.register(Course)
admin.site.register(Submission)