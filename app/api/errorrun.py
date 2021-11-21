import json
import math
import os
import re
import subprocess
from datetime import datetime
from time import time
from functools import wraps

from flask import request, current_app, render_template
from flask_login import current_user
from sqlalchemy import desc, or_, func

from app.api import api
from app.decorators import permission_required
from app.api.jwplayer import get_signed_player, jwt_signed_url
from app.models import Permission, AssessmentEnroll, Marking, Item, Codebook, Student, AssessmentRetry, RetryMarking, \
    Assessment, Testset, TestletHasItem
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
        retry_is_single = ErrorRunSession.retry_is_single_from_session_key(session_key)
        if retry_is_single:
            run_session = get_single_run_session(session_key)
        else:
            run_session = get_run_session(session_key)
        if run_session.error_code is not None:
            return bad_request(error_code=run_session.error_code,
                               message=run_session.error_message)
        kwargs['run_session'] = run_session
        return func(*args, **kwargs)
    return decorated_view


def get_single_run_session(session_key):
    run_session = ErrorRunSession(key=session_key)
    if run_session.assessment is None:
        run_session.set_error(TEST_SESSION_ERROR, "Retry session is finished!")
    return run_session


def get_run_session(session_key):
    run_session = ErrorRunSession(key=session_key)
    if run_session.assessment is None:
        retry_id = ErrorRunSession.retry_id_from_session_key(session_key)
        # 동일한 assessment id, testset id 조합으로 enroll 은 유일해야한다.
        # 혹시 몰라서 start_time 을 기준 최신을 확인.
        retry = AssessmentRetry.query.filter(AssessmentRetry.id == retry_id) \
            .order_by(desc(AssessmentRetry.start_time)).first()
        # session 이 없는 이유를 알아본다.
        if retry.is_finished:
            run_session.set_error(TEST_SESSION_ERROR, "Retry session is finished!")
        elif retry.session_key != session_key:
            run_session.set_error(
                TEST_SESSION_ERROR,
                "This session is invalid! A new session has been started from another browser."
            )
        else:
            # 이 경우라면 DB 로부터 session 을 복원한다.
            assessment_enrol = AssessmentEnroll.query.filter_by(id=retry.assessment_enroll_id).first();
            run_session.reset(current_user.id, retry_id, assessment_enrol.testset_id,
                              assessment_enrol.test_duration, retry.attempt_count, retry.start_time)
            # retry has no stage data:  run_session.set_value('stage_data', enroll.stage_data)
            markings = RetryMarking.query.filter_by(assessment_retry_id=retry_id,
                                                    testset_id=assessment_enrol.testset_id) \
                .order_by(RetryMarking.question_no).all()
            # build test_items
            test_items = []
            for m in markings:
                info = {'question_no': m.question_no, 'item_id': m.item_id,
                        'marking_id': m.id, 'is_flagged': m.is_flagged,
                        'is_read': m.is_read,
                        'saved_answer': m.candidate_r_value if m.candidate_r_value is not None else ''
                        }
                test_items.append(info)
            run_session.set_value('test_items', test_items)
    return run_session


