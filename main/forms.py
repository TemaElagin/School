from django import forms
from django.contrib.auth.models import User
from .models import Profile
from .models import Lesson, Course

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            Profile.objects.create(user=user, role='student')
        return user

# class LessonCreateForm(forms.ModelForm):
#     class Meta:
#         model = Lesson
#         fields = ['title', 'type', 'status', 'allowed_students']
#         widgets = {
#             'allowed_students': forms.SelectMultiple(attrs={'class': 'form-control'}),
#         }


class TeacherLessonCreateForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'type']


class SuperLessonCreateForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'type', 'status', 'allowed_students']
        widgets = {
            'allowed_students': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }


class CourseCreateForm(forms.ModelForm):
    lessons = forms.ModelMultipleChoiceField(
        queryset=Lesson.objects.all(),
        required=False,
        label="Выбрать уроки для курса",
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Course
        fields = ['title', 'lessons']

    def save(self, commit=True):
        course = super().save(commit=commit)
        if commit:
            Lesson.objects.filter(course=course).update(course=None)
            chosen_lessons = self.cleaned_data['lessons']
            for lesson in chosen_lessons:
                lesson.course = course
                lesson.save()
        return course


class EditAllowedStudentsForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['allowed_students']
        widgets = {
            'allowed_students': forms.SelectMultiple(attrs={'style': 'height: 60px; width: 150px;'}),
        }