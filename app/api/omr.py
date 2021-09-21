import json
import subprocess
from collections import namedtuple

from app.api import api
from flask import jsonify, request, current_app

from app.api.errors import bad_request
from app.models import AssessmentEnroll, Assessment, Codebook, Student, Marking, Item
from config import Config
from qti.itemservice.itemservice import ItemService
from .assessments import parse_processed_response, parse_correct_response, allowed_file, save_writing_data
from .response import success
from .. import db


@api.route('/omr/marking', methods=['POST', 'GET'])
def omr_marking():
    #if request.headers['Authorization'] == None or request.headers['Authorization'] != Config.AUTHORIZATION_KEY:
    #    return bad_request()

    #retsult = request.json.get('result')

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
