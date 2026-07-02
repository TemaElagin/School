from django import forms
from django.contrib.auth.models import User
from .models import Lesson, Course, Question, TaskSubmission, Profile
import os

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input'}))
    teacher_invite_code = forms.CharField(
        max_length=15,
        required=False,
        label="Код вашего учителя (если есть)",
        help_text="Оставьте пустым, если вы учитесь самостоятельно"
    )

    class Meta:
        model = User
        fields = ['username', 'password']  # Убрали email навсегда
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'maxlength': '30'}),  # Ограничение 30 символов
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) > 30:
            raise forms.ValidationError("Длина логина не должна превышать 30 символов.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            code = self.cleaned_data.get('teacher_invite_code')
            profile, created = Profile.objects.get_or_create(user=user)
            if code:
                try:
                    teacher_profile = Profile.objects.get(teacher_code=code, role__in=['teacher', 'super_teacher'])
                    profile.my_teacher = teacher_profile.user
                    profile.save()
                except Profile.DoesNotExist:
                    pass
        return user


class LessonCreateOrEditForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['course', 'title', 'content', 'lesson_file', 'type', 'status', 'video_url', 'allowed_students']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['allowed_students'].required = False
        self.fields['allowed_students'].label = "Доступ ученикам (только для приватных уроков)"

        if user:
            if user.profile.role == 'teacher':
                self.fields['status'].choices = [
                    ('private', 'Приватный'),
                    ('lock', 'Закрытый'),
                    ('superlock', 'Суперзамок'),
                ]
                self.fields['allowed_students'].queryset = User.objects.filter(profile__my_teacher=user,
                                                                               profile__role='student')
            elif user.profile.role == 'super_teacher':
                self.fields['allowed_students'].queryset = User.objects.filter(profile__role='student')


class CourseCreateForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description']


class StudentSubmissionForm(forms.ModelForm):
    # Используем наше новое поле
    uploaded_files = MultipleFileField(
        required=False,
        label="Прикрепить файлы (до 10 штук)"
    )

    class Meta:
        model = TaskSubmission
        fields = ['comment']

    def clean_uploaded_files(self):
        files = self.files.getlist('uploaded_files')
        if len(files) > 10:
            raise forms.ValidationError("Вы не можете загрузить более 10 файлов.")

        allowed_extensions = ['.pdf', '.docx', '.jpg', '.jpeg', '.png']
        MAX_FILE_SIZE = 5 * 1024 * 1024
        for f in files:
            ext = os.path.splitext(f.name)[1].lower()

            if f.size > MAX_FILE_SIZE:
                raise forms.ValidationError(f"Файл {f.name} слишком тяжелый. Максимальный размер одного файла — 5 МБ.")

            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    f"Файл {f.name} имеет недопустимый формат. Разрешены только: pdf, docx, jpg, jpeg, png.")
        return files

    class Meta:
        model = TaskSubmission
        fields = ['comment']

    def clean_uploaded_files(self):
        files = self.files.getlist('uploaded_files')
        if len(files) > 10:
            raise forms.ValidationError("Вы не можете загрузить более 10 файлов.")

        allowed_extensions = ['.pdf', '.docx', '.jpg', '.jpeg', '.png']
        for f in files:
            ext = os.path.splitext(f.name)[1].lower()
            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    f"Файл {f.name} имеет недопустимый формат. Разрешены только: pdf, docx, jpg, jpeg, png.")
        return files


class TeacherCheckForm(forms.ModelForm):
    grade = forms.ChoiceField(
        choices=[('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')],
        label="Оценка (0-5)"
    )

    class Meta:
        model = TaskSubmission
        fields = ['grade', 'teacher_comment', 'teacher_file']