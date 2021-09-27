import json
import subprocess
from collections import namedtuple
from datetime import datetime, timedelta
import re

from app.api import api
from flask import jsonify, request, current_app

from app.api.errors import bad_request
from app.models import AssessmentEnroll, Assessment, Codebook, Student, Marking, Item, Testset, AssessmentHasTestset, \
    TestletHasItem
from config import Config
from qti.itemservice.itemservice import ItemService
from .assessments import parse_processed_response, parse_correct_response, allowed_file, save_writing_data
from .response import success, fail
from .. import db


@api.route('/omr/marking', methods=['POST', 'GET'])
def omr_marking():
    if request.headers['Authorization'] is None:
        return bad_request(message="The Authorization is not correct.")
    authorization = request.headers['Authorization'].split(' ')
    if len(authorization) != 2:
        return bad_request(message="The Authorization is not correct.")
    else:
        if authorization[0] != 'KEY' or authorization[1] != Config.AUTHORIZATION_KEY:
            return bad_request(message="The Authorization is not correct.")

    if len(request.json) !=3:
        return bad_request(message="The parameter's length is not correct.")

    scores_list = request.json[0]
    examInfo = request.json[1]
    info = request.json[2]

    student = Student.query.filter_by(student_id=info[0].get("student_id")).first()
    if student is None:
        return bad_request(message="Student does not exist.")

    test_center = Codebook.query.filter(Codebook.code_type == 'test_center',
                                        Codebook.additional_info.contains(
                                            {"campus_prefix": student.branch.strip()})).first()
    test_center_id = None
    if test_center:
        test_center_id = test_center.id

    for _info in info:
        scores = list(filter(lambda x: (x["Subject"] == _info["subject"]), scores_list))

        #_info['testset_guid'] = '3b1a9db6-3be2-4e67-b566-2a44f3675539'
        _info['testset_guid'] = '8b5b575c-7219-48ea-98d4-8fead8ef55bf'

        assessment = Assessment.query.with_entities(Assessment.id.label('assessment_id'), Assessment.test_type, Testset.test_duration,
                          Assessment.GUID.label('assessment_guid'), Testset.id.label('testset_id'),
                        Testset.branching).\
                    join(AssessmentHasTestset, Assessment.id == AssessmentHasTestset.assessment_id).\
                        join(Testset, AssessmentHasTestset.testset_id == Testset.id).\
                        filter(Testset.GUID == _info.get('testset_guid'), Testset.active == True).first()
        if assessment is None:
            return bad_request(message="The assessment does not exist.")

        testset_id = assessment.testset_id
        '''
        AssessmentEnroll
        '''
        assessment_enroll_id = None
        assessment_enroll = AssessmentEnroll.query.filter_by(assessment_id=assessment.assessment_id, student_user_id=student.user_id,
                                                    testset_id=testset_id, start_ip=None).first()
        if assessment_enroll is None:
            assessment_guid = assessment.assessment_guid
            student_user_id = student.user_id
            attempt_count = 1
            test_type_name = Codebook.get_code_name(assessment.test_type)
            dt = datetime.utcnow()
            start_time = dt + timedelta(minutes=(-1 * assessment.test_duration))

            enrolled = AssessmentEnroll(assessment_guid=assessment_guid, assessment_id=assessment.assessment_id, testset_id=testset_id,
                                        student_user_id=student_user_id, attempt_count=attempt_count,
                                        start_time=start_time, finish_time=dt, assessment_type=test_type_name, test_center=test_center_id)
            db.session.add(enrolled)
            db.session.commit()
            assessment_enroll_id = enrolled.id
        else:
            assessment_enroll_id = assessment_enroll.id

        '''
        Marking
        '''
        if assessment_enroll is not None:
            Marking.query.filter_by(assessment_enroll_id=assessment_enroll_id).delete()
            db.session.commit()

        item_list = []
        branching = json.dumps(assessment.branching)
        ends = [m.end() for m in re.finditer('"id":', branching)]
        for end in ends:
            comma = branching.find(',', end)
            testlet_id = int(branching[end:comma])

            items = db.session.query(*Item.__table__.columns,TestletHasItem.weight, TestletHasItem.order). \
                select_from(Item). \
                join(TestletHasItem, Item.id == TestletHasItem.item_id). \
                filter(TestletHasItem.testlet_id == testlet_id).order_by(TestletHasItem.order).all()

            for item in items:
                i = {'item_id':item.id,
                     'testlet_id':testlet_id,
                     'order':item.order,
                     'correct_r_value':item.correct_r_value,
                     'weight':item.weight,
                     'outcome_score':item.outcome_score
                     }
                item_list.append(i)

        for item in item_list:
            score = list(filter(lambda x: (x["QuestionNo"] == str(item.get('order'))), scores))

            qti_item_obj = Item.query.filter_by(id=item.get('item_id')).first()
            db.session.expunge(qti_item_obj)

            processed = None
            try:
                item_service = ItemService(qti_item_obj.file_link)
                qti_xml = item_service.get_qti_xml_path()
                processing_php = current_app.config['QTI_RSP_PROCESSING_PHP']
                identifier = None
                answers = marking_to_value(score)
                if len(answers) == 1:
                    identifier = answers[0]
                else:
                    identifier = answers
                response = {"RESPONSE": {
                    "base": {
                        "identifier": identifier
                    }
                }}
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

            if response.get("RESPONSE") and response.get("RESPONSE").get("base") and response.get("RESPONSE").get(
                    "base").get('file'):
                candidate_response = response.get("RESPONSE").get("base")
            else:
                candidate_response = parse_processed_response(processed.get('RESPONSE'))

            candidate_r_value = candidate_response
            candidate_mark = processed.get('SCORE')
            outcome_score = processed.get('maxScore')
            is_correct = candidate_mark >= outcome_score
            correct_r_value = parse_correct_response(processed.get('correctResponses'))

            marking = Marking(testset_id=testset_id,
                              testlet_id=testlet_id,
                              item_id=item.get('item_id'),
                              question_no=item.get('order'),
                              weight=item.get('weight'),
                              candidate_r_value=candidate_r_value,
                              candidate_mark=candidate_mark,
                              outcome_score=outcome_score,
                              is_correct=is_correct,
                              correct_r_value=correct_r_value,
                              is_read=True,
                              is_flagged=False,
                              assessment_enroll_id=assessment_enroll_id)
            db.session.add(marking)
        db.session.commit()

    return success({"result": "success"})


