import json
import os
import subprocess
from datetime import datetime, timezone
from time import time
from functools import wraps

from flask import jsonify, request, current_app, render_template
from flask_login import current_user

from app.api import api
from app.decorators import permission_required
from app.models import Permission, AssessmentEnroll, Marking, Item, Codebook, Student
from qti.itemservice.itemservice import ItemService
from .response import success, bad_request, TEST_SESSION_ERROR
from .errorrunsession import ErrorRunSession
from .. import db


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
        run_session = get_run_session(session_key)
        if run_session.error_code is not None:
            return bad_request(error_code=run_session.error_code,
                               message=run_session.error_message)
        kwargs['run_session'] = run_session
        return func(*args, **kwargs)
    return decorated_view


def get_run_session(session_key):
    run_session = ErrorRunSession(key=session_key)
    if run_session.assessment is None:
        run_session.set_error(TEST_SESSION_ERROR, "Session is finished!")
    return run_session


def new_error_run_session(user_id, enroll_id, testset_id, test_duration, attempt_count):
    return ErrorRunSession(user_id, enroll_id, testset_id, test_duration, attempt_count)


def get_next_item(error_run_session: ErrorRunSession, current_question_no=0):
    """
    :param error_run_session:
    :param current_question_no: 학생이 보는 문제 번호. 1부터 시작.
    :return:
    """
    test_items = error_run_session.get_value('test_items')
    for item in test_items:
        if item['question_no'] > current_question_no:
            return item

    return None


def parse_correct_response(correct_response):
    correct_response = correct_response.strip()
    if correct_response != '' and correct_response[0] == '[':
        correct_response = correct_response.replace("'", '"')
        correct_response = json.loads(correct_response)
    return correct_response


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


