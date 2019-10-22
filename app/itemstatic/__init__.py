from flask import Blueprint

itemstatic = Blueprint('itemstatic', __name__)

from . import views
