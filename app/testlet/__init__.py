from flask import Blueprint

testlet = Blueprint('testlet', __name__)

from . import views, forms
from ..models import Permission, Codebook, Weights


# Context Processor에 등록. 모든 template에 global하게 사용가능한 변수로 만든다.
@testlet.app_context_processor
def inject_permission():
    return dict(Permission=Permission)


@testlet.app_context_processor
def inject_code():
    return dict(Codebook=Codebook)


@testlet.app_context_processor
def inject_weight():
    return dict(Weights=Weights)
