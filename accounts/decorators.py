# decorators.py
import base64
from django.conf import settings
from django.shortcuts import redirect

from accounts.services.security_services import security_service

from cryptography.fernet import Fernet


def auth_user(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            # Add the 'user' parameter to the decorated view function's arguments only if it's used
            if 'user' in view_func.__code__.co_varnames:
                kwargs['user'] = request.user

            return view_func(request, *args, **kwargs)
        else:
            return redirect('login')
    return wrapper
