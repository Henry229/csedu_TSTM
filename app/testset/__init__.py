from flask import Blueprint

testset = Blueprint('testset', __name__)

from . import views, forms
from ..models import Permission, Codebook, Weights


# Context Processor에 등록. 모든 template에 global하게 사용가능한 변수로 만든다.
@testset.app_context_processor
def inject_permission():
    return dict(Permission=Permission)


# TODO - Can't use Choices here because DB call is not available yet
#
@testset.app_context_processor
def inject_code():
    return dict(Codebook=Codebook)


@testset.app_context_processor
def inject_weight():
    return dict(Weights=Weights)