def new_error_run_session(user_id, enroll_id, testset_id, test_duration, attempt_count, is_single=False):
    return ErrorRunSession(user_id, enroll_id, testset_id, test_duration, attempt_count, is_single)


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
    session_key = request.json.get('session_key')

    enrolled = AssessmentEnroll.query.filter_by(id=assessment_enroll_id).first()
    user_id = current_user.id

    if session_key is None:
        assessment_retry = AssessmentRetry.query.filter_by(assessment_enroll_id=assessment_enroll_id)\
            .order_by(desc(AssessmentRetry.start_time)).first()
        if assessment_retry is None:
            retry_count = 1
        else:
            # 이미 시작어 진행중인 세션이 있으면 error 를 return 한다.
            if assessment_retry.finish_time is None:
                return bad_request(error_code=TEST_SESSION_ERROR,
                                   message="A new session has been started from another browser.")
            retry_count = assessment_retry.attempt_count + 1
        assessment_retry = AssessmentRetry.from_enroll(enrolled)
        assessment_retry.attempt_count = retry_count
        if 'HTTP_X_FORWARDED_FOR' in request.headers.environ:
            assessment_retry.start_ip = request.headers.environ['HTTP_X_FORWARDED_FOR']
        else:
            assessment_retry.start_ip = request.headers.environ['REMOTE_ADDR']
        assessment_retry.start_time = datetime.utcnow()
        assessment_retry.created_time = datetime.utcnow()
        db.session.add(assessment_retry)
        db.session.commit()
        assessment_retry_id = assessment_retry.id
        # 새로운 세션을 만든다.
        error_run_session = new_error_run_session(user_id, assessment_retry_id, enrolled.testset_id,
                                                  enrolled.test_duration, 1)
        # Find markings that are marked incorrect in the last try.
        markings = Marking.query.filter(Marking.assessment_enroll_id == assessment_enroll_id,
                                        or_(Marking.last_is_correct == False, Marking.last_is_correct == None)) \
            .order_by(Marking.question_no).all()
        # create RetryMarking
        retry_markings = []
        for m in markings:
            retry_marking = RetryMarking.from_marking(assessment_retry_id, m)
            db.session.add(retry_marking)
            retry_markings.append(retry_marking)
        db.session.commit()
        question_no = -1
        # build test_items
        test_items = []
        for m in retry_markings:
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
        next_item = get_next_item(error_run_session, question_no - 1)
    else:
        # session 을 찾는다.
        error_run_session = get_run_session(session_key)
        if error_run_session.error_code is not None:
            return bad_request(error_code=error_run_session.error_code,
                               message=error_run_session.error_message)
        new_session_key = error_run_session.change_session_key()
        assessment_retry_id = error_run_session.get_value('assessment_retry_id')
        assessment_retry = AssessmentRetry.query.filter_by(id=assessment_retry_id).first()
        assessment_retry.session_key = new_session_key
        db.session.commit()
        test_items = error_run_session.get_value('test_items')
        retry_marking = RetryMarking.query.filter_by(assessment_retry_id=assessment_retry_id, is_read=True)\
            .order_by(desc(RetryMarking.read_time)).first()
        question_no = 1
        if retry_marking is not None:
            question_no = retry_marking.question_no
        next_item = get_next_item(error_run_session, question_no - 1)

    assessment_retry.session_key = error_run_session.key
    if len(test_items) == 0:
        assessment_retry.finish_time = datetime.utcnow()
    db.session.commit()

    next_question_no = 0
    data = {'is_read': False, 'is_flagged': False}
    if next_item is not None:
        # next_item_id = next_item.get('item_id')
        next_question_no = next_item['question_no']
        next_marking_id = next_item.get('marking_id')
        marking = RetryMarking.query.filter_by(id=next_marking_id).first()
        marking.is_read = True
        marking.read_time = datetime.utcnow()
        db.session.commit()
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


