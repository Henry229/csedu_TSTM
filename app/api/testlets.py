from flask import jsonify, request
from flask_login import current_user

from app.api import api
from app.decorators import permission_required
from app.models import Item, Permission, Codebook, Testlet


# Testlet > Create > Item search > Items return for apply
@api.route('/testlet_items/')
@permission_required(Permission.TESTLET_MANAGE)
def _get_testlet_items():
    search_name = request.args.get('search_name'),
    search_grade = request.args.get('search_grade'),
    search_subject = request.args.get('search_subject'),
    search_level = request.args.get('search_level'),
    search_category = request.args.get('search_category'),
    search_byme = request.args.get('search_byme', False)

    query = Item.query
    if search_name[0] != '':
        query = query.filter(Item.name.ilike('%{}%'.format(search_name[0])))
    if search_grade[0] != '0':
        query = query.filter_by(grade=search_grade[0])
    if search_level[0] != '0':
        query = query.filter_by(level=search_level[0])
    if search_subject[0] != '0':
        query = query.filter_by(subject=search_subject[0])
    if search_category[0] != '0':
        query = query.filter_by(category=search_category[0])
    if search_byme=='true':
        query = query.filter_by(modified_by=current_user.id)
    query = query.filter_by(active=True)
    items = query.order_by(Item.modified_time.desc()).all()
    rows = [(row.id, row.name, Codebook.get_code_name(row.category), Codebook.get_code_name(row.level)) for row in
            items]
    return jsonify(rows)


# Testlet > List > Testlet search > Items return for listing
@api.route('/item_list/')
@permission_required(Permission.TESTLET_MANAGE)
def get_item_list():
    id = request.args.get('testlet_id', '01', type=int)
    testlet = Testlet.query.filter_by(id=id).first()
    no_items = testlet.no_of_items
    items = testlet.items
    rows = [(row.id, row.name, Codebook.get_code_name(row.category), Codebook.get_code_name(row.level), no_items) for
            row in items]
    return jsonify(rows)
