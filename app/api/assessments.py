import json
import math
import os
import random
import re
import string
import subprocess
from datetime import datetime, timedelta
from functools import wraps
from time import time

import pytz
from flask import jsonify, request, current_app, render_template
from flask_login import current_user
from sqlalchemy import desc, or_
from sqlalchemy.orm import load_only
from werkzeug.utils import secure_filename

from app.api import api
from app.api.assessmentsession import AssessmentSession
from app.api.apicache import ApiCache
from app.api.jwplayer import get_signed_player, jwt_signed_url
from app.decorators import permission_required
from app.models import Testset, Permission, Assessment, TestletHasItem, \
    Marking, AssessmentEnroll, MarkingBySimulater, Student, MarkingForWriting, User, OnlineHelp
from common.logger import log
from qti.itemservice.itemservice import ItemService
from .response import success, bad_request, TEST_SESSION_ERROR
from .. import db, mail
from ..email import common_send_email, send_email
from ..models import Item, Codebook
from ..writing.views import text_to_images
from flask_mail import Message

def validate_session(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if request.method == 'GET':
            session_key = request.args.get('session')
        elif request.method == 'POST':
            if request.json:
                session_key = request.json.get('session')
            elif request.form:
                session_key = request.form.get('session')
            else:
                return bad_request(message="Session key is not provided!")
        else:
            return bad_request(message="Session key is not provided!")
        assessment_session = get_assessment_session(session_key)
        if assessment_session.error_code is not None:
            return bad_request(error_code=assessment_session.error_code,
                               message=assessment_session.error_message)
        kwargs['assessment_session'] = assessment_session
        return func(*args, **kwargs)
    return decorated_view


# Assessment > Testsets search Modal > Testsets return for apply
@api.route('/testset_list/')
@permission_required(Permission.ASSESSMENT_MANAGE)
def _search_testsets():
    search_test_type = request.args.get('test_type', 1, int)
    search_testset_name = request.args.get('testset_name', '01', str)
    search_grade = request.args.get('grade', 1, int)
    search_subject = request.args.get('subject', 1, int)

    query = Testset.query
    if search_testset_name != '':
        query = query.filter(Testset.name.ilike('%{}%'.format(search_testset_name)))
    if search_grade != 0:
        query = query.filter_by(grade=search_grade)
    if search_subject != 0:
        query = query.filter_by(subject=search_subject)
    if search_test_type != 0:
        query = query.filter_by(test_type=search_test_type)
    query = query.filter_by(active=True)
    query = query.filter(or_(Testset.delete.is_(False), Testset.delete.is_(None)))
    testsets = query.order_by(Testset.modified_time.desc()).all()
    rows = [(row.id, row.name, row.version, Codebook.get_code_name(row.grade), Codebook.get_code_name(row.subject)) for
            row in testsets]
    return jsonify(rows)


# Assessment > Testsets loading
@api.route('/testsets/')
@permission_required(Permission.ASSESSMENT_MANAGE)
def _get_testsets():
    id = request.args.get('id', 0, int)
    assessment = Assessment.query.filter_by(id=id).first()
    rows, testset_list = [], []
    for testset in assessment.testsets:
        if testset.delete == True:
            continue
        else:
            testset_list.append(testset)
    if assessment is not None:
        rows = [(row.id, row.name, Codebook.get_code_name(row.grade), Codebook.get_code_name(row.subject)) for
                row in testset_list]
    return jsonify(rows)


# Simulator
@api.route('/get_stage_testlet/', methods=['POST'])
@permission_required(Permission.TESTSET_MANAGE)
def get_stage_testlet():
    id = request.json['id']  # testset_id
    stage = request.json['stage']
    candidate_answers = request.json['candidate_answers']
    stage_data = request.json['stage_data']
    score = 1  # Todo: this value is for item outcome_score so need to add item table for the correct simulation
    assessment_enroll_id = None  # Todo: need to change this value lator
    percentile = 0
    if len(candidate_answers) != 0:
        sum_score = 0
        testlet_id = candidate_answers["testlet_id"]
        for item in candidate_answers["items"]:
            query = MarkingBySimulater.query
            query = query.filter_by(testset_id=id)
            query = query.filter_by(testlet_id=testlet_id)
            query = query.filter_by(item_id=item["item"])
            marking = query.first()
            marking.is_correct = item["iscorrect"]
            if item["iscorrect"]:
                marking.candidate_mark = marking.outcome_score
            else:
                marking.candidate_mark = 0
            sum_score = sum_score + marking.getScore()
        outcomeTotal = MarkingBySimulater.getTotalOutcomeScore(assessment_enroll_id, id,
                                                               candidate_answers["testlet_id"])
        percentile = sum_score / outcomeTotal * 100  # Student's marked percentile
    else:
        testlet_id = 0

    next_branch_json = get_next_testlet(stage_data, id, testlet_id, percentile)
    if next_branch_json:
        next_testlet_id = next_branch_json.get("id")
    else:
        # when last stage of branch, no next branch data formed and return empty data
        rows = [(0, '', 0, 0, 0, percentile)]
        MarkingBySimulater.query.filter_by(assessment_enroll_id=None).delete()
        db.session.commit()
        return jsonify(rows)

    items = TestletHasItem.query.filter_by(testlet_id=next_testlet_id).order_by(TestletHasItem.order.asc()).all()
    index = 1
    for item in items:
        marking = MarkingBySimulater(question_no=index,
                                     testset_id=id,
                                     testlet_id=next_testlet_id,
                                     item_id=item.item_id,
                                     weight=item.weight,
                                     candidate_mark=0,
                                     outcome_score=score)
        marking.assessment_enroll_id = assessment_enroll_id
        db.session.add(marking)
        index += 1
    db.session.commit()

    rows = [(1 + int(stage), next_branch_json.get("name"), next_testlet_id, row.item_id, row.weight, percentile) for row
            in items]
    return jsonify(rows)


'''
@api.route('/get_next_stage/', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
def get_next_stage():
    assessment_enroll_id = request.json['assessment_enroll_id']  # assessment_enroll_id
    testset_id = request.json['testset_id']  # testset_id
    testlet_id = request.json['testlet_id']  # testlet_id
    # or marking_id 로 바꿀수 있다
    stage = request.json['stage']
    stage_data = request.json['stage_data']

    # scoring
    sum_score = 0
    percentile = 0
    markings = MarkingBySimulater.query.filter_by(assessment_enroll_id=int(assessment_enroll_id)).\
                            filter_by(testset_id=int(testset_id)).\
                            filter_by(testlet_id=int(testlet_id)).all()
    if len(markings)>0:
        for marking in markings:
            sum_score = sum_score + marking.getScore()
        outcomeTotal = MarkingBySimulater.getTotalOutcomeScore(assessment_enroll_id, testset_id, testlet_id)
        percentile = sum_score / outcomeTotal * 100  # Student's marked percentile

    next_branch_json = get_next_testlet(stage_data, testset_id, testlet_id, percentile)
    print(str(testset_id)+':'+str(stage)+':'+str(testlet_id)+':'+str(percentile))
    if not next_branch_json:
        rows = [(0,0,0,0,0)]
        # Todo: Delete these temporary simulating data. It is just for 1 time testing.
        #       and need to remove delete lator with valid assessment_enroll_id
        MarkingBySimulater.query.filter_by(assessment_enroll_id=1).delete()
        db.session.commit()
    else:
        next_testlet_id = next_branch_json.get("id")
        return redirect(url_for('api.get_stage_items', stage = stage, assessment_enroll_id=assessment_enroll_id,
                                 testset_id=testset_id, testlet_id=next_testlet_id))
    return jsonify(rows)
'''

"""
*** Assessment session handling ***
    + Response
        {
            "status": "in_testing",
            "data" : {}
        }
    + Main status
        - ready: Test is not started.
        - in_testing: Test is tarted and giving items to students.
        - submit_ready: All test items are marked and ready to submit.
        - test_finished: The testset is submitted.
    + APIs
        - session(POST): Create a new assessment session.
        - start(POST): Start a testset in an assessment.
        - responses(POST): Submit a response and get transition information.
        - next_stage(POST): Finalize this stage and move to next one
        - item(GET): Get item
        - submit(POST): Finalize all test and close this testset 
    + helper functions
        - get_next_item(assessment_session, current_question_no)
                ~ 
"""


@api.route('/session', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
def create_session():
    """ Create a new assessment session.
    o 2가지 경우가 있다.
        + 시험을 처음 시작하는 경우 : session_id 가 없다.
        + 시험을 다시 시작하는 경우 : session_id 가 있다.
    1. session_id 가 있는 경우 session 을 찾는다.(/start 에서 처리)
        a. session 이 존재하고 active 인 경우
            + 중단한 시험을 바로 이어 시작하는 경우이다.
            + session 을 복사해서 새로 생성하고 이전 것은 inactive 로 변경한다.
        b.  session 이 존재하고 inactive 인 경우
            + 시험이 다른 기기나 브라우저에서 다시 시작된 경우이다.
            + 서버에서는 에러를 주고, client 에서는 경고를 주고 시험을 진행할 수 없도록 한다.
        c. session 이 존재하재 하지 않는 경우
            + session 이 존재하지 않는 다는 것은 시간이 지나서 삭제되었다는 것을 의미함.
    2. session_id 가 없는 경우
        a. DB 에 assessment_enroll 이 존재하지 않는 경우 (/session 에서 처리)
            + 새로운 session 을 시작한다.
        b. DB 에 assessment_enroll 이 존재하는 경우(/resume 에서 처리)
            + 시험 시간이 남은 경우는 시험 시간이 남았으니 다시 해 보라고 한다.
            + 시험 시간이 남지 않은 경우는 시험이 끝났다고 알려준다.
    :return:
    """
    assessment_guid = request.json.get('assessment_guid')
    testset_id = request.json.get('testset_id')
    start_time = request.json.get('start_time')
    student_ip = request.json.get('student_ip')
    tnc_agree_checked = request.json.get('tnc_agree_checked', False)

    if tnc_agree_checked is False:
        return bad_request()

    # 1. check if there is an assessment with the guid and get the latest one.
    assessment = Assessment.query.filter_by(GUID=assessment_guid).order_by(Assessment.version.desc()).first()
    if assessment is None:
        return bad_request()

    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return bad_request()
    student_user_id = student.user_id

    testset = Testset.query.filter_by(id=testset_id).first()
    if testset is None:
        return bad_request('testset_id', message="Cannot find testset_id {}".format(testset_id))

    # 2. check if the student went through the testset.
    # If we only handle single test, it's time to check count and proceed or stop processing.
    # did_enroll_count = AssessmentEnroll.query.filter_by(assessment_guid=assessment_guid,
    #                                                     student_user_id=student_user_id).count()

    # 3. Find out the test attempt count. ==> 시험은 1회만 허용한다. 단 homework 는 정해진 기간 안에 무제한 가능하다.
    last_attempt = AssessmentEnroll.query.filter_by(assessment_guid=assessment_guid, student_user_id=student_user_id,
                                                    testset_id=testset_id)\
        .order_by(desc(AssessmentEnroll.attempt_count)).first()

    attempt_count = 1
    if last_attempt is not None:
        # Homework 가 아니거나 homework 이더라도 시험이 진행중이면 새로 시작할 수는 없다.
        if not assessment.is_homework or not AssessmentEnroll.is_finished:
            return bad_request(error_code=TEST_SESSION_ERROR,
                               message="This session is invalid! A new session has been started from another browser.")
        else:
            attempt_count = last_attempt.attempt_count + 1

    # 4. Create a new enroll
    # assessment_type_name = Codebook.get_code_name(assessment.test_type)
    assessment_type_name = assessment.test_type_name
    if assessment.is_homework:
        au_tz = pytz.timezone('Australia/Sydney')
        session_date = datetime(assessment.session_valid_until.year, assessment.session_valid_until.month,
                                assessment.session_valid_until.day, tzinfo=au_tz) + timedelta(days=1)
        now = datetime.now(tz=au_tz)
        remaining = session_date - now
        test_duration = int(remaining.total_seconds() / 60)
    else:
        test_duration = testset.test_duration or 70
    enrolled = AssessmentEnroll(assessment_guid=assessment_guid, assessment_id=assessment.id, testset_id=testset_id,
                                student_user_id=student_user_id, attempt_count=attempt_count,
                                test_duration=test_duration, assessment_type=assessment_type_name)
    if student_ip:
        enrolled.start_ip = student_ip
    elif 'HTTP_X_FORWARDED_FOR' in request.headers.environ:
        enrolled.start_ip = request.headers.environ['HTTP_X_FORWARDED_FOR']
    else:
        enrolled.start_ip = request.headers.environ['REMOTE_ADDR']
    test_center = Codebook.get_testcenter_of_current_user()
    if test_center:
        enrolled.test_center = test_center.id
    enrolled.start_time = datetime.utcnow()
    enrolled.start_time_client = datetime.fromtimestamp(start_time, pytz.utc)
    db.session.add(enrolled)
    db.session.commit()
    assessment_enroll_id = enrolled.id

    assessment_session = new_assessment_session(current_user.id, assessment_enroll_id,
                                                testset_id, test_duration, attempt_count)
    assessment_session.set_value('start_time', int(time()))

    # Start a new assessment session.
    assessment_session.set_status(AssessmentSession.STATUS_IN_TESTING)
    # session key 를 enroll db 에 저장한다.
    enrolled.session_key = assessment_session.key
    db.session.add(enrolled)
    db.session.commit()
    data = {
        'session': assessment_session.key,
    }
    return success(data)


@api.route('/start', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
@validate_session
def test_start(assessment_session):
    """ Start the test with session_id.
        전체적인 설명은 /session 참고
            a. session 이 존재하고 active 인 경우
                + 중단한 시험을 바로 이어 시작하는 경우이다.
                + session 을 복사해서 새로 생성하고 이전 것은 inactive 로 변경한다.
            b.  session 이 존재하고 inactive 인 경우
                + 시험이 다른 기기나 브라우저에서 다시 시작된 경우이다.
                + 서버에서는 에러를 주고, client 에서는 경고를 주고 시험을 진행할 수 없도록 한다.
            c. session 이 존재하재 하지 않는 경우
                + session 이 존재하지 않는 다는 것은 시간이 지나서 삭제되었다는 것을 의미함.

    :return:
    """
    session_id = request.json.get('session_id')
    # question_no = request.json.get('question_no')
    # assessment_session = AssessmentSession(key=session_id)
    # if assessment_session.assessment is None:
    #     return bad_request(message="session is expired or not exists.")

    # status = assessment_session.get_value('status')
    # if status == AssessmentSession.STATUS_TEST_SUBMITTED:
    #     return bad_request(message="Test session finished already!")

    assessment_enroll_id = assessment_session.get_value('assessment_enroll_id')
    testset_id = assessment_session.get_value('testset_id')
    attempt_count = assessment_session.get_value('attempt_count')
    last_read_marking = Marking.query.filter_by(is_read=True, assessment_enroll_id=assessment_enroll_id)\
        .order_by(desc(Marking.read_time)).first()
    if last_read_marking is None:
        question_no = 1
    else:
        question_no = last_read_marking.question_no

    # Find markings.
    markings = Marking.query.filter_by(assessment_enroll_id=assessment_enroll_id, testset_id=testset_id) \
        .order_by(Marking.question_no).all()
    question_loaded = False
    # build test_items
    test_items = []
    for m in markings:
        info = {'question_no': m.question_no, 'item_id': m.item_id,
                'marking_id': m.id, 'is_flagged': m.is_flagged,
                'is_read': m.is_read,
                'saved_answer': m.candidate_r_value if m.candidate_r_value is not None else ''
                }
        test_items.append(info)
        if m.question_no == question_no:
            question_loaded = True
    assessment_session.set_value('test_items', test_items)
    if len(test_items) == 0 and question_no == 1:
        load_next_testlet(assessment_session)
    else:
        if question_loaded is False:
            return bad_request(message="Question No requested is not correct.")

    assessment_session.set_status(AssessmentSession.STATUS_IN_TESTING)
    # Load test_items from session. It has items already before load_next_testlet
    new_questions = assessment_session.get_value('test_items')
    next_question_no, next_item_id, next_marking_id = 0, 0, 0
    next_item = get_next_item(assessment_session, question_no - 1)
    data = {'is_read': False, 'is_flagged': False}
    if next_item is not None:
        # next_item_id = next_item.get('item_id')
        next_question_no = question_no
        next_marking_id = next_item.get('marking_id')
        marking = Marking.query.filter_by(id=next_marking_id).first()
        marking.is_read = True
        marking.read_time = datetime.utcnow()
        db.session.commit()
        data['is_flagged'] = marking.is_flagged
        data['is_read'] = marking.is_read
        # Mark this question as read
        for n_q in new_questions:
            if n_q['marking_id'] == next_marking_id:
                n_q['is_read'] = True
                break

    data.update({
        'status': assessment_session.get_status(),
        'session': assessment_session.key,
        'next_question_no': next_question_no,
        'test_duration': assessment_session.get_value('test_duration'),
        'start_time': assessment_session.get_value('start_time'),
        'current_time': int(time()),
        'new_questions': new_questions,
    })
    return success(data)


@api.route('/resume', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
def test_resume():
    """ Resume the test with session_id. 전체적인 설명은 /session 참고
        b. DB 에 assessment_enroll 이 존재하는 경우(/resume 에서 처리)
            + 시험 시간이 남은 경우는 시험 시간이 남았으니 다시 해 보라고 한다.
            + 시험 시간이 남지 않은 경우는 시험이 끝났다고 알려준다.
    :return:
    """
    session_key = request.json.get('session_key')
    assessment_session = get_assessment_session(session_key)
    if assessment_session.error_code is not None:
        return bad_request(error_code=assessment_session.error_code,
                           message=assessment_session.error_message)
    new_session_key = assessment_session.change_session_key()
    enroll = AssessmentEnroll.query.filter_by(id=assessment_session.get_value('assessment_enroll_id')).first()
    enroll.session_key = new_session_key
    # db.session.add(enroll)
    db.session.commit()
    return success({'session_key': new_session_key})


@api.route('/flag/<int:item_id>', methods=['PUT'])
@permission_required(Permission.ITEM_EXEC)
def flag(item_id):
    flagged = request.json.get('flagged', False)
    marking_id = request.json.get('marking_id')
    marking = Marking.query.filter_by(id=marking_id, item_id=item_id).first()
    marking.is_flagged = flagged
    if marking is None:
        return bad_request('marking_id', message='marking is not found.')
    db.session.commit()
    return success()


@api.route('/responses/<int:item_id>', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
@validate_session
def response_process(item_id, assessment_session=None):
    # item_id = request.json.get('item_id')
    question_no = request.json.get('question_no')
    session_key = request.json.get('session')
    marking_id = request.json.get('marking_id')
    response = request.json.get('response')
    file_names = request.json.get('file_names')
    direction = request.json.get('direction')
    if direction is None:
        direction = ''

    # assessment_session = AssessmentSession(key=session_key)

    # check session status
    # if assessment_session.get_status() == AssessmentSession.STATUS_READY:
    #     return bad_request(error_code=TEST_SESSION_ERROR, message='Session status is wrong.')
    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return bad_request(message='Student id is not valid!')
    # remove from the db session
    db.session.expunge(student)

    # check timeout: give 5 seconds gap
    timeout = (assessment_session.get_value('test_duration') * 60
               - (int(datetime.now().timestamp()) - assessment_session.get_value('start_time'))) + 5
    if timeout <= 0:
        return bad_request(error_code=TEST_SESSION_ERROR, message="Test session is finished!")

    # response_json = request.json
    qti_item_obj = Item.query.filter_by(id=item_id).first()
    # remove from the db session
    db.session.expunge(qti_item_obj)
    item_subject = Codebook.get_code_name(qti_item_obj.subject)
    writing_text = None
    if item_subject.lower() == 'writing':
        writing_text = request.json.get('writing_text')

    processed = None
    # correct_response = ''
    try:
        item_service = ItemService(qti_item_obj.file_link)
        # correct_response = item_service.get_item().get_correct_response()
        qti_xml = item_service.get_qti_xml_path()
        processing_php = current_app.config['QTI_RSP_PROCESSING_PHP']
        parameter = json.dumps({'response': response, 'qtiFilename': qti_xml})
        try:
            result = subprocess.run(['php', processing_php, parameter], stdout=subprocess.PIPE)
            processed = result.stdout.decode("utf-8")
            processed = json.loads(processed)
        except Exception as e:
            response['processed'] = "Not implemented."
    except Exception as e:
        print(e)
    if processed is None:
        return bad_request(message="Processing response error")

    if response.get("RESPONSE") and response.get("RESPONSE").get("base") and response.get("RESPONSE").get("base").get(
            'file'):
        candidate_response = response.get("RESPONSE").get("base")
    else:
        candidate_response = parse_processed_response(processed.get('RESPONSE'))
    if item_subject.lower() == 'writing':
        if writing_text is None and file_names is None:
            candidate_response = ''
        else:
            candidate_response = {}
            if writing_text is not None:
                candidate_response["writing_text"] = writing_text
            if file_names is not None:
                candidate_response["file_names"] = file_names
        candidate_r_value = candidate_response
    else:
        candidate_r_value = candidate_response

    # Get the last marking of this question.
    last_marking = Marking.query.filter_by(id=marking_id).first()
    # We don't need to read back the changes.
    db.session.expunge(last_marking)
    marking_testlet_id = last_marking.testlet_id

    candidate_mark = processed.get('SCORE')
    outcome_score = processed.get('maxScore')
    is_correct = candidate_mark >= outcome_score
    correct_r_value = parse_correct_response(processed.get('correctResponses'))
    last_r_value = last_marking.candidate_r_value
    last_is_correct = last_marking.is_correct
    # Update changes
    marking_updated = {
        "candidate_r_value": candidate_r_value,
        "candidate_mark": candidate_mark,
        "outcome_score": outcome_score,
        "is_correct": is_correct,
        "correct_r_value": correct_r_value,
    }
    if last_r_value is not None:
        marking_updated["last_r_value"] = last_r_value
    if last_is_correct is not None:
        marking_updated["last_is_correct"] = last_is_correct
    db.session.query(Marking).filter(Marking.id == marking_id).update(marking_updated)
    db.session.commit()

    assessment_session.set_saved_answer(marking_id, candidate_r_value)

    next_question_no, next_item_id, next_marking_id = 0, 0, 0
    next_item = None
    if direction == 'back':
        next_item = get_previous_item(assessment_session, question_no)
    else:
        next_item = get_next_item(assessment_session, question_no)
    data = None
    if direction == 'back':
        data = {'is_read': True, 'is_flagged': False}
    else:
        data = {'is_read': False, 'is_flagged': False}
    if next_item is None:
        # There is 2 cases where next_item is None
        #   1. It consumed all of the current testlet items. ==> Ask to proceed to a next testlet.
        #   2. It consumed all of the current testset items.  ==> Ask to submit the testset.
        if can_load_next_testlet(assessment_session, marking_testlet_id):
            assessment_enroll_id = assessment_session.get_value('assessment_enroll_id')
            testset_id = assessment_session.get_value('testset_id')
            markings = Marking.query.filter_by(assessment_enroll_id=assessment_enroll_id,
                                               testset_id=testset_id, testlet_id=marking_testlet_id) \
                .order_by(Marking.question_no).all()
            start = markings[0].question_no
            end = markings[-1].question_no
            data['html'] = render_template("runner/stage_finished.html", start=start, end=end)
            data['testlet_id'] = marking_testlet_id
            data['question_no'] = question_no
            assessment_session.set_status(AssessmentSession.STATUS_STAGE_FINISHED)
        else:
            testset_id = assessment_session.get_value('testset_id')
            testset = Testset.query.with_entities(Testset.test_type).filter_by(id=testset_id).first()
            test_type = testset.test_type
            assessment_session.set_status(AssessmentSession.STATUS_TEST_FINISHED)
            data['html'] = render_template("runner/test_finished.html", test_type=test_type)
    else:
        next_item_id = next_item.get('item_id')
        next_question_no = None
        if direction == 'back':
            next_question_no = question_no - 1
        else:
            next_question_no = question_no + 1
        next_marking_id = next_item.get('marking_id')
        marking = Marking.query.filter_by(id=next_marking_id).first()
        data['is_flagged'] = marking.is_flagged
        data['is_read'] = True
        data['next_saved_answer'] = marking.candidate_r_value if marking.candidate_r_value is not None else ""
        # Comment out codes. Update will be done in rendered.
        # marking.is_read = True
        # marking.read_time = datetime.utcnow()
        # db.session.commit()

    if direction == 'back':
        assessment_session.set_status(AssessmentSession.STATUS_IN_TESTING)

    data.update({
        'status': assessment_session.get_status(),
        'session': session_key,
        'question_no': question_no,
        'saved_answer': candidate_response,
        'next_item_id': next_item_id,
        'next_question_no': next_question_no,
        'next_marking_id': next_marking_id,
        'test_duration': assessment_session.get_value('test_duration'),
        'start_time': assessment_session.get_value('start_time'),
    })
    return success(data)


@api.route('/responses/file/<int:item_id>', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
@validate_session
def response_process_file(item_id, assessment_session=None):
    session_key = request.form.get('session')
    marking_id = request.form.get('marking_id')
    writing_files = request.files.getlist('files')
    writing_text = request.form.get('writing_text')
    has_files = request.form.get('has_files', 'false')
    has_files = has_files.lower() == 'true'
    for f in writing_files:
        if allowed_file(f.filename) is False:
            return bad_request(message='File type is not supported.')

    # assessment_session = AssessmentSession(key=session_key)
    # check session status
    # if assessment_session.get_status() == AssessmentSession.STATUS_READY:
    #     return bad_request(message='Session status is wrong.')

    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return bad_request()
    student_user_id = student.user_id
    save_writing_data(student_user_id, marking_id, writing_files=writing_files, writing_text=writing_text,
                      has_files=has_files)

    return success({"result": "success"})


def save_writing_data(student_user_id, marking_id, writing_files=None, writing_text=None, has_files=False):
    if writing_files is None:
        writing_files = []
    file_names = []
    # 1.1 Save the file to the path at config['USER_DATA_FOLDER']
    for writing_file in writing_files:
        file_name = writing_file.filename if writing_file is not None else 'writing.txt'
        random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=24))
        new_file_name = 'file_' + str(student_user_id) + '_' + random_name + '_' + secure_filename(file_name)
        writing_upload_dir = os.path.join(current_app.config['USER_DATA_FOLDER'], str(student_user_id), "writing")
        item_file = os.path.join(writing_upload_dir, new_file_name)
        if not os.path.exists(writing_upload_dir):
            os.makedirs(writing_upload_dir)
        writing_file.save(item_file)
        file_names.append(new_file_name)

    marking_writing = MarkingForWriting.query.filter_by(marking_id=marking_id) \
        .order_by(MarkingForWriting.id.desc()).first()
    if len(writing_files) == 0 and has_files and marking_writing is not None:
        candidate_file_link = json.loads(marking_writing.candidate_file_link)
        for f_n in candidate_file_link.values():
            if not f_n.startswith('writing'):
                file_names.append(f_n)

    # 1.2 Save the text to the path at config['USER_DATA_FOLDER']
    if writing_text is not None:
        file_name = 'writing.txt'
        random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=24))
        new_file_name = 'writing_' + str(student_user_id) + '_' + random_name + '_' + secure_filename(file_name)
        writing_upload_dir = os.path.join(current_app.config['USER_DATA_FOLDER'], str(student_user_id), "writing")
        item_file = os.path.join(writing_upload_dir, new_file_name)
        if not os.path.exists(writing_upload_dir):
            os.makedirs(writing_upload_dir)
        with open(item_file, "w") as f:
            f.write(writing_text)
        file_names += text_to_images(student_user_id, item_file)

    # 2. Create a record in MarkingForWriting
    index = 1
    candidate_file_link_json = {}
    for file_name in file_names:
        candidate_file_link_json["file%s" % index] = file_name
        index += 1
    if marking_writing is None:
        marking_writing = MarkingForWriting(marking_id=marking_id, marker_id=current_user.id)
    marking_writing.candidate_file_link = candidate_file_link_json
    marking_writing.modified_time = datetime.utcnow()
    db.session.add(marking_writing)
    db.session.commit()


def allowed_file(filename):
    """
    Call from writing.saveWritingFile to check file extension allowed
    :param filename:
    :return:
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['WRITING_ALLOWED_EXTENSIONS']


def parse_correct_response(correct_response_org):
    """
    PHP 에서 parsing 해서 넘어온 정답이 리스트 형태인 경우 최대한 리스트 object 로 변환을 해 본다.
    안되면 그냥 그대로 string 으로 저장을 한다.
    """
    correct_response = correct_response_org.strip()
    if correct_response != '' and correct_response[0] == '[':
        try:
            correct_response = json.loads(correct_response)
        except json.decoder.JSONDecodeError:
            try:
                # correct_response 가 "['red', 'blue']" 로 넘어 오는 경우.
                correct_response = correct_response.replace("'", '"')
                correct_response = json.loads(correct_response)
            except json.decoder.JSONDecodeError:
                correct_response = correct_response_org
        return correct_response
    return correct_response_org


def parse_processed_response(candidate_response):
    from json import JSONDecodeError
    candidate_response = candidate_response.strip()
    if candidate_response != '' and candidate_response[0] == '[':
        responses = candidate_response[1:-1].replace("'", "").split(';')
        candidate_response = []
        for r in responses:
            r = r.strip()
            candidate_response.append(r)
    elif candidate_response != '':
        try:
            rsp = json.loads(candidate_response)
            if type(rsp) == dict:
                candidate_response = rsp
        except TypeError:
            pass
        except JSONDecodeError:
            pass
    return candidate_response


@api.route('/rendered/<int:item_id>', methods=['GET'])
@permission_required(Permission.ITEM_EXEC)
@validate_session
def rendered(item_id, assessment_session=None):
    assessment_session.set_status(AssessmentSession.STATUS_IN_TESTING)

    # 이미 캐시에 저장된 rendering 된 html 이 있다면 그걸 사용한다.
    # 없다면 새로 만들어서 캐시에 저장해 둔다.
    rendered_template_key = "item-{id:08d}-rendered".format(id=item_id)
    rendered_cache = ApiCache()
    cache_enabled = current_app.config['API_RENDERED_CACHE'] == 'enabled'
    if cache_enabled:
        response = rendered_cache.get(rendered_template_key)
    else:
        response = None
    if response is None:
        rendered_item = ''
        response = {}
        qti_item_obj = Item.query.filter_by(id=item_id).first()
        item_subject = Codebook.get_code_name(qti_item_obj.subject)
        try:
            item_service = ItemService(qti_item_obj.file_link)
            qti_item = item_service.get_item()
            rendered_item = qti_item.to_html()
            response['type'] = qti_item.get_interaction_type()
            response['cardinality'] = qti_item.get_cardinality()
            response['object_variables'] = qti_item.get_interaction_object_variables()
            response['interactions'] = qti_item.get_interaction_info()
            response['subject'] = item_subject
        except Exception as e:
            print(e)

        # debug mode 일 때만 정답을 표시할 수 있도록 하기위해
        debug_rendering = os.environ.get('DEBUG_RENDERING') == 'true'
        rendered_template = render_template("runner/test_item.html", item=qti_item_obj, debug_rendering=debug_rendering)
        if rendered_item:
            rendered_template = rendered_template.replace('rendered_html', rendered_item)
        response['html'] = rendered_template

        # 캐시에 저장한다.
        # timeout ==> defined in config.py as API_RENDERED_CACHE_TIMEOUT
        if cache_enabled:
            rendered_cache.set(rendered_template_key, response)

    # 문제를 앞뒤로 왔다 갔다 하는 경우에 대해서도 read time 을 기록해 준다.
    # 브라우저를 refresh 하거나 다른 브라우저에서 로그인한 경우 어떤 item 을 보여줄 지 결정할 때 사용한다.
    marking_id = assessment_session.marking_id_from_item_id(item_id)
    db.session.query(Marking).filter(Marking.id == marking_id).update({"is_read": True, "read_time": datetime.utcnow()})
    db.session.commit()

    media_id_match = re.search(r"http://jwplayer-id/([a-zA-Z0-9]+)", response['html'])
    if media_id_match:
        test_duration_min = assessment_session.get_value('test_duration')
        start_time_sec = assessment_session.get_value('start_time')
        remained_sec = test_duration_min*60 - int(datetime.now().timestamp() - start_time_sec)
        # Max time remained set to 50 minutes
        remained_sec = min(max(remained_sec, 0), 3000)
        # Link is valid for remained_sec but normalized to 5 minutes to promote better caching
        expires = math.ceil((time() + remained_sec) / 300) * 300
        media_id = media_id_match.group(1)
        jw_key = current_app.config['JWAPI_CREDENTIAL']
        player_id = current_app.config['JWPLAYER_ID']
        signed_player_url = get_signed_player(player_id, jw_key, expires)
        path = "/v2/media/{media_id}".format(media_id=media_id)
        media_url = jwt_signed_url(path, jw_key, expires)
        response['jw_player'] = {
            'player_url': signed_player_url, 'media_url': media_url
        }
    return success(response)


@api.route('/next_stage', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
@validate_session
def next_stage(assessment_session):
    session_key = request.json.get('session')
    testlet_id = request.json.get('testlet_id')
    question_no = request.json.get('question_no')

    # assessment_session = AssessmentSession(key=session_key)

    # check session status
    if assessment_session.get_status() != AssessmentSession.STATUS_STAGE_FINISHED:
        return bad_request(message='Session status is wrong.')

    new_questions = load_next_testlet(assessment_session, testlet_id)
    next_item = get_next_item(assessment_session, question_no)
    next_question_no, next_item_id, next_marking_id = 0, 0, 0
    data = {'is_read': False, 'is_flagged': False}
    if next_item is not None:
        assessment_session.set_status(AssessmentSession.STATUS_IN_TESTING)
        next_item_id = next_item.get('item_id')
        next_question_no = question_no + 1
        next_marking_id = next_item.get('marking_id')
        marking = Marking.query.filter_by(id=next_marking_id).first()
        marking.is_read = True
        marking.read_time = datetime.utcnow()
        db.session.commit()
        data['is_read'] = True
        data['is_flagged'] = marking.is_flagged
        data['answer'] = marking.correct_r_value
        # Mark this question as read
        for n_q in new_questions:
            if n_q['marking_id'] == next_marking_id:
                n_q['is_read'] = True
                break
    data.update({
        'status': assessment_session.get_status(),
        'session': session_key,
        'next_item_id': next_item_id,
        'next_question_no': next_question_no,
        'next_marking_id': next_marking_id,
        'test_duration': assessment_session.get_value('test_duration'),
        'start_time': assessment_session.get_value('start_time'),
        'new_questions': new_questions
    })
    return success(data)


@api.route('/finish', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
@validate_session
def finish_test(assessment_session):
    session_key = request.json.get('session')
    finish_time = request.json.get('finish_time')
    # assessment_session = AssessmentSession(key=session_key)
    # check session status
    # if assessment_session.get_status() != AssessmentSession.STATUS_TEST_FINISHED:
    #     return bad_request(message='Session status is wrong.')

    if assessment_session.assessment:
        assessment_session.set_status(AssessmentSession.STATUS_TEST_SUBMITTED)
        assessment_enroll_id = assessment_session.get_value('assessment_enroll_id')
        enrolled = AssessmentEnroll.query.filter_by(id=assessment_enroll_id).first()
        if enrolled:
            enrolled.finish_time = datetime.utcnow()
            enrolled.finish_time_client = datetime.fromtimestamp(finish_time, pytz.utc)
            db.session.add(enrolled)
            db.session.commit()

    data = {'redirect_url': '/tests/assessments'}
    return success(data)

@api.route('/online/help/report', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
@validate_session
def online_help_report(assessment_session):
    enroll_id = request.form.get('id', 0, type=int)
    desc = request.form.get('desc', '', type=str)
    test_type = request.form.get('type', '', type=str)
    requester_email = request.form.get('email', '', type=str)


    return bad_request()
    try:
        assessment_enroll = db.session.query(Assessment.id, Assessment.name,
                AssessmentEnroll.finish_time, AssessmentEnroll.start_time,
                Testset.name.label('testset_name'), Testset.grade). \
            join(AssessmentEnroll, Assessment.id == AssessmentEnroll.assessment_id). \
            join(Testset, Testset.id == AssessmentEnroll.testset_id). \
            filter(AssessmentEnroll.id == enroll_id).first()

        if assessment_enroll is None:
            return bad_request()

        au_tz = pytz.timezone('Australia/Sydney')
        now = datetime.now(tz=au_tz)

        test_center_name = ''
        student_id = ''
        cc = []
        if requester_email != '':
            cc.append(requester_email)

        student = Student.query.filter_by(user_id=current_user.id).first()
        if student:
            student_id = student.student_id

            test_center = Codebook.query.filter(Codebook.code_type == 'test_center',
                                         Codebook.additional_info.contains({"campus_prefix": student.branch})).first()
            if test_center:
                test_center_name = test_center.code_name

            online_help = Codebook.query.filter(Codebook.code_type == 'online_help').filter(Codebook.code_name == student.branch).first()
            if online_help:
                for user_id in online_help.additional_info["user_id"]:
                    userinfo = User.query.filter_by(id=user_id).first()
                    cc.append(userinfo.email)

        start_time = ''
        if assessment_enroll.start_time:
            start_time = assessment_enroll.start_time.strftime("%d/%m/%Y, %H:%M:%S")
        finish_time = ''
        if assessment_enroll.finish_time:
            finish_time = assessment_enroll.finish_time.strftime("%d/%m/%Y, %H:%M:%S")

        hours = 0
        minutes = 0
        seconds = 0
        if start_time != '' and finish_time != '':
            cal_time = assessment_enroll.finish_time - assessment_enroll.start_time
            seconds = cal_time.total_seconds()
            hours = int((seconds // 3600) % 24)
            minutes = int((seconds // 60) % 60)
            seconds = int(seconds % 60)

        itsupport = "itsupport@cseducation.com.au"
        sender = itsupport
        #sender = current_user.email
        #if not sender:
        #    sender = itsupport


        #test
        cc = ['hverityg@gmail.com', 'chsverity@cseducation.com.au']
        #sender = 'chsverity@cseducation.com.au'

        #OnlineHelp insert
        onlinehelp = OnlineHelp(student_user_id=current_user.id,
                                assessment_enroll_id=enroll_id,
                                test_type=test_type,
                                test_center_name=test_center_name,
                                cc=','.join(cc),
                                description=desc)
        db.session.add(onlinehelp)
        db.session.commit()

        #sending email
        common_send_email(sender, itsupport, cc, "CSEDU_COMMON_MAIL_SUBJECT_PREFIX"
                          , "From " + current_user.username + " in " + test_center_name, "auth/email/assessment_report"
                          , user_id=student_id
                          , user_name=current_user.username
                          , date=now.strftime("%d/%m/%Y, %H:%M:%S")
                          , assessment_name=assessment_enroll.name
                          , testset_name=assessment_enroll.testset_name
                          , test_type=test_type
                          , grade=Codebook.get_code_name(assessment_enroll.grade)
                          , test_center=test_center_name
                          , start_time=start_time
                          , finish_time=finish_time
                          , hours=hours
                          , minutes=minutes
                          , seconds=seconds
                          , contents=desc)
    except Exception as e:
        log.debug("Inward: %s" % e)
        return bad_request(message=e)

    return success({"result": "success"})


def get_next_item(assessment_session: AssessmentSession, current_question_no=0):
    """
    :param assessment_session:
    :param current_question_no: 학생이 보는 문제 번호. 1부터 시작.
    :return:
    """
    test_items = assessment_session.get_value('test_items')
    if len(test_items) == 0:
        return None
    # If current_question_no == 0, it means it's the first time requesting a test item.
    if current_question_no == 0:
        index = 0
    else:
        if len(test_items) <= current_question_no:
            return None
        else:
            index = current_question_no

    return test_items[index]

def get_previous_item(assessment_session: AssessmentSession, current_question_no=0):
    """
    :param assessment_session:
    :param current_question_no: 학생이 보는 문제 번호. 1부터 시작.
    :return:
    """
    test_items = assessment_session.get_value('test_items')
    if len(test_items) == 0:
        return None
    # If current_question_no == 0, it means it's the first time requesting a test item.
    if current_question_no == 0:
        index = 0
    else:
        index = current_question_no - 2

    return test_items[index]

def can_load_next_testlet(assessment_session: AssessmentSession, testlet_id=0):
    """
    Check if there is a next testlet.
    :param assessment_session:
    :param testlet_id:
    :return:
    """
    testset_id = assessment_session.get_value('testset_id')
    stage_data = assessment_session.get_value('stage_data')
    percentile = 0
    next_branch_json = get_next_testlet(stage_data, testset_id, testlet_id, percentile)
    return next_branch_json is not None


def load_next_testlet(assessment_session: AssessmentSession, testlet_id=0):
    assessment_enroll_id = assessment_session.get_value('assessment_enroll_id')
    testset_id = assessment_session.get_value('testset_id')
    stage_data = assessment_session.get_value('stage_data')
    test_items = assessment_session.get_value('test_items')
    attempt_count = assessment_session.get_value('attempt_count')
    # scoring
    sum_score = 0
    percentile = 0
    last_question_no = 0
    if testlet_id != 0:
        markings = Marking.query.filter_by(assessment_enroll_id=assessment_enroll_id,
                                           testset_id=testset_id, testlet_id=testlet_id) \
            .order_by(Marking.question_no).all()
        for marking in markings:
            sum_score = sum_score + marking.getScore()
            last_question_no = marking.question_no
            db.session.expunge(marking)
        outcome_total = Marking.getTotalOutcomeScore(assessment_enroll_id, testset_id, testlet_id)
        percentile = sum_score / outcome_total * 100  # Student's marked percentile

    next_branch_json = get_next_testlet(stage_data, testset_id, testlet_id, percentile)
    new_questions = []
    if next_branch_json is not None:
        testlet_id = next_branch_json.get("id")
        if stage_data is not None:
            stage = len(stage_data) + 1
            stage_data.append({'stage': stage, 'testlet_id': int(testlet_id), 'percentile': percentile})
            # stage 정보를 session 과 DB 에 저장한다.
            assessment_session.set_value('stage_data', stage_data)
        assessment_enroll = AssessmentEnroll.query.filter_by(id=assessment_enroll_id).first()
        assessment_enroll.stage_data = stage_data
        db.session.add(assessment_enroll)
        # db.session.commit()
        items = TestletHasItem.query.filter_by(testlet_id=testlet_id).order_by(TestletHasItem.order.asc()).all()
        marking_objects = []
        for item in items:
            if Marking.query.filter_by(assessment_enroll_id=assessment_enroll_id, testset_id=testset_id, testlet_id=testlet_id, item_id=item.item_id).count()==0:
                last_question_no += 1
                marking = Marking(testset_id=testset_id,
                                  testlet_id=testlet_id,
                                  item_id=item.item_id, question_no=last_question_no,
                                  weight=item.weight,
                                  assessment_enroll_id=assessment_enroll_id)
                marking_objects.append(marking)
                db.session.expunge(item)
        # higher performing “executemany” operations
        # https://docs.sqlalchemy.org/en/14/orm/session_api.html#sqlalchemy.orm.Session.bulk_save_objects
        db.session.bulk_save_objects(marking_objects, return_defaults=False)
        db.session.commit()
        markings = Marking.query.filter_by(assessment_enroll_id=assessment_enroll_id,
                                           testset_id=testset_id, testlet_id=testlet_id) \
            .order_by(Marking.question_no).all()
        for marking in markings:
            item_info = {'question_no': marking.question_no, 'item_id': marking.item_id,
                         'marking_id': marking.id, 'is_flagged': marking.is_flagged, 'is_read': marking.is_read,
                         'saved_answer': marking.candidate_r_value if marking.candidate_r_value is not None else ''
                         }
            test_items.append(item_info)
            new_questions.append(item_info)

        assessment_session.set_value('test_items', test_items)
    return new_questions


def get_next_testlet(stage_data, testset_id, testlet_id, percentile):
    testset = Testset.query.filter_by(id=testset_id).first()
    first_branch = testset.branching.get('data')[0]

    if stage_data is None or len(stage_data) == 0:
        next_branch = first_branch
    else:
        c_stage_no = stage_data[-1].get("stage")  # candidate's current stage_no
        c_testlet_id = stage_data[-1].get("testlet_id")  # candidate's current testlet_id
        if testlet_id != c_testlet_id:  # check if correct answer's testlet same as last testlet id
            return None

        next_branch = first_branch
        next_branches = []
        i = 0
        for s in stage_data:

            # for stage 2 .. n
            for b in next_branches:
                if int(b.get('id')) == int(s.get('testlet_id')):
                    next_branch = b
                    break

            curr_branch = next_branch
            if i == int(c_stage_no) - 1:  # last stage and find the next branching
                next_branches = curr_branch.get('next')
                if next_branches:
                    for b in next_branches:
                        _cond = b.get('condition')
                        if percentile >= _cond:
                            next_branch = b
                            break
                else:
                    next_branch = None
            else:
                # for stage 1..n
                next_branches = curr_branch.get('next')
            i = i + 1
    return next_branch


@api.route('/get_item/', methods=['GET'])
@permission_required(Permission.ITEM_EXEC)
def get_item_from_marking():
    id = request.args.get('marking_id')
    item = Marking.query.options(load_only("item_id")).filter_by(id=id).first()
    rows = [(row.id, row.correct_answer) for
            row in item]
    return jsonify(rows)


@api.route('/set_student_marking/', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
def set_student_marking():
    marking_id = request.form.get('marking_id')
    item_id = request.form.get('item_id')
    candidate_r_value = request.form.get('candidate_r_value')
    correct_r_value = request.form.get('correct_r_value')
    outcome_score = request.form.get('outcome_score')
    candidate_mark = request.form.get('candidate_mark')

    marking = Marking.query.filter_by(id=int(marking_id)).filter_by(item_id=int(item_id)).first()
    if marking:
        marking = Marking.query.filter_by(id=marking_id).first()
        marking.candidate_mark = candidate_mark
        marking.candidate_r_value = candidate_r_value
        marking.correct_r_value = correct_r_value
        marking.outcome_score = outcome_score
        marking.modified_time = datetime.now(pytz.utc)
        if candidate_mark == outcome_score:
            marking.is_correct = True
        else:
            marking.is_correct = False
        db.session.commit()
    else:
        candidate_mark = 0
    return candidate_mark


def new_assessment_session(user_id, enroll_id, testset_id, test_duration, attempt_count):
    return AssessmentSession(user_id, enroll_id, testset_id, test_duration, attempt_count)


def get_assessment_session(session_key):
    assessment_session = AssessmentSession(key=session_key)
    if assessment_session.assessment is None:
        enroll_id = AssessmentSession.enrol_id_from_session_key(session_key)
        # 동일한 assessment id, testset id 조합으로 enroll 은 유일해야한다.
        # 혹시 몰라서 start_time 을 기준 최신을 확인.
        enroll = AssessmentEnroll.query.filter(AssessmentEnroll.id == enroll_id) \
            .order_by(desc(AssessmentEnroll.start_time)).first()
        # session 이 없는 이유를 알아본다.
        if enroll.is_finished:
            assessment_session.set_error(TEST_SESSION_ERROR, "Test session is finished!")
        elif enroll.session_key != session_key:
            assessment_session.set_error(
                TEST_SESSION_ERROR,
                "This session is invalid! A new session has been started from another browser."
            )
        else:
            # 이 경우라면 DB 로부터 session 을 복원한다.
            assessment_session.reset(current_user.id, enroll_id, enroll.testset_id,
                                     enroll.test_duration, enroll.attempt_count, enroll.start_time)
            assessment_session.set_value('stage_data', enroll.stage_data)
            markings = Marking.query.filter_by(assessment_enroll_id=enroll_id, testset_id=enroll.testset_id) \
                .order_by(Marking.question_no).all()
            # build test_items
            test_items = []
            for m in markings:
                info = {'question_no': m.question_no, 'item_id': m.item_id,
                        'marking_id': m.id, 'is_flagged': m.is_flagged,
                        'is_read': m.is_read,
                        'saved_answer': m.candidate_r_value if m.candidate_r_value is not None else ''
                        }
                test_items.append(info)
            assessment_session.set_value('test_items', test_items)

    return assessment_session


# correct_r_value & candidate_r_value : JSON or string ?
def get_correct_r_value():
    pass


def get_outcome_score():
    pass


def get_candidate_mark():
    pass


'''
@api.route('/get_stage_items/', methods=['GET'])
@permission_required(Permission.ITEM_EXEC)
def get_stage_items():
    assessment_enroll_id = request.args.get("assessment_enroll_id")
    testset_id = request.args.get("testset_id")
    testlet_id = request.args.get("testlet_id")
    stage = request.args.get("stage")

    items = TestletHasItem.query.filter_by(testlet_id=testlet_id).order_by(TestletHasItem.order.asc()).all()
    marking_ids = []

    for item in items:
        marking = Marking(testset_id=testset_id,
                          testlet_id=testlet_id,
                          item_id=item.item_id,
                          weight=item.weight,
                          assessment_enroll_id=assessment_enroll_id)
        # correct_r_value, outcome_score : decide when set
        # candidate_r_value, candidate_mark, is_correct : need data whenever item submit
        # duration, flag, is_flag, modified_time : need data whenever item submit
        db.session.add(marking)
        db.session.commit()
        marking_ids.append(marking.id)

    marking_id_list = [i for i in marking_ids]

    markings = Marking.query.filter(Marking.id.in_(marking_id_list)).all()
    rows = [(str(1 + int(stage)), str(row.id), str(row.testlet_id), str(row.item_id)) for row
            in markings]
    # print(rows)
    return jsonify(rows)
'''

