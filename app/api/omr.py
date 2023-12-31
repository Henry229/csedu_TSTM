import json
import random
import string
import subprocess
from collections import namedtuple
from datetime import datetime, timedelta
import re

from sqlalchemy import desc

from app.api import api
from flask import jsonify, request, current_app

from app.api.errors import bad_request
from app.models import AssessmentEnroll, Assessment, Codebook, Student, Marking, Item, Testset, AssessmentHasTestset, \
    TestletHasItem, Role, User, MarkingForWriting, MarkerBranch
from common.logger import log
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
        if info[0].get("stud_first_name") is None or info[0].get("stud_last_name") is None or info[0].get("branch") is None:
            return bad_request(message="Student sent from OMR System is wrong.")
        if (info[0].get("stud_first_name").strip() == '' and info[0].get("stud_last_name").strip() == '') or info[0].get("branch").strip() == '':
            return bad_request(message="Student sent from OMR System is wrong.")

        role = Role.query.filter_by(name='Test_taker').first()
        student_user = User(
            username="%s %s (%s)" % (
                info[0].get("stud_first_name").strip(), info[0].get("stud_last_name").strip(), info[0].get("student_id")),
            role=role,
            confirmed=True,
            active=True,
            email=info[0].get("student_id") + '@cseducation.com.au')
        temp_password = ''.join(
            random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))
        student_user.password = temp_password
        db.session.add(student_user)
        db.session.commit()  # Commit to get the student_user.id

        student = Student(student_id=info[0].get("student_id"),
                          user_id=student_user.id,
                          branch=info[0].get("branch").strip())

        info_test_center = Codebook.query.filter(Codebook.code_type == 'test_center',
                                            Codebook.additional_info.contains(
                                                {"campus_prefix": info[0].get("branch").strip()})).first()
        if info_test_center:
            if info_test_center.additional_info.get("state") is not None:
                student.state = info_test_center.additional_info["state"]
            else:
                if info_test_center.additional_info.get("branch_state") is not None:
                    student.state = info_test_center.additional_info["branch_state"]

        db.session.add(student)
        db.session.commit()

    test_center = Codebook.query.filter(Codebook.code_type == 'test_center',
                                        Codebook.additional_info.contains(
                                            {"campus_prefix": student.branch.strip()})).first()
    test_center_id = None
    if test_center:
        test_center_id = test_center.id

    for _info in info:
        scores = list(filter(lambda x: (x["Subject"] == _info["subject"]), scores_list))

        #_info['testset_guid'] = '3b1a9db6-3be2-4e67-b566-2a44f3675539'
        #_info['testset_guid'] = '8b5b575c-7219-48ea-98d4-8fead8ef55bf'

        assessment = Assessment.query.with_entities(Assessment.id.label('assessment_id'), Assessment.test_type, Testset.test_duration,
                          Assessment.GUID.label('assessment_guid'), Testset.id.label('testset_id'),
                        Testset.branching).\
                    join(AssessmentHasTestset, Assessment.id == AssessmentHasTestset.assessment_id).\
                        join(Testset, AssessmentHasTestset.testset_id == Testset.id).\
                        filter(Testset.GUID == _info.get('testset_guid'), Testset.active == True).order_by(desc(Assessment.id)).first()
        if assessment is None:
            return bad_request(message="The assessment does not exist.")

        testset_id = assessment.testset_id
        '''
        AssessmentEnroll
        '''
        assessment_enroll_id = None
        assessment_enroll = AssessmentEnroll.query.filter_by(assessment_id=assessment.assessment_id, student_user_id=student.user_id,
                                                    testset_id=testset_id).first()
        if assessment_enroll is None:
            assessment_guid = assessment.assessment_guid
            student_user_id = student.user_id
            attempt_count = 1
            test_type_name = None
            is_subject_of_test_type = False
            row = Codebook.query.filter_by(id=assessment.test_type).first()
            if row:
                test_type_name = row.code_name
                if row.additional_info:
                    for x, y in row.additional_info.items():
                        if x == 'omr_subject':
                            if bool(y):
                                is_subject_of_test_type = True

            if not is_subject_of_test_type:
                return bad_request(message="The test type is not the subject of OMR System.")

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

        total_candidate_mark = 0
        total_outcome_score = 0
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

                answers = answer_to_value(score)
                if len(answers) == 0:
                    identifier = ''
                elif len(answers) == 1:
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

            total_candidate_mark += candidate_mark
            total_outcome_score += outcome_score

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

        db.session.query(AssessmentEnroll).filter(AssessmentEnroll.id == assessment_enroll_id).update(
            {"score": total_candidate_mark, "total_score": total_outcome_score})
        db.session.commit()

    return success({"result": "success"})


