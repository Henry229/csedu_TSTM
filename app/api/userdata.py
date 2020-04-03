import os

from flask import send_from_directory, current_app
from flask_login import current_user, login_required
from sqlalchemy.orm import load_only

from app.api import api
from .. import db
from ..models import Permission, MarkingForWriting, Marking, MarkerAssigned, AssessmentEnroll, MarkerBranch
from ..web.errors import forbidden


@api.route('/userdata/<int:user_id>/<string:file>', methods=['GET'])
@login_required
def get_data(user_id, file):
    if current_user.can(Permission.ADMIN) or current_user.id == user_id:
        return send_from_directory(
            os.path.join(current_app.instance_path, current_app.config['USER_DATA_FOLDER'], str(user_id)), file)
    return forbidden("Not authorised to get the resource requested")


@api.route('/userdata/writing/<int:marking_writing_id>/<int:student_user_id>/<string:file>', methods=['GET'])
@login_required
def get_writing(marking_writing_id, student_user_id, file):
    # marking_id = (
    #     MarkingForWriting.query.options(load_only("marking_id")).filter_by(id=marking_writing_id).first()).marking_id
    # marking = Marking.query.filter_by(id=marking_id).first()
    # assessment_id = marking.enroll.assessment_id
    branch_id = (db.session.query(AssessmentEnroll.test_center). \
                    join(Marking, AssessmentEnroll.id == Marking.assessment_enroll_id). \
                    join(MarkingForWriting, Marking.id == MarkingForWriting.marking_id). \
                    filter(MarkingForWriting.id==marking_writing_id).first()
                 ).test_center

    marker_ids = [sub.marker_id for sub in MarkerBranch.query.options(load_only("marker_id")).filter_by(
        branch_id=branch_id).filter(MarkerBranch.delete.isnot(True)).all()]
    if current_user.can(Permission.ADMIN) or current_user.id in marker_ids or current_user.id == student_user_id:
        p = os.path.join(os.path.dirname(current_app.root_path), current_app.config['USER_DATA_FOLDER'],
                         str(student_user_id), "writing")
        return send_from_directory(p, file)
    return forbidden("Not authorised to get the resource requested")


@api.route('/userdata/naplan/<int:student_user_id>/<string:file>', methods=['GET'])
@login_required
def get_naplan(student_user_id, file):
    if current_user.can(Permission.ADMIN) or current_user.id == student_user_id:
        p = os.path.join(os.path.dirname(current_app.root_path), current_app.config['USER_DATA_FOLDER'],
                         str(student_user_id), "naplan")
        mimetype = None
        if file.find('.png') > 0:
            mimetype = "application/png"
        elif file.find('.jpg') > 0:
            mimetype = "application/jpg"
        return send_from_directory(p, file, mimetype=mimetype)
    return forbidden("Not authorised to get the resource requested")
