from flask import Blueprint

web = Blueprint('web', __name__)

from . import views, errors
from ..models import Permission


# render_template()에서 Permission을 매번 인수로 추가하지 않기 위하여,
# Context Processor에 등록. 모든 template에 global하게 사용가능한 변수로 만든다.
@web.app_context_processor
def inject_permission():
    return dict(Permission=Permission)
