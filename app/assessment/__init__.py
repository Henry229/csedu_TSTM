from flask import Blueprint

assessment = Blueprint('assessment', __name__)

from . import views, forms
from ..models import Permission, Codebook


# Context Processor에 등록. 모든 template에 global하게 사용가능한 변수로 만든다.
@assessment.app_context_processor
def inject_permission():
    return dict(Permission=Permission)


@assessment.app_context_processor
def inject_code():
    return dict(Codebook=Codebook)


@assessment.context_processor
def utility_functions():
    def print_in_console(message):
        print(str(message))

    return dict(mdebug=print_in_console)
