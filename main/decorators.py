from django.shortcuts import redirect


def student_only(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'student':
            return view_func(request, *args, **kwargs)
        return redirect('index')
    return wrapper


def teacher_only(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
            return view_func(request, *args, **kwargs)
        return redirect('index')
    return wrapper


def super_teacher_only(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'super_teacher':
            return view_func(request, *args, **kwargs)
        return redirect('index')
    return wrapper