@api.route('/omr/writing', methods=['POST'])
def omr_writing():
    if request.headers['Authorization'] is None:
        return bad_request(message="The Authorization is not correct.")
    authorization = request.headers['Authorization'].split(' ')
    if len(authorization) != 2:
        return bad_request(message="The Authorization is not correct.")
    else:
        if authorization[0] != 'KEY' or authorization[1] != Config.AUTHORIZATION_KEY:
            return bad_request(message="The Authorization is not correct.")

    if len(request.json) !=2:
        return bad_request(message="The parameter's length is not correct.")

    scores_list = request.json[0]
    info = request.json[1]

    if len(scores_list) != 7:
        return bad_request(message="The scores size is not correct.")

    student = Student.query.filter_by(student_id=info[0].get("student_id")).first()
    if student is None:
        if info[0].get("stud_first_name") is None or info[0].get("stud_last_name") is None or info[0].get("branch") is None:
            return bad_request(message="Student sent from OMR System is wrong.")
        if (info[0].get("stud_first_name").strip() == '' and info[0].get("stud_last_name").strip() == '') or info[0].get("branch").strip() == '':
            return bad_request(message="Student sent from OMR System is wrong.")

        role = Role.query.filter_by(name='Test_taker').first()
        student_user = User(
            username="%s %s (%s)" % (
                info[0].get("stud_first_name").strip(), info[0].get("stud_last_name").strip(), info[0].get("student_id")),
            role=role,
            confirmed=True,
            active=True,
            email=info[0].get("student_id") + '@cseducation.com.au')
        temp_password = ''.join(
            random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))
        student_user.password = temp_password
        db.session.add(student_user)
        db.session.commit()  # Commit to get the student_user.id

        student = Student(student_id=info[0].get("student_id"),
                          user_id=student_user.id,
                          branch=info[0].get("branch").strip())

        info_test_center = Codebook.query.filter(Codebook.code_type == 'test_center',
                                            Codebook.additional_info.contains(
                                                {"campus_prefix": info[0].get("branch").strip()})).first()
        if info_test_center:
            if info_test_center.additional_info.get("state") is not None:
                student.state = info_test_center.additional_info["state"]
            else:
                if info_test_center.additional_info.get("branch_state") is not None:
                    student.state = info_test_center.additional_info["branch_state"]

        db.session.add(student)
        db.session.commit()

    test_center = Codebook.query.filter(Codebook.code_type == 'test_center',
                                        Codebook.additional_info.contains(
                                            {"campus_prefix": student.branch.strip()})).first()
    test_center_id = None
    if test_center:
        test_center_id = test_center.id

    marker_branch = MarkerBranch.query.filter_by(branch_id=test_center_id).filter(MarkerBranch.delete.isnot(True)).first()

    if not marker_branch:
        return bad_request(message="The branch is not correct.")

    for _info in info:
        #_info['testset_guid'] = '3b1a9db6-3be2-4e67-b566-2a44f3675539'
        assessment = Assessment.query.with_entities(Assessment.id.label('assessment_id'), Assessment.test_type, Testset.test_duration,
                          Assessment.GUID.label('assessment_guid'), Testset.id.label('testset_id'),
                        Testset.branching).\
                    join(AssessmentHasTestset, Assessment.id == AssessmentHasTestset.assessment_id).\
                        join(Testset, AssessmentHasTestset.testset_id == Testset.id).\
                        filter(Testset.GUID == _info.get('testset_guid'), Testset.active == True).order_by(desc(Assessment.id)).first()
        if assessment is None:
            return bad_request(message="The assessment does not exist.")

        testset_id = assessment.testset_id
        '''
        AssessmentEnroll
        '''
        assessment_enroll_id = None
        assessment_enroll = AssessmentEnroll.query.filter_by(assessment_id=assessment.assessment_id, student_user_id=student.user_id,
                                                    testset_id=testset_id).first()
        if assessment_enroll is None:
            assessment_guid = assessment.assessment_guid
            student_user_id = student.user_id
            attempt_count = 1
            test_type_name = None
            is_subject_of_test_type = False
            row = Codebook.query.filter_by(id=assessment.test_type).first()
            if row:
                test_type_name = row.code_name
                if row.additional_info:
                    for x, y in row.additional_info.items():
                        if x == 'omr_subject':
                            if bool(y):
                                is_subject_of_test_type = True


            if not is_subject_of_test_type:
                return bad_request(message="The test type is not the subject of OMR System.")


            stage_data= []
            branching = json.dumps(assessment.branching)
            ends = [m.end() for m in re.finditer('"id":', branching)]

            for end in ends:
                comma = branching.find(',', end)
                stage = len(stage_data) + 1
                stage_data.append({'stage': stage, 'testlet_id': int(branching[end:comma]), 'percentile': 0})

            dt = datetime.utcnow()
            start_time = dt + timedelta(minutes=(-1 * assessment.test_duration))

            enrolled = AssessmentEnroll(assessment_guid=assessment_guid, assessment_id=assessment.assessment_id, testset_id=testset_id,
                                        student_user_id=student_user_id, attempt_count=attempt_count, stage_data=stage_data,
                                        start_time=start_time, finish_time=dt, assessment_type=test_type_name, test_center=test_center_id,
                                        test_duration=assessment.test_duration,
                                        score=0, total_score=1)
            db.session.add(enrolled)
            db.session.commit()
            assessment_enroll_id = enrolled.id
        else:
            assessment_enroll_id = assessment_enroll.id

        '''
        Marking
        '''
        if assessment_enroll is not None:
            old_marking = Marking.query.with_entities(Marking.id).filter_by(assessment_enroll_id=assessment_enroll_id).all()
            for m in old_marking:
                MarkingForWriting.query.filter_by(marking_id=m.id).delete()

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

        writing_text = {}
        writing_text["%s" % "writing_text"] = ""

        for item in item_list:

            marking = Marking(testset_id=testset_id,
                              testlet_id=testlet_id,
                              item_id=item.get('item_id'),
                              question_no=item.get('order'),
                              weight=item.get('weight'),
                              candidate_r_value=writing_text,
                              candidate_mark=0,
                              outcome_score=1,
                              is_read=True,
                              assessment_enroll_id=assessment_enroll_id)
            db.session.add(marking)

            '''
            MarkingForWriting
            '''
            test_center = Codebook.query.filter(Codebook.code_type == 'test_center',
                                                Codebook.additional_info.contains(
                                                    {"campus_prefix": student.branch.strip()})).first()
            test_center_id = None
            if test_center:
                test_center_id = test_center.id

            candidate_file_link_json = {}
            candidate_mark_detail = {}

            for score in scores_list:
                questionNo = score.get("QuestionNo")
                questionNo = questionNo.replace("LANG_", "").replace("_LANG", "")
                questionNo = questionNo.replace("_ORGANIZATION", "")
                questionNo = questionNo[3:]
                questionNo = questionNo.title()
                candidate_mark_detail["%s" % questionNo] = score.get("Answer")

            marking_writing = MarkingForWriting(marking_id=marking.id, marker_id=marker_branch.marker_id)
            marking_writing.candidate_file_link = candidate_file_link_json
            marking_writing.candidate_mark_detail = candidate_mark_detail
            marking_writing.created_time = datetime.utcnow()
            marking_writing.modified_time = datetime.utcnow()
            db.session.add(marking_writing)
            db.session.commit()

    return success({"result": "success"})


def receive_image(f):
    image_filename = f.get('name')
    image_data = f.get('data').decode("base64")
    handler = open(image_filename, "wb+")
    handler.write(image_data)
    handler.close()
    return handler

# [False, False, True, False, False, True, False] -> ['C', 'F']
def marking_to_value(score):
    alfa = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    candidate_r_value = []
    markings = score[0]["marking"]

    for idx, val in enumerate(markings):
        if val:
            candidate_r_value.append(alfa[idx])

    return candidate_r_value

#Answer': '36' -> ['C', 'F']
def answer_to_value(score):
    def Convert(string):
        list1 = []
        list1[:0] = string
        return list1

    alfa = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
    candidate_r_value = []
    markings = Convert(score[0]["Answer"])

    for val in markings:
        candidate_r_value.append(alfa[int(val) -1])

    return candidate_r_value


