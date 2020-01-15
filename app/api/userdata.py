import os

from flask import send_from_directory, current_app
from flask_login import current_user, login_required

from app.api import api


@api.route('/userdata/<string:file>', methods=['GET'])
@login_required
def get_userdata(file):
    return send_from_directory(os.path.join(current_app.instance_path, current_app.config['USER_DATA_FOLDER'], str(current_user.id)), file)


@api.route('/userdata/writing/<string:file>', methods=['GET'])
@login_required
def get_writing(file):
    p = os.path.join(os.path.dirname(current_app.root_path), current_app.config['WRITING_UPLOAD_FOLDER'], str(current_user.id))
    return send_from_directory(p, file)