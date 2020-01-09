from flask import jsonify, request, g, url_for

from app import db
from app.api import api
from app.api.errors import forbidden
from app.decorators import permission_required
from app.models import Item, Permission, Codebook
from app.models import sort_codes


@api.route('/_get_child_codes/')
def _get_child_codes():
    parent = request.args.get('parent', '01', type=str)
    child = [(row.id, row.code_name) for row in Codebook.query.filter_by(parent_code=parent).all()]
    child.insert(0, (0, ''))
    child = sort_codes(child)
    return jsonify(child)


# def sort_codes(codesets):
#     if len(codesets) > 1:
#         if (codesets[1][1].startswith('Y') or codesets[1][1].startswith('K') or codesets[1][1].startswith('L')):
#             codesets = sorted(codesets, key=lambda x: int(x[1].strip('YKL').replace('', '0')))
#         else:
#             codesets = sorted(codesets, key=lambda x: x[1])
#     return codesets


@api.route('/items/<int:id>')
@permission_required(Permission.ITEM_EXEC)
def get_item(id):
    item = Item.query.get_or_404(id)
    return jsonify(item.to_json())


@api.route('/items/', methods=['POST'])
@permission_required(Permission.ITEM_MANAGE)
def new_item():
    item = Item.from_json(request.json)
    # item.author = g.current_user
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_json()), 201, \
           {'Location': url_for('api.get_post', id=item.id)}


@api.route('/items/<int:id>', methods=['PUT'])
@permission_required(Permission.ITEM_MANAGE)
def edit_item(id):
    item = Item.query.get_or_404(id)
    if g.current_user != item.author and \
            not g.current_user.can(Permission.ADMIN):
        return forbidden('Insufficient permissions')
    item.body = request.json.get('body', item.body)
    db.session.commit()
    return jsonify(item.to_json())
