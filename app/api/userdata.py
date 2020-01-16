import os

from flask import send_from_directory, current_app
from flask_login import current_user, login_required

from app.api import api
from ..decorators import permission_required
from ..models import Permission


@api.route('/userdata/<string:file>', methods=['GET'])
@login_required
def get_data(file):
    return send_from_directory(
        os.path.join(current_app.instance_path, current_app.config['USER_DATA_FOLDER'], str(current_user.id)), file)


@api.route('/userdata/writing/<string:file>', methods=['GET'])
@login_required
def get_writing(file):
    p = os.path.join(os.path.dirname(current_app.root_path), current_app.config['USER_DATA_FOLDER'],
                     str(current_user.id), "writing")
    return send_from_directory(p, file)


@api.route('/userdata/naplan/<string:file>', methods=['GET'])
@login_required
def get_naplan(file):
    p = os.path.join(os.path.dirname(current_app.root_path), current_app.config['USER_DATA_FOLDER'],
                     str(current_user.id), "naplan")
    mimetype = None
    if file.find('.png') > 0:
        mimetype = "application/png"
    elif file.find('.jpg') > 0:
        mimetype = "application/jpg"
    return send_from_directory(p, file, mimetype=mimetype)

