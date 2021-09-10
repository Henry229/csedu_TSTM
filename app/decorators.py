from functools import wraps

from flask import abort, redirect, url_for, session
from flask_login import current_user

from .models import Permission


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator

def permission_required_or_multiple(permission1, permission2):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not (current_user.can(permission1) or current_user.can(permission2)):
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator

def admin_required(f):
    return permission_required(Permission.ADMIN)(f)

def check_sample_login():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('sample') is None:
                return redirect(url_for('sample.sample_index'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator

def check_sample_login_api():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('sample') is None:
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator