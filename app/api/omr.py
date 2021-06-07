import json
import subprocess
from collections import namedtuple

from app.api import api
from flask import jsonify, request, current_app

from app.api.errors import bad_request
from app.models import AssessmentEnroll, Assessment, Codebook, Student, Marking, Item
from config import Config
from qti.itemservice.itemservice import ItemService
from .assessments import parse_processed_response, parse_correct_response
from .. import db

@api.route('/omr/marking', methods=['POST'])
def omr_marking():
    if request.headers['Authorization'] == None or request.headers['Authorization'] != Config.AUTHORIZATION_KEY:
        return bad_request()

    retsult = request.json.get('result')
    assessment_guid = retsult.get('assessment_guid')

    assessment = Assessment.query.filter_by(GUID=assessment_guid).order_by(Assessment.version.desc()).first()
    if assessment is None:
        return bad_request()

    student = Student.query.filter_by(user_id=retsult.get('user_id')).first()
    if student is None:
        return bad_request()

    '''
    AssessmentEnroll
    '''
    student_user_id = student.user_id
    testset_id = retsult.get('testset_id')
    attempt_count = retsult.get('attempt_count')
    assessment_type_name = assessment.test_type_name
    start_time = retsult.get('start_time')

    enrolled = AssessmentEnroll(assessment_guid=assessment_guid, assessment_id=assessment.id, testset_id=testset_id,
                                student_user_id=student_user_id, attempt_count=attempt_count,
                                start_time=start_time, assessment_type=assessment_type_name)

    student = Student.query.filter_by(user_id=retsult.get('user_id')).first()
    if student:
        test_center = Codebook.query.filter(Codebook.code_type == 'test_center',
                                     Codebook.additional_info.contains({"campus_prefix": student.branch})).first()
        if test_center:
            enrolled.test_center = test_center.id

    db.session.add(enrolled)
    db.session.commit()
    assessment_enroll_id = enrolled.id

    '''
    Marking
    '''
    marking = retsult.get('marking')
    testset_id = marking.get('testset_id')
    answers = marking.get('answers')
    #items
    column_names = ['b.testlet_id',
                    'b.item_id',
                    'b.weight'
                    ]
    sql_stmt = 'WITH data_elements(elem) AS ( ' \
               'SELECT jsonb_array_elements(branching->\'data\') ' \
               'FROM testset  where id = :testset_id ' \
               ') ' \
               'SELECT {columns} ' \
               'FROM (SELECT (elem->\'id\')::int AS id FROM data_elements) a ' \
               'INNER JOIN testlet_items b ' \
               '  ON a.id = b.testlet_id ' \
               'ORDER BY "order"'.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt, {'testset_id': testset_id})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]

    if len(rows) == 0:
        return bad_request()
    question_no = 0
    for row in rows:
        testlet_id = row.testlet_id
        item_id = row.item_id
        weight = row.weight
        answer = answers[question_no]
        '''
        candidate_r_value = answer.get('candidate_r_value')
        correct_r_value = answer.get('correct_r_value')
        outcome_score = answer.get('outcome_score')
        candidate_mark = answer.get('candidate_mark')
        is_correct = candidate_mark >= outcome_score
        '''
        qti_item_obj = Item.query.filter_by(id=item_id).first()
        db.session.expunge(qti_item_obj)

        processed = None
        try:
            item_service = ItemService(qti_item_obj.file_link)
            qti_xml = item_service.get_qti_xml_path()
            processing_php = current_app.config['QTI_RSP_PROCESSING_PHP']
            response = {"RESPONSE": {
                "base": {
                    "identifier": answer
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

        if response.get("RESPONSE") and response.get("RESPONSE").get("base") and response.get("RESPONSE").get("base").get('file'):
            candidate_response = response.get("RESPONSE").get("base")
        else:
            candidate_response = parse_processed_response(processed.get('RESPONSE'))

        candidate_r_value = candidate_response
        candidate_mark = processed.get('SCORE')
        outcome_score = processed.get('maxScore')
        is_correct = candidate_mark >= outcome_score
        correct_r_value = parse_correct_response(processed.get('correctResponses'))

        question_no += 1
        marking = Marking(testset_id=testset_id,
                          testlet_id=testlet_id,
                          item_id=item_id, question_no=question_no,
                          weight=weight,
                          candidate_r_value=candidate_r_value,
                          candidate_mark=candidate_mark,
                          outcome_score=outcome_score,
                          is_correct=is_correct,
                          correct_r_value=correct_r_value,
                          is_read=True,
                          is_flagged=False,
                          assessment_enroll_id=assessment_enroll_id)



    return jsonify(retsult)

@api.route('/omr/writing', methods=['POST'])
def omr_writing():
    if request.headers['Authorization'] == None or request.headers['Authorization'] != Config.AUTHORIZATION_KEY:
        return bad_request()

    retsult = json.dumps(request.json.get('result'))
    assessment_guid = retsult.get('assessment_guid');





    return jsonify(retsult)
