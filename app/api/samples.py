import json
import math
import os
import re
import subprocess
import uuid
from datetime import datetime, timedelta
from time import time, strftime, gmtime

from flask import jsonify, request, current_app, render_template, session
from sqlalchemy import func

from app.api import api
from app.models import Testset, SampleAssessment, SampleAssessmentEnroll, SampleAssessmentItems, Item, Codebook, \
    SampleMarking
from qti.itemservice.itemservice import ItemService
from .assessments import parse_processed_response, parse_correct_response
from .jwplayer import get_signed_player, jwt_signed_url
from .response import success, bad_request
from .. import db
from ..decorators import check_sample_login_api


@api.route('/sample/session', methods=['POST'])
@check_sample_login_api()
def sample_create_session():
    user_ip = request.json.get('user_ip')
    tnc_agree_checked = request.json.get('tnc_agree_checked', False)
    assessment_id = request.json.get('assessment_id')

    if tnc_agree_checked is False:
        return bad_request()
    if assessment_id is None:
        return bad_request()

    assessment = SampleAssessment.query.filter_by(id=assessment_id).first()
    if assessment is None:
        return bad_request()

    session_key = str(uuid.uuid4())
    testset = Testset.query.filter_by(id=assessment.testset_id).first()
    test_duration = testset.test_duration or 70
    enrolled = SampleAssessmentEnroll(session_key=session_key,
                                sample_assessment_id=assessment_id,
                                user_id=session["sample"],
                                start_ip=user_ip)
    if user_ip:
        enrolled.start_ip = user_ip
    elif 'HTTP_X_FORWARDED_FOR' in request.headers.environ:
        enrolled.start_ip = request.headers.environ['HTTP_X_FORWARDED_FOR']
    else:
        enrolled.start_ip = request.headers.environ['REMOTE_ADDR']
    enrolled.start_time = datetime.utcnow()
    db.session.add(enrolled)
    db.session.commit()
    assessment_enroll_id = enrolled.id

    data = {
        'session': session_key,
    }
    return success(data)


@api.route('/sample/rendered/<int:sample_assessment_id>/<int:question_no>', methods=['GET'])
@check_sample_login_api()
def sample_rendered(sample_assessment_id, question_no, run_session=None):

    assessment = SampleAssessment.query.filter_by(id=sample_assessment_id).first()
    if assessment is None:
        return bad_request()

    assessment_item = SampleAssessmentItems.query.filter_by(sample_assessment_id=sample_assessment_id).filter_by(question_no=question_no).first()
    if assessment_item is None:
        return bad_request()

    response = {}
    rendered_item = ''
    qti_item_obj = Item.query.filter_by(id=assessment_item.item_id).first()
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

    rendered_template = render_template("runner/test_item.html", item=qti_item_obj, debug_rendering=False)
    if rendered_item:
        rendered_template = rendered_template.replace('rendered_html', rendered_item)
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

    if request.cookies.get('hhmmss'):
        response['test_duration'] = get_sec(request.cookies.get('hhmmss'))
    else:
        response['test_duration'] = assessment.test_duration * 60

    return success(response)



@api.route('/sample/responses', methods=['POST'])
@check_sample_login_api()
def sample_responses():
    session_key = request.json.get('session')
    question_no = request.json.get('question_no')
    response = request.json.get('response')

    if session_key is None:
        return bad_request()
    if question_no is None:
        return bad_request()

    assessmentEnroll = SampleAssessmentEnroll.query.filter_by(session_key=session_key, user_id=session["sample"]).first()
    if assessmentEnroll is None:
        return bad_request()

    assessmentItems = SampleAssessmentItems.query.filter_by(sample_assessment_id=assessmentEnroll.sample_assessment_id, question_no=question_no).first()
    if assessmentItems is None:
        return bad_request()

    max_question_no = db.session.query(func.max(SampleAssessmentItems.question_no)).filter(SampleAssessmentItems.sample_assessment_id==assessmentEnroll.sample_assessment_id).scalar()
    if question_no > max_question_no or question_no < 1:
        return bad_request()

    # response_json = request.json
    qti_item_obj = Item.query.filter_by(id=assessmentItems.item_id).first()
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
        if writing_text is None:
            candidate_response = ''
        else:
            candidate_response = {}
            if writing_text is not None:
                candidate_response["writing_text"] = writing_text
        candidate_r_value = candidate_response
    else:
        candidate_r_value = candidate_response


    candidate_mark = processed.get('SCORE')
    outcome_score = processed.get('maxScore')
    is_correct = candidate_mark >= outcome_score
    candidate_mark = processed.get('SCORE')
    outcome_score = processed.get('maxScore')
    is_correct = candidate_mark >= outcome_score
    correct_r_value = parse_correct_response(processed.get('correctResponses'))



    marking = SampleMarking.query.filter_by(sample_assessment_enroll_id=assessmentEnroll.id, question_no=question_no).first()
    if marking is None:
        marking_inserted = SampleMarking(question_no=question_no,
                                        candidate_r_value=candidate_r_value,
                                        is_correct=is_correct,
                                        candidate_mark=candidate_mark,
                                        sample_assessment_enroll_id=assessmentEnroll.id)
        db.session.add(marking_inserted)
        db.session.commit()
    else:
        marking.candidate_r_value = candidate_r_value
        marking.candidate_mark = candidate_mark
        marking.outcome_score = outcome_score
        marking.is_correct = is_correct
        db.session.commit()

    if max_question_no == question_no:
        data = {
            'last': 1,
        }
    else:
        data = sample_rendered(assessmentEnroll.sample_assessment_id, question_no + 1, run_session=None)

    return success(data)


def get_sec(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)

