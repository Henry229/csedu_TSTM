from flask import Blueprint

writing = Blueprint('writing', __name__)

from . import views, forms
from ..models import Permission, Student, User

@writing.app_context_processor
def inject_permission():
    return dict(Permission=Permission)

@writing.app_context_processor
def inject_permission():
    return dict(Student=Student)

@writing.app_context_processor
def inject_permission():
    return dict(User=User)



