from flask import Blueprint

report = Blueprint('report', __name__)

from . import views, forms
from ..models import Permission, Codebook, Student, User


# Context Processor에 등록. 모든 template에 global하게 사용가능한 변수로 만든다.
@report.app_context_processor
def inject_permission():
    return dict(Permission=Permission)


@report.app_context_processor
def inject_code():
    return dict(Codebook=Codebook)


@report.app_context_processor
def inject_common():
    return dict(Student=Student, User=User)
