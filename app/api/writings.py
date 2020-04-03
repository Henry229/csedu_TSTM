from flask import jsonify
from flask import jsonify
from flask import request
from sqlalchemy.orm import load_only

from app.api import api
from app.decorators import permission_required_or_multiple
from app.models import Item, Permission, AssessmentEnroll, MarkingForWriting


# Writing > Assessment List > search writings > Items return for listing
@api.route('/writing_item_list/')
@permission_required_or_multiple(Permission.WRITING_READ, Permission.WRITING_MANAGE)
def get_writing_item_list():
    assessment_guid = request.args.get('assessment_guid', '01', type=str)
    student_user_id = request.args.get('student_user_id', 0, type=int)

    marking_writing_list = []
    assessment_enroll = AssessmentEnroll.query.filter_by(assessment_guid=assessment_guid).filter_by(
        student_user_id=student_user_id).all()
    for a in assessment_enroll:
        markings = a.marking
        for m in markings:
            marking_writing = MarkingForWriting.query.filter_by(marking_id=m.id).first()
            if marking_writing:
                interaction_type = (
                    Item.query.options(load_only("interaction_type")).filter_by(id=m.item_id).first()).interaction_type
                if interaction_type == 'extendedTextInteraction' or interaction_type == 'uploadInteraction':
                    if marking_writing.candidate_file_link:
                        is_candidate_file = True
                    else:
                        is_candidate_file = False
                    if marking_writing.candidate_mark_detail:
                        is_marked = True
                    else:
                        is_marked = False

                    json_str = {"assessment_enroll_id": a.id,
                                "assessment_name": a.assessment.name,
                                "start_time": a.start_time,
                                "marking_id": m.id,
                                "item_id": m.item_id,
                                "marking_writing_id": marking_writing.id,
                                "is_candidate_file": is_candidate_file,
                                "is_marked": is_marked}
                    marking_writing_list.append(json_str)
    return jsonify(marking_writing_list)
