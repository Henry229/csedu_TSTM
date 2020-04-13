from flask import jsonify
from flask import request

from app.api import api
from app.decorators import permission_required_or_multiple
from app.models import Item, Permission, AssessmentEnroll, MarkingForWriting, Codebook
from common.logger import log


# Writing > Assessment List > search writings > Items return for listing

@api.route('/writing_item_list/')
@permission_required_or_multiple(Permission.WRITING_READ, Permission.WRITING_MANAGE)
def get_writing_item_list():
    assessment_guid = request.args.get('assessment_guid', '01', type=str)
    student_user_id = request.args.get('student_user_id', 0, type=int)

    log.info("Get writing list for %s:%s" % (assessment_guid, student_user_id))

    marking_writing_list = []
    assessment_enroll = AssessmentEnroll.query.filter_by(assessment_guid=assessment_guid).filter_by(
        student_user_id=student_user_id).all()
    log.debug("Assessment Enrolls: %s" % assessment_enroll)
    for a in assessment_enroll:
        log.debug("Assessment: %s" % a)
        markings = a.marking
        log.debug(markings)
        for m in markings:
            item_subject_code = Item.query.filter_by(id=m.item_id).first().subject
            if item_subject_code != Codebook.get_code_id("Writing"):
                continue
            marking_writing = MarkingForWriting.query.filter_by(marking_id=m.id).first()
            if marking_writing:
                item_subject_code = Item.query.filter_by(id=m.item_id).first().subject
                log.debug(m)
                if Codebook.get_code_name(item_subject_code) == Codebook.get_code_id("Writing"):
                    if marking_writing.candidate_file_link:
                        is_candidate_file = True
                    else:
                        is_candidate_file = False
                    if marking_writing.candidate_mark_detail:
                        is_marked = True
                    else:
                        is_marked = False
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
