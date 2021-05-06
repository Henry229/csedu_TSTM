import json

from app.api import api
from flask import jsonify, request


@api.route('/omr/marking', methods=['POST'])
#@login_required
def omr_marking():
    retsult = json.dumps(request.json.get('result'))

    return jsonify(retsult)

@api.route('/omr/writing', methods=['POST'])
#@login_required
def omr_writing():
    retsult = json.dumps(request.json.get('result'))

    return jsonify(retsult)
