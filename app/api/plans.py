from flask import jsonify, request

from app.api import api
from app.decorators import permission_required
from app.models import Permission, Codebook, Assessment, EducationPlanDetail
from .. import db
from app.models import sort_codes


# EducationPlan > Add Assessments > Assessment search > Assessments return for apply
@api.route('/plan_assessments/')
@permission_required(Permission.ADMIN)
def get_plan_assessments():
    search_name = request.args.get('search_name', '01', type=str),
    search_test_type = request.args.get('search_test_type', '01', type=int),
    search_test_center = request.args.get('search_test_center', '01', type=int),
    query = Assessment.query
    if search_name[0] != '':
        query = query.filter(Assessment.name.ilike('%{}%'.format(search_name)))
    if search_test_type[0] != 0:
        query = query.filter_by(test_type=search_test_type)
    if search_test_center[0] != 0:
        query = query.filter_by(branch_id=search_test_center)
    # ToDo: Check if should be active=True
    # query = query.filter_by(active=True)

    assessments = query.order_by(Assessment.id.desc()).all()
    rows = [(row.id, row.name, Codebook.get_code_name(row.test_type), Codebook.get_code_name(row.branch_id),
             row.year) for row in assessments]
    return jsonify(rows)


# EducationPlan > List > Assessment search > Assessments return for listing
@api.route('/assessment_list/')
@permission_required(Permission.ADMIN)
def get_assessment_list():
    id = request.args.get('plan_id', '01', type=int)
    query = db.session.query(Assessment.id, Assessment.name, Assessment.test_type, Assessment.branch_id,
                             Assessment.year) \
        .join(EducationPlanDetail).filter(EducationPlanDetail.plan_id == id).order_by(EducationPlanDetail.order.asc())
    assessments = query.all()
    rows = [(row.id, row.name, Codebook.get_code_name(row.test_type), Codebook.get_code_name(row.branch_id),
             row.year) for row in assessments]
    return jsonify(rows)


# Administration > Codebook Manage > Update
@api.route('/update_codebook/', methods=['PUT'])
@permission_required(Permission.ADMIN)
def update_codebook():
    code_id = request.form.get('code_id', 0, type=int)
    code_value = request.form.get('code_value', '', type=str)
    codebook = Codebook.query.filter_by(id=code_id).first()
    codebook.code_name = code_value
    db.session.commit()

    query = Codebook.query.filter_by(code_type=codebook.code_type)
    if codebook.parent_code:
        query = query.filter_by(parent_code=codebook.parent_code)
    child = [(row.id, row.code_name) for row in query.all()]
    child.insert(0, (0, ''))
    child = sort_codes(child)
    return jsonify(child)


# Administration > Codebook Manage > Add
@api.route('/add_codebook/', methods=['POST'])
@permission_required(Permission.ADMIN)
def add_codebook():
    code_id = request.form.get('parent_code_id', None, type=int)
    code_type = request.form.get('code_type', '', type=str)
    code_value = request.form.get('code_value', '', type=str)

    codebook = Codebook(code_type=code_type, code_name=code_value, parent_code=code_id)
    db.session.add(codebook)
    db.session.commit()

    query = Codebook.query.filter_by(code_type=codebook.code_type)
    if codebook.parent_code:
        query = query.filter_by(parent_code=codebook.parent_code)
    child = [(row.id, row.code_name) for row in query.all()]
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
