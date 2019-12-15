import json
import os
import subprocess
from datetime import datetime
import random
import string
from time import time

import pytz
from flask import jsonify, request, current_app, render_template
from flask_login import current_user
from sqlalchemy import desc
from sqlalchemy.orm import load_only
from werkzeug.utils import secure_filename

from app.api import api
from app.api.assessmentsession import AssessmentSession
from app.decorators import permission_required
from app.models import Testset, Permission, Assessment, TestletHasItem, \
    Marking, AssessmentEnroll, MarkingBySimulater, Student, MarkingForWriting
from qti.itemservice.itemservice import ItemService
from .response import success, bad_request
from .. import db
from ..models import Item, Codebook


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
    if assessment is not None:
        rows = [(row.id, row.name, Codebook.get_code_name(row.grade), Codebook.get_code_name(row.subject)) for
                row in assessment.testsets]
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
        rows = [(0, '', 0, 0, 0, percentile)]
        # Todo: Delete these temporary simulating data. It is just for 1 user tester.
        #       and need to remove delete lator with valid assessment_enroll_id
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
    :return:
    """
    assessment_guid = request.json.get('assessment_guid')
    testset_id = request.json.get('testset_id')
    start_time = request.json.get('start_time')
    student_ip = request.json.get('student_ip')

    # 1. check if there is an assessment with the guid and get the latest one.
    assessment = Assessment.query.filter_by(GUID=assessment_guid).order_by(Assessment.version.desc()).first()
    if assessment is None:
        return bad_request()

    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return bad_request()
    student_id = student.id

    # 2. check if the student went through the testset.
    # ToDo: What should we do if he already did?
    # If we only handle single test, it's time to check count and proceed or stop processing.
    did_enroll_count = AssessmentEnroll.query.filter_by(assessment_guid=assessment_guid, student_id=student_id).count()

    # 3. Find out the test attempt count.
    last_attempt = AssessmentEnroll.query.filter_by(assessment_guid=assessment_guid, student_id=student_id) \
        .order_by(desc(AssessmentEnroll.attempt_count)).first()
    if last_attempt is None:
        attempt_count = 1
    else:
        # attempt_count is added to the model. Old rows have None
        attempt_count = 1 if last_attempt.attempt_count is None else last_attempt.attempt_count + 1

    # 4. Create a new enroll
    enrolled = AssessmentEnroll(assessment_guid=assessment_guid, assessment_id=assessment.id, testset_id=testset_id,
                                student_id=student_id, attempt_count=attempt_count)
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
    enrolled.start_time_client = datetime.fromtimestamp(start_time)
    db.session.add(enrolled)
    db.session.commit()
    assessment_enroll_id = enrolled.id

    testset = Testset.query.filter_by(id=testset_id).first()
    if testset is None:
        return bad_request('testset_id', message="Cannot find testset_id {}".format(testset_id))
    test_duration = testset.test_duration or 70
    assessment_session = AssessmentSession(current_user.id, assessment_enroll_id,
                                           testset_id, test_duration, attempt_count)
    assessment_session.set_value('start_time', int(time()))

    # Start a new assessment session.
    assessment_session.set_status(AssessmentSession.STATUS_IN_TESTING)
    data = {
        'session': assessment_session.key,
    }
    return success(data)


@api.route('/start', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
def test_start():
    """ Start the test with session_id.
    :return:
    """
    session_id = request.json.get('session_id')
    question_no = request.json.get('question_no')
    assessment_session = AssessmentSession(key=session_id)
    if assessment_session.assessment is None:
        return bad_request(message="session is expired or not exists.")

    status = assessment_session.get_value('status')
    if status == AssessmentSession.STATUS_TEST_SUBMITTED:
        return bad_request(message="Test session finished already!")

    if question_no is None:
        question_no = 1
    else:
        question_no = int(question_no)

    assessment_enroll_id = assessment_session.get_value('assessment_enroll_id')
    testset_id = assessment_session.get_value('testset_id')
    attempt_count = assessment_session.get_value('attempt_count')
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
    if len(test_items) is 0 and question_no == 1:
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
        'new_questions': new_questions,
    })
    return success(data)


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
def response_process(item_id):
    # item_id = request.json.get('item_id')
    question_no = request.json.get('question_no')
    session_key = request.json.get('session')
    marking_id = request.json.get('marking_id')
    response = request.json.get('response')

    assessment_session = AssessmentSession(key=session_key)

    # check session status
    if assessment_session.get_status() == AssessmentSession.STATUS_READY:
        return bad_request(message='Session status is wrong.')
    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return bad_request()
    student_id = student.id

    # response_json = request.json
    qti_item_obj = Item.query.filter_by(id=item_id).first()
    if qti_item_obj.interaction_type == 'extendedTextInteraction':
        item_subject = Codebook.get_code_name(qti_item_obj.subject)
        if item_subject.lower() == 'writing':
            writing_text = request.json.get('writing_text')
            save_writing_data(student_id, marking_id, writing_text=writing_text)

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
    if response.get("RESPONSE") and response.get("RESPONSE").get("base") and response.get("RESPONSE").get("base").get('file'):
        candidate_response = response.get("RESPONSE").get("base")
    else:
        candidate_response = parse_processed_response(processed.get('RESPONSE'))
    marking.candidate_r_value = candidate_response
    marking.candidate_mark = processed.get('SCORE')
    marking.outcome_score = processed.get('maxScore')
    marking.is_correct = marking.candidate_mark >= marking.outcome_score
    marking.correct_r_value = parse_correct_response(processed.get('correctResponses'))

    db.session.commit()

    next_question_no, next_item_id, next_marking_id = 0, 0, 0
    next_item = get_next_item(assessment_session, question_no)
    data = {'is_read': False, 'is_flagged': False}
    if next_item is None:
        # There is 2 cases where next_item is None
        #   1. It consumed all of the current testlet items. ==> Ask to proceed to a next testlet.
        #   2. It consumed all of the current testset items.  ==> Ask to submit the testset.
        if can_load_next_testlet(assessment_session, marking.testlet_id):
            assessment_enroll_id = assessment_session.get_value('assessment_enroll_id')
            testset_id = assessment_session.get_value('testset_id')
            testlet_id = marking.testlet_id
            markings = Marking.query.filter_by(assessment_enroll_id=assessment_enroll_id,
                                               testset_id=testset_id, testlet_id=testlet_id) \
                .order_by(Marking.question_no).all()
            start = markings[0].question_no
            end = markings[-1].question_no
            data['html'] = render_template("runner/stage_finished.html", start=start, end=end)
            data['testlet_id'] = testlet_id
            data['question_no'] = question_no
            assessment_session.set_status(AssessmentSession.STATUS_STAGE_FINISHED)
        else:
            assessment_session.set_status(AssessmentSession.STATUS_TEST_FINISHED)
            data['html'] = render_template("runner/test_finished.html")
    else:
        next_item_id = next_item.get('item_id')
        next_question_no = question_no + 1
        next_marking_id = next_item.get('marking_id')
        marking = Marking.query.filter_by(id=next_marking_id).first()
        marking.is_read = True
        db.session.commit()
        data['is_flagged'] = marking.is_flagged
        data['is_read'] = marking.is_read
        data['next_saved_answer'] = marking.candidate_r_value if marking.candidate_r_value is not None else ""

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
def response_process_file(item_id):
    session_key = request.form.get('session')
    marking_id = request.form.get('marking_id')
    writing_file = request.files.get('file')

    if allowed_file(writing_file.filename) is False:
        return bad_request(message='File type is not supported.')

    assessment_session = AssessmentSession(key=session_key)
    # check session status
    if assessment_session.get_status() == AssessmentSession.STATUS_READY:
        return bad_request(message='Session status is wrong.')

    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return bad_request()
    student_id = student.id
    save_writing_data(student_id, marking_id, writing_file=writing_file)

    return success({"result": "success"})


def save_writing_data(student_id, marking_id, writing_file=None, writing_text=None):
    file_name = writing_file.filename if writing_file is not None else 'writing.txt'
    # 1. Save the file to the path at config['WRITING_UPLOAD_FOLDER']
    random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=24))
    new_file_name = str(student_id) + '_' + random_name + '_' + secure_filename(file_name)
    item_file = os.path.join(current_app.config['WRITING_UPLOAD_FOLDER'], new_file_name)
    if writing_file is not None:
        writing_file.save(item_file)
    else:
        with open(item_file, "w") as f:
            f.write(writing_text)

    # 2. Create a record in MarkingForWriting
    marking_writing = MarkingForWriting(candidate_file_link=new_file_name,
                                        marking_id=marking_id)
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


def parse_correct_response(correct_response):
    correct_response = correct_response.strip()
    if correct_response != '' and correct_response[0] == '[':
        correct_response = correct_response.replace("'", '"')
        correct_response = json.loads(correct_response)
    return correct_response


def parse_processed_response(candidate_response):
    candidate_response = candidate_response.strip()
    if candidate_response != '' and candidate_response[0] == '[':
        responses = candidate_response[1:-1].replace("'", "").split(';')
        candidate_response = []
        for r in responses:
            r = r.strip()
            candidate_response.append(r)
    return candidate_response


@api.route('/rendered/<int:item_id>', methods=['GET'])
@permission_required(Permission.ITEM_EXEC)
def rendered(item_id):
    session_key = request.args.get('session')
    assessment_session = AssessmentSession(key=session_key)
    assessment_session.set_status(AssessmentSession.STATUS_IN_TESTING)
    response = {}
    rendered_item = ''
    qti_item_obj = Item.query.filter_by(id=item_id).first()
    if os.environ.get("DEBUG_RENDERING", 'false') == 'false':
        try:
            item_service = ItemService(qti_item_obj.file_link)
            qti_item = item_service.get_item()
            rendered_item = qti_item.to_html()
            response['type'] = qti_item.get_interaction_type()
            response['cardinality'] = qti_item.get_cardinality()
            response['object_variables'] = qti_item.get_interaction_object_variables()
            response['interactions'] = qti_item.get_interaction_info()
        except Exception as e:
            print(e)
    else:
        item_service = ItemService(qti_item_obj.file_link)
        qti_item = item_service.get_item()
        rendered_item = qti_item.to_html()
        response['type'] = qti_item.get_interaction_type()
        response['cardinality'] = qti_item.get_cardinality()
        response['object_variables'] = qti_item.get_interaction_object_variables()
        response['interactions'] = qti_item.get_interaction_info()

    # debug mode 일 때만 정답을 표시할 수 있도록 하기위해
    debug_rendering = os.environ.get('DEBUG_RENDERING') == 'true'
    rendered_template = render_template("runner/test_item.html", item=qti_item_obj, debug_rendering=debug_rendering)
    if rendered_item:
        rendered_template = rendered_template.replace('rendered_html', rendered_item)
    response['html'] = rendered_template
    return success(response)


@api.route('/next_stage', methods=['POST'])
@permission_required(Permission.ITEM_EXEC)
def next_stage():
    session_key = request.json.get('session')
    testlet_id = request.json.get('testlet_id')
    question_no = request.json.get('question_no')

    assessment_session = AssessmentSession(key=session_key)

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
def finish_test():
    session_key = request.json.get('session')
    assessment_session = AssessmentSession(key=session_key)
    # check session status
    if assessment_session.get_status() != AssessmentSession.STATUS_TEST_FINISHED:
        return bad_request(message='Session status is wrong.')

    assessment_session.set_status(AssessmentSession.STATUS_TEST_SUBMITTED)

    data = {'redirect_url': '/tests/testsets'}
    return success(data)


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
    if testlet_id is not 0:
        markings = Marking.query.filter_by(assessment_enroll_id=assessment_enroll_id,
                                           testset_id=testset_id, testlet_id=testlet_id) \
            .order_by(Marking.question_no).all()
        for marking in markings:
            sum_score = sum_score + marking.getScore()
            last_question_no = marking.question_no
        outcome_total = Marking.getTotalOutcomeScore(assessment_enroll_id, testset_id, testlet_id)
        percentile = sum_score / outcome_total * 100  # Student's marked percentile

    next_branch_json = get_next_testlet(stage_data, testset_id, testlet_id, percentile)
    new_questions = []
    if next_branch_json is not None:
        testlet_id = next_branch_json.get("id")
        stage = len(stage_data) + 1
        stage_data.append({'stage': stage, 'testlet_id': int(testlet_id)})
        assessment_session.set_value('stage_data', stage_data)
        items = TestletHasItem.query.filter_by(testlet_id=testlet_id).order_by(TestletHasItem.order.asc()).all()
        for item in items:
            last_question_no += 1
            marking = Marking(testset_id=testset_id,
                              testlet_id=testlet_id,
                              item_id=item.item_id, question_no=last_question_no,
                              weight=item.weight,
                              assessment_enroll_id=assessment_enroll_id)
            db.session.add(marking)
            db.session.commit()
            item_info = {'question_no': last_question_no, 'item_id': marking.item_id,
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

    if len(stage_data) == 0:
        next_branch = first_branch
    else:
        c_stage_no = stage_data[-1].get("stage")  # candidate's
        c_testlet_id = stage_data[-1].get("testlet_id")  # candidate's
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
                        # Todo: check conditions if any other case
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
