import json

from app.api import api
from flask import jsonify, request

from app.api.errors import bad_request
from config import Config


@api.route('/omr/marking', methods=['POST'])
def omr_marking():
    if request.headers['Authorization'] == None or request.headers['Authorization'] != Config.AUTHORIZATION_KEY:
        return bad_request()

    retsult = json.dumps(request.json.get('result'))

    return jsonify(retsult)

@api.route('/omr/writing', methods=['POST'])
def omr_writing():
    if request.headers['Authorization'] == None or request.headers['Authorization'] != Config.AUTHORIZATION_KEY:
        return bad_request()

    retsult = json.dumps(request.json.get('result'))

    return jsonify(retsult)
