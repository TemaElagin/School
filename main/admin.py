from django.contrib import admin
from .models import Profile, Lesson, Course, Submission

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_editable = ('role',)

admin.site.register(Lesson)
admin.site.register(Course)
admin.site.register(Submission)