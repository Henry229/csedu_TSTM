import os
from flask import jsonify
from flask import request, current_app
from app.api import api
from app.decorators import permission_required
from app.models import Item, Permission, Codebook, Testlet, AssessmentEnroll, MarkingForWriting
from sqlalchemy.orm import load_only

# Writing > Assessment List > search writings > Items return for listing
@api.route('/writing_item_list/')
@permission_required(Permission.ADMIN)
def get_writing_item_list():
    assessment_guid = request.args.get('assessment_guid', '01', type=str)
    student_id = request.args.get('student_id', 0, type=int)

    marking_writing_list = []
    assessment_enroll = AssessmentEnroll.query.filter_by(assessment_guid=assessment_guid).filter_by(student_id=student_id).all()
    for a in assessment_enroll:
        markings = a.marking
        for m in markings:
            marking_writing = MarkingForWriting.query.filter_by(marking_id=m.id).first()
            if marking_writing:
                interaction_type = (Item.query.options(load_only("interaction_type")).filter_by(id=m.item_id).first()).interaction_type
                if interaction_type=='extendedTextInteraction' or interaction_type=='uploadInteraction':
                    json_str = { "assessment_enroll_id" : a.id,
                                 "assessment_name": a.assessment.name,
                                 "start_time": a.start_time,
                                 "marking_id": m.id,
                                 "item_id": m.item_id,
                                 "marking_writing_id" : marking_writing.id}
                    marking_writing_list.append(json_str)
    return jsonify(marking_writing_list)

