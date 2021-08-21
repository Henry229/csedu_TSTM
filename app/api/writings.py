import json
from datetime import datetime

from flask import jsonify
from flask import request
from flask_login import current_user

from app import db
from app.api import api
from app.api.response import success
from app.decorators import permission_required_or_multiple, permission_required
from app.models import Item, Permission, AssessmentEnroll, MarkingForWriting, Codebook, Assessment, Testset, \
    MarkerBranch, Marking
from common.logger import log


def getBranchIds(marker_id):
    branch_ids = [row.branch_id for row in
                  db.session.query(MarkerBranch.branch_id).filter_by(marker_id=marker_id).all()]
    all_branches = []
    for branch_id in branch_ids:
        if Codebook.get_code_name(branch_id) == 'All':
            all_branches = [row.id for row in
                            db.session.query(Codebook.id).filter(Codebook.code_type == 'test_center').all()]
            break
    branch_ids += all_branches
    return branch_ids

# Writing > Assessment List > search writings > Items return for listing

@api.route('/writing_item_list/')
@permission_required_or_multiple(Permission.WRITING_READ, Permission.WRITING_MANAGE)
def get_writing_item_list():
    assessment_guid = request.args.get('assessment_guid', '01', type=str)
    testset_id = request.args.get('testset_id', 0, type=int)
    student_user_id = request.args.get('student_user_id', 0, type=int)

    log.info("Get writing list for %s:%s" % (assessment_guid, student_user_id))

    marking_writing_list = []
    assessment_enroll = AssessmentEnroll.query.filter_by(assessment_guid=assessment_guid).filter_by(
        student_user_id=student_user_id).filter_by(testset_id=testset_id).all()
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

@api.route('/writing_search_assessment/')
@permission_required_or_multiple(Permission.WRITING_READ, Permission.TESTSET_READ)
def writing_search_assessment():
    year = request.args.get('year', '2020', type=str)
    test_type = request.args.get('test_type', 0, type=int)
    marker = request.args.get('marker', 0, type=int)

    marker_id = None
    if current_user.is_administrator():
        marker_id = current_user.id if marker == 0 else marker
    else:
        marker_id = current_user.id
    branch_ids = getBranchIds(marker_id)
    writing_code_id = Codebook.get_code_id('Writing')

    assessment_list = []
    assessments = common_writing_search_assessment(year, branch_ids, writing_code_id, test_type)
    for assessment in assessments:
        data = {}
        data['assessment_id'] = assessment.id
        data['assessment_name'] = assessment.name
        data['testset_name'] = assessment.name
        data['testset_id'] = assessment.testset_id
        data['testset_name'] = assessment.testset_name
        data['testset_version'] = assessment.version
        assessment_list.append(data)
    return success(assessment_list)

def common_writing_search_assessment(year, branch_ids, writing_code_id, test_type):
    writing_code_id = Codebook.get_code_id('Writing')

    query = db.session.query(Assessment.id, Assessment.name, Testset.id.label('testset_id'),
                             Testset.version, Testset.name.label('testset_name')). \
        join(AssessmentEnroll, Assessment.id == AssessmentEnroll.assessment_id). \
        join(Testset, Testset.id == AssessmentEnroll.testset_id). \
        join(Marking, AssessmentEnroll.id == Marking.assessment_enroll_id). \
        join(MarkingForWriting, Marking.id == MarkingForWriting.marking_id). \
        filter(AssessmentEnroll.start_time_client > datetime(int(year), 1, 1)). \
        filter(AssessmentEnroll.test_center.in_(branch_ids)). \
        filter(Testset.subject == writing_code_id)

    test_type = int(test_type)
    if test_type != 0:
        query = query.filter(Assessment.test_type == test_type)

    return query.distinct().order_by(Assessment.id.desc()).all()


@api.route('/writing_marking_list/downloaded', methods=['POST'])
def writing_marking_downloaded():
    marking_writing_id = request.form.get('id', 0, type=int)

    marking_writing = MarkingForWriting.query.filter_by(id=marking_writing_id).first()
    if marking_writing:
        if marking_writing.additional_info:
            infos = json.loads(marking_writing.additional_info)
            if 'downloaded' in infos:
                additional_info = {}
                changed = False
                for x, y in infos.items():
                    if x == 'downloaded':
                        if not y:
                            changed = True
                            additional_info[x] = True
                        else:
                            break
                    else:
                        additional_info[x] = y
                if changed:
                    marking_writing.additional_info = json.dumps(additional_info)
                    db.session.commit()

                return success()
            else:
                info = infos.copy()
                info['downloaded'] = True
                marking_writing.additional_info = json.dumps(info)
                db.session.commit()
                return success()
        else:
            additional_info = {
                'downloaded': True
            }
            marking_writing.additional_info = json.dumps(additional_info)
            db.session.commit()
            return success()
