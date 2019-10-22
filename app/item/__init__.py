from flask import Blueprint

item = Blueprint('item', __name__)

from . import views, forms
from ..models import Permission, Codebook


# Context Processor에 등록. 모든 template에 global하게 사용가능한 변수로 만든다.
@item.app_context_processor
def inject_permission():
    return dict(Permission=Permission)


@item.app_context_processor
def inject_code():
    return dict(Codebook=Codebook)
