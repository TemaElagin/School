from django.contrib import admin
from .models import Profile, Lesson, Course, Submission

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_editable = ('role',)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'status', 'author')
    filter_horizontal = ('allowed_students',)


admin.site.register(Course)
admin.site.register(Submission)