@api.route('/errorrun/single', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
def start_single_error_run():
    assessment_enroll_id = request.json.get('assessment_enroll_id')
    question_no = request.json.get('question_no')

    enrolled = AssessmentEnroll.query.filter_by(id=assessment_enroll_id).first()
    user_id = current_user.id

    assessment_retry = AssessmentRetry.query.filter_by(assessment_enroll_id=assessment_enroll_id,
                                                       is_single_retry=True)\
        .order_by(desc(AssessmentRetry.start_time)).first()
    # 없으면 새로 만들고 있으면 재활용한다.
    if assessment_retry is None:
        assessment_retry = AssessmentRetry.from_enroll(enrolled)
        assessment_retry.is_single_retry = True
    if 'HTTP_X_FORWARDED_FOR' in request.headers.environ:
        assessment_retry.start_ip = request.headers.environ['HTTP_X_FORWARDED_FOR']
    else:
        assessment_retry.start_ip = request.headers.environ['REMOTE_ADDR']
    assessment_retry.start_time = datetime.utcnow()
    db.session.add(assessment_retry)
    db.session.commit()
    assessment_retry_id = assessment_retry.id
    # 새로운 세션을 만든다.
    error_run_session = new_error_run_session(user_id, assessment_retry_id, enrolled.testset_id,
                                              enrolled.test_duration, 1, True)
    # Find markings that are marked incorrect in the last try.
    markings = Marking.query.filter(Marking.assessment_enroll_id == assessment_enroll_id,
                                    Marking.question_no == question_no,
                                    or_(Marking.last_is_correct == False, Marking.last_is_correct == None)) \
        .order_by(Marking.question_no).all()
    # create RetryMarking
    retry_markings = []
    for m in markings:
        retry_marking = RetryMarking.from_marking(assessment_retry_id, m)
        db.session.add(retry_marking)
        retry_markings.append(retry_marking)
    db.session.commit()
    question_no = -1
    # build test_items
    test_items = []
    for m in retry_markings:
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
    next_item = get_next_item(error_run_session, question_no - 1)

    assessment_retry.session_key = error_run_session.key
    if len(test_items) == 0:
        assessment_retry.finish_time = datetime.utcnow()
    db.session.commit()

    next_question_no = 0
    data = {'is_read': False, 'is_flagged': False}
    if next_item is not None:
        # next_item_id = next_item.get('item_id')
        next_question_no = next_item['question_no']
        next_marking_id = next_item.get('marking_id')
        marking = RetryMarking.query.filter_by(id=next_marking_id).first()
        marking.is_read = True
        marking.read_time = datetime.utcnow()
        db.session.commit()
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
    retry_id = ErrorRunSession.retry_id_from_session_key(session_key)
    marking = RetryMarking.query.filter_by(assessment_retry_id=retry_id, item_id=item_id).first()
    marking.read_time = datetime.utcnow()
    db.session.commit()
    response['html'] = rendered_template
    media_id_match = re.search(r"http://jwplayer-id/([a-zA-Z0-9]+)", rendered_template)
    if media_id_match:
        test_duration_min = run_session.get_value('test_duration')
        start_time_sec = run_session.get_value('start_time')
        remained_sec = test_duration_min * 60 - int(datetime.now().timestamp() - start_time_sec)
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

    retry = RetryMarking.query.filter_by(id=marking_id).first()
    # marking = Marking.query.filter_by(id=retry.marking_id).first()
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

    retry.candidate_r_value = candidate_r_value
    retry.candidate_mark = processed.get('SCORE')
    retry.outcome_score = processed.get('maxScore')
    retry.is_correct = retry.candidate_mark >= retry.outcome_score
    retry.correct_r_value = parse_correct_response(processed.get('correctResponses'))

    # candidate_mark = processed.get('SCORE')
    # outcome_score = processed.get('maxScore')
    # is_correct = candidate_mark >= outcome_score
    # marking.last_r_value = candidate_r_value
    # marking.last_is_correct = is_correct

    db.session.commit()

    run_session.set_saved_answer(marking_id, retry.candidate_r_value)

    next_question_no, next_item_id, next_marking_id = 0, 0, 0
    next_item = get_next_item(run_session, question_no)
    data = {'is_read': False, 'is_flagged': False}
    if next_item is None:
        run_session.set_status(ErrorRunSession.STATUS_TEST_FINISHED)
        data['html'] = render_template("errornote/test_finished.html")
    else:
        next_item_id = next_item.get('item_id')
        next_question_no = next_item['question_no']
        next_marking_id = next_item.get('marking_id')
        marking = RetryMarking.query.filter_by(id=next_marking_id).first()
        marking.is_read = True
        marking.read_time = datetime.utcnow()
        db.session.commit()
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
    # finish_time = request.json.get('finish_time')
    retry_result = {}

    if run_session.assessment:
        run_session.set_status(ErrorRunSession.STATUS_TEST_SUBMITTED)
        assessment_retry_id = run_session.get_value('assessment_retry_id')
        retry = AssessmentRetry.query.filter_by(id=assessment_retry_id).first()
        assessment_enroll_id = retry.assessment_enroll_id
        retry.finish_time = datetime.utcnow()
        # retry.finish_time_client = datetime.fromtimestamp(finish_time, timezone.utc)
        db.session.add(retry)
        db.session.commit()
        if ErrorRunSession.retry_is_single_from_session_key(run_session.key):
            test_items = run_session.get_value('test_items')
            marking_id = test_items[0]['marking_id']
            r_markings = RetryMarking.query.filter_by(id=marking_id).all()
        else:
            r_markings = RetryMarking.query.filter_by(assessment_retry_id=assessment_retry_id).all()
        retry_markings = {}
        questions = []
        for rm in r_markings:
            retry_markings[rm.question_no] = rm
            retry_result[rm.question_no] = rm.is_correct
            questions.append(rm.question_no)
        markings = Marking.query.filter(Marking.assessment_enroll_id == retry.assessment_enroll_id,
                                        Marking.question_no.in_(questions)).all()
        for m in markings:
            rm = retry_markings[m.question_no]
            m.last_is_correct = rm.is_correct
            m.last_r_value = rm.candidate_r_value
        db.session.commit()

        # 틀린 문제가 없다면 finish 가 안된 retry 를 모두 끝낸다.
        error_count = Marking.query.filter(Marking.assessment_enroll_id == assessment_enroll_id,
                                           or_(Marking.last_is_correct == False, Marking.last_is_correct == None)) \
            .count()
        if error_count == 0:
            retries = AssessmentRetry.query.filter_by(assessment_enroll_id=assessment_enroll_id, finish_time=None).all()
            for r in retries:
                r.finish_time = datetime.utcnow()
            db.session.commit()

    return success(retry_result)


@api.route('/errorrun/writing/text', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
def error_run_writing_text():
    marking_id = request.json.get('marking_id')
    writing_text = json.dumps(request.json.get('writing_text'))

    sql_stmt = 'UPDATE marking a set candidate_r_value =:candidate_r_value WHERE id =:marking_id and exists(select 1 from assessment_enroll aa where aa.id=a.assessment_enroll_id and aa.finish_time is null) and exists(select 1 from item aa where aa.id = a.item_id and subject=107)'
    db.session.execute(sql_stmt,  {'marking_id': marking_id, 'candidate_r_value': writing_text})
    db.session.commit()

    return success()


@api.route('/errorrun/instruction', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
def error_run_instruction():
    data = {}
    testset_id = request.form.get('testset_id', 0, type=int)
    assessment_guid = request.form.get('assessment_guid', '', type=str)

    assessment = Assessment.query.filter_by(GUID=assessment_guid).first()
    if assessment:
        data['assessment_name'] = assessment.name
        codebook = Codebook.query.filter_by(id=assessment.test_type).first()
        if codebook:
            if codebook.additional_info:
                for x, y in codebook.additional_info.items():
                    if x == 'instruction':
                        data['instruction'] = y

    question_count = 0
    testset = Testset.query.filter_by(id=testset_id).first()
    subjects = []
    if testset:
        data['duration'] = testset.test_duration
        branching = json.dumps(testset.branching)
        ends = [m.end() for m in re.finditer('"id":', branching)]
        for end in ends:
            comma = branching.find(',', end)
            testlet_id = int(branching[end:comma])

            items = db.session.query(*Item.__table__.columns). \
                select_from(Item). \
                join(TestletHasItem, Item.id == TestletHasItem.item_id). \
                filter(TestletHasItem.testlet_id == testlet_id).order_by(TestletHasItem.order).all()

            #subjects.extend(list({i.subject for i in items}))
            for i in items:
                subjects.append(i.subject)
            question_count = question_count + len(items)
    data['subjects'] = []
    if len(subjects) > 0:
        subjects = dict((x,subjects.count(x)) for x in set(subjects))
        for key, value in subjects.items():
            data['subjects'].append({Codebook.get_code_name(key) : value})

    data['question_count'] = question_count

    #data['instruction'] = 'oc'

    return success(data)
