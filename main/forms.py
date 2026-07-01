from django import forms
from django.contrib.auth.models import User
from .models import Lesson, Course, Question, TaskSubmission, Profile


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
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            # Проверяем код учителя при регистрации
            code = self.cleaned_data.get('teacher_invite_code')
            profile, created = Profile.objects.get_or_create(user=user)
            if code:
                try:
                    teacher_profile = Profile.objects.get(teacher_code=code, role__in=['teacher', 'super_teacher'])
                    profile.my_teacher = teacher_profile.user
                    profile.save()
                except Profile.DoesNotExist:
                    pass  # Если код неверный, просто регистрируем без учителя
        return user


class LessonCreateOrEditForm(forms.ModelForm):
    class Meta:
        model = Lesson
        # Добавили allowed_students в форму
        fields = ['course', 'title', 'content', 'lesson_file', 'type', 'status', 'video_url', 'allowed_students']

    def __init__(self, *args, **kwargs):
        # Извлекаем пользователя из аргументов (если передан)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Настройка поля доступов
        self.fields['allowed_students'].required = False
        self.fields['allowed_students'].label = "Доступ ученикам (только для приватных уроков)"
        self.fields['allowed_students'].help_text = "Зажмите Ctrl (или Cmd на Mac), чтобы выбрать нескольких учеников."

        # Фильтруем список учеников в зависимости от роли
        if user:
            if user.profile.role == 'super_teacher':
                # СуперУчитель может выдать доступ любому ученику
                self.fields['allowed_students'].queryset = User.objects.filter(profile__role='student')
            elif user.profile.role == 'teacher':
                # Обычный учитель видит только тех, кто привязан к нему
                self.fields['allowed_students'].queryset = User.objects.filter(profile__my_teacher=user,
                                                                               profile__role='student')


class CourseCreateForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description']


class StudentSubmissionForm(forms.ModelForm):
    class Meta:
        model = TaskSubmission
        fields = ['file', 'comment']


class TeacherCheckForm(forms.ModelForm):
    class Meta:
        model = TaskSubmission
        fields = ['grade', 'teacher_comment', 'teacher_file']