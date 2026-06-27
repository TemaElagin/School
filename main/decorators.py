from django.shortcuts import redirect

def teacher_required(view_func):
    def wrapper(request, *args, **kwargs):
        if hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
            return view_func(request, *args, **kwargs)
        else:
            return redirect('index')
    return wrapper