@api.route('/errorrun/start', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
def start_error_run():
    assessment_enroll_id = request.json.get('assessment_enroll_id')
    enrolled = AssessmentEnroll.query.filter_by(id=assessment_enroll_id).first()
    user_id = current_user.id
    error_run_session = new_error_run_session(user_id, assessment_enroll_id, enrolled.testset_id,
                                              enrolled.test_duration, 1)
    # Find markings.
    markings = Marking.query.filter_by(assessment_enroll_id=assessment_enroll_id, testset_id=enrolled.testset_id,
                                       last_is_correct=False) \
        .order_by(Marking.question_no).all()
    question_no = -1
    # build test_items
    test_items = []
    for m in markings:
        info = {'question_no': m.question_no, 'item_id': m.item_id,
                'marking_id': m.id, 'is_flagged': m.is_flagged,
                'is_read': False,
                'saved_answer': ''
                }
        if question_no == -1:
            question_no = m.question_no
            info['is_read'] = True
        test_items.append(info)
    error_run_session.set_value('test_items', test_items)
    next_question_no = 0
    next_item = get_next_item(error_run_session, question_no - 1)
    data = {'is_read': False, 'is_flagged': False}
    if next_item is not None:
        # next_item_id = next_item.get('item_id')
        next_question_no = next_item['question_no']
        next_marking_id = next_item.get('marking_id')
        marking = Marking.query.filter_by(id=next_marking_id).first()
        marking.is_read = True
        # marking.read_time = datetime.utcnow()
        # db.session.commit()
        data['is_flagged'] = marking.is_flagged
        data['is_read'] = marking.is_read

    data.update({
        'status': error_run_session.get_status(),
        'session': error_run_session.key,
        'next_question_no': next_question_no,
        'test_duration': error_run_session.get_value('test_duration'),
        'start_time': error_run_session.get_value('start_time'),
        'current_time': int(time()),
        'new_questions': test_items,
    })
    return success(data)


@api.route('/errorrun/rendered/<int:item_id>', methods=['GET'])
@permission_required(Permission.ITEM_EXEC)
@validate_session
def error_run_rendered(item_id, run_session=None):
    session_key = request.args.get('session')
    # assessment_session = AssessmentSession(key=session_key)
    run_session.set_status(ErrorRunSession.STATUS_IN_TESTING)
    response = {}
    rendered_item = ''
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
    # 문제를 앞뒤로 왔다 갔다 하는 경우에 대해서도 ream time 을 기록해 준다.
    enroll_id = ErrorRunSession.enrol_id_from_session_key(session_key)
    response['html'] = rendered_template
    return success(response)


@api.route('/errorrun/responses/<int:item_id>', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
@validate_session
def error_run_response_process(item_id, run_session=None):
    question_no = request.json.get('question_no')
    session_key = request.json.get('session')
    marking_id = request.json.get('marking_id')
    response = request.json.get('response')
    file_names = request.json.get('file_names')

    # assessment_session = AssessmentSession(key=session_key)

    # check session status
    # if assessment_session.get_status() == AssessmentSession.STATUS_READY:
    #     return bad_request(error_code=TEST_SESSION_ERROR, message='Session status is wrong.')
    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return bad_request(message='Student id is not valid!')

    # check timeout: give 5 seconds gap
    # timeout = (run_session.get_value('test_duration') * 60
    #            - (int(datetime.now().timestamp()) - run_session.get_value('start_time'))) + 5
    # if timeout <= 0:
    #     return bad_request(error_code=TEST_SESSION_ERROR, message="Test session is finished!")

    # response_json = request.json
    qti_item_obj = Item.query.filter_by(id=item_id).first()
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

    marking = Marking.query.filter_by(id=marking_id).first()
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
    candidate_mark = processed.get('SCORE')
    outcome_score = processed.get('maxScore')
    is_correct = candidate_mark >= outcome_score
    marking.last_r_value = candidate_r_value
    marking.last_is_correct = is_correct
    db.session.commit()

    run_session.set_saved_answer(marking_id, marking.candidate_r_value)

    next_question_no, next_item_id, next_marking_id = 0, 0, 0
    next_item = get_next_item(run_session, question_no)
    data = {'is_read': False, 'is_flagged': False}
    if next_item is None:
        run_session.set_status(ErrorRunSession.STATUS_TEST_FINISHED)
        data['html'] = render_template("runner/test_finished.html")
    else:
        next_item_id = next_item.get('item_id')
        next_question_no = next_item['question_no']
        next_marking_id = next_item.get('marking_id')
        marking = Marking.query.filter_by(id=next_marking_id).first()
        # marking.is_read = True
        # marking.read_time = datetime.utcnow()
        # db.session.commit()
        data['is_flagged'] = marking.is_flagged
        data['is_read'] = True
        data['next_saved_answer'] = next_item.get('saved_answer')

    data.update({
        'status': run_session.get_status(),
        'session': session_key,
        'question_no': question_no,
        'saved_answer': candidate_response,
        'next_item_id': next_item_id,
        'next_question_no': next_question_no,
        'next_marking_id': next_marking_id,
        'test_duration': run_session.get_value('test_duration'),
        'start_time': run_session.get_value('start_time'),
    })
    return success(data)


@api.route('/errorrun/responses/file/<int:item_id>', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
@validate_session
def error_run_response_process_file(item_id, run_session=None):
    """
    Ignore file and just return success!!
    """
    return success({"result": "success"})


@api.route('/errorrun/finish', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
@validate_session
def error_run_finish_test(run_session):
    session_key = request.json.get('session')
    finish_time = request.json.get('finish_time')
    # assessment_session = AssessmentSession(key=session_key)
    # check session status
    # if assessment_session.get_status() != AssessmentSession.STATUS_TEST_FINISHED:
    #     return bad_request(message='Session status is wrong.')

    if run_session.assessment:
        run_session.set_status(ErrorRunSession.STATUS_TEST_SUBMITTED)
        assessment_enroll_id = run_session.get_value('assessment_enroll_id')
        enrolled = AssessmentEnroll.query.filter_by(id=assessment_enroll_id).first()
        if enrolled:
            enrolled.finish_time = datetime.utcnow()
            enrolled.finish_time_client = datetime.fromtimestamp(finish_time, timezone.utc)
            db.session.add(enrolled)
            # db.session.commit()

    data = {}
    return success(data)