@api.route('/omr/writing', methods=['POST'])
def omr_writing():
    if request.headers['Authorization'] == None or request.headers['Authorization'] != Config.AUTHORIZATION_KEY:
        return bad_request()

    retsult = request.json.get('result')
    marking_id = request.get('marking_id')
    writing_files = request.files.getlist('files')
    writing_text = request.get('writing_text')
    files = request.get('files')
    has_files = False

    for f in writing_files:
        has_files = True
        if allowed_file(f.filename) is False:
            return bad_request(message='File type is not supported.')

    student = Student.query.filter_by(user_id=retsult.get('user_id')).first()
    if student is None:
        return bad_request()

    student_user_id = student.user_id

    writing_files = []
    if has_files is True:
        for f in writing_files:
            writing_files.append(receive_image(f))

    save_writing_data(student_user_id, marking_id, writing_files=writing_files, writing_text=writing_text,
                      has_files=has_files)

    return success({"result": "success"})

    return jsonify(retsult)


def receive_image(f):
    image_filename = f.get('name')
    image_data = f.get('data').decode("base64")
    handler = open(image_filename, "wb+")
    handler.write(image_data)
    handler.close()
    return handler

def marking_to_value(score):
    alfa = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    candidate_r_value = []
    markings = score[0]["marking"]

    for idx, val in enumerate(markings):
        if val:
            candidate_r_value.append(alfa[idx])

    return candidate_r_value
