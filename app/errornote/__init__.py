from flask import Blueprint

errornote = Blueprint('errornote', __name__)

from . import views
from ..models import Permission, Codebook, Student, User


# Context Processor에 등록. 모든 template에 global하게 사용가능한 변수로 만든다.
@errornote.app_context_processor
def inject_permission():
    return dict(Permission=Permission)


@errornote.app_context_processor
def inject_code():
    return dict(Codebook=Codebook)


@errornote.app_context_processor
def inject_common():
    return dict(Student=Student, User=User)
