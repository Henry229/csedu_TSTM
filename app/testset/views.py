import json
import re
import uuid
from datetime import datetime

import pytz
from flask import render_template, flash, request, redirect, url_for, jsonify
from flask_login import login_required, current_user

from qti.itemservice.itemservice import ItemService
from . import testset
from .forms import TestsetSearchForm, TestsetCreateForm
from .. import db
from ..decorators import permission_required
from ..models import Testset, Codebook, Permission, Testlet, Item, TestletHasItem, TestsetBinding

'''Testset Info Page - rendering template'''


@testset.route('/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def info(id):
    testset = Testset.query.filter_by(id=id).first()
    if testset.branching:
        parsedData = testset.parsingStageData()
        nodes = parsedData.get('nodes')
        edges = parsedData.get('edges')
    else:
        nodes = []
        edges = []
    return render_template("testset/info.html", testset=testset, nodes=nodes, edges=edges)


'''Testset New Page - rendering template'''


@testset.route('/create', methods=['GET'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def new():
    testset_id = request.args.get('id')
    error = request.args.get('error')

    stageData = request.args.get('stageData')
    testlet_db = []
    testlet_id_list = request.args.get('testlet_list')
    if testlet_id_list:
        testlet_list = testlet_id_list.split(',')
        testlet_db = [(row.id, row.name) for row in
                      Testlet.query.filter_by(active=True).filter(Testlet.id.in_(testlet_list)).order_by(
                          Testlet.name.desc()).all()]
    testset_form = TestsetCreateForm()
    if testset_id is None:
        testset_form.test_type.data = Codebook.get_code_id('Naplan')
    else:
        testset = Testset.query.filter_by(id=testset_id).first()
        testset_form.testset_id.data = testset.id
        testset_form.testset_name.data = testset.name
        testset_form.test_type.data = testset.test_type
        testset_form.grade.data = testset.grade
        testset_form.subject.data = testset.subject
        testset_form.no_stages.data = testset.no_of_stages
        testset_form.test_duration.data = testset.test_duration
        testset_form.total_score.data = testset.total_score
        if testset.extended_property:
            testset_form.link1.data = testset.extended_property['explanation_link']
        stageData = {"stage_depth": testset.no_of_stages}
    if error:
        flash(error)
    if stageData is None:
        stageData = {"stage_depth": 1}
    return render_template('testset/create.html', testset_form=testset_form, stageData=stageData, testlets=testlet_db)


'''Testset New Page - Insert new DB::testset data'''


@testset.route('/create/testset', methods=['POST'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def testset_insert():
    form = TestsetCreateForm()
    if form.validate_on_submit():
        testlets = Testlet.query.filter_by(test_type=form.test_type.data).filter_by(grade=form.grade.data).filter_by(
            subject=form.subject.data).filter_by(active=True).order_by(Testlet.name.desc()).all()
        if (len(testlets) == 0):
            flash("No testlets found having the same condition - Test Type{}, Grade:{}, Subject{}".format(
                form.test_type.data, form.grade.data, form.subject.data
            ))
            return redirect(url_for('testset.new'))
        else:
            my_guid = str(uuid.uuid4())

            testset = Testset(GUID=my_guid,
                              name=form.testset_name.data,
                              test_type=form.test_type.data,
                              grade=form.grade.data,
                              subject=form.subject.data,
                              test_duration=form.test_duration.data,
                              no_of_stages=form.no_stages.data,
                              modified_by=current_user.id)
            if form.total_score.data != '':
                testset.total_score = float(form.total_score.data)
            else:
                testset.total_score = 100
            link_json = {"explanation_link": form.link1.data}
            testset.extended_property = link_json
            db.session.add(testset)
            db.session.commit()

            testlet_list = [str(i.id) for i in testlets]
            testlet_list = ','.join(testlet_list)
            return redirect(url_for('testset.new', id=testset.id, testlet_list=testlet_list))
    else:
        flash(form.errors)
    return redirect(url_for('testset.new', error="Testset Creation Form validation Error"))


'''Testlet Branching Page'''


@testset.route('/create/branching/<int:id>', methods=['POST'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def testlet_branching(id):
    if request.json:
        import json
        testset_data = request.json

        testset = Testset.query.filter_by(id=id).first()
        testset.branching = testset_data
        testset.modified_time = datetime.now(pytz.utc)
        testset.modified_by = current_user.id
        db.session.commit()
        return json.dumps(testset_data)
    else:
        testset = Testset.query.filter_by(id=id).first()
        if testset.branching:
            testset.completed = True
            testset.active = True
            db.session.add(testset)
        db.session.commit()
        flash('Testset {} update has been finished.'.format(id))
    return redirect(
        url_for('testset.manage', grade=testset.grade, subject=testset.subject, test_type=testset.test_type))


'''Delete Testset Page - update row set delete True'''


@testset.route('/manage/delete', methods=['POST'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def delete():
    id = request.form.get('testset_id')
    if id and request.method == 'POST':
        row = Testset.query.filter(Testset.id == int(id)).filter(Testset.delete.isnot(True)).first()
        if row:
            row.delete = True
            row.modified_time = datetime.utcnow()
            row.modified_by = current_user.id
            db.session.commit()
            flash("{} has been deleted".format(row.name))
        return redirect(url_for('testset.manage', grade=row.grade, subject=row.subject, test_type=row.test_type))
    return redirect(url_for('testset.manage', error="Testset Delete - Form validation error!"))


'''Recover Testset Page - update row set delete False'''


@testset.route('/manage/recover', methods=['POST'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def recover():
    id = request.form.get('id')
    if id and request.method == 'POST':
        row = Testset.query.filter(Testset.id == int(id)).filter(Testset.delete.is_(True)).first()
        if row:
            row.delete = False
            row.modified_date = datetime.utcnow()
            row.modified_by = current_user.id
            db.session.commit()
            flash("{} has been recovered".format(row.name))
            return redirect(url_for('testset.manage', grade=row.grade, subject=row.subject, test_type=row.test_type))
    return redirect(url_for('testset.manage', error="Testset Recovery validation error!"))


'''Edit Testset Page - rendering template'''


@testset.route('/manage/update/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def edit(id):
    testset_form = TestsetCreateForm()
    testset = Testset.query.filter_by(id=id).first()
    # 사용자가 입력한 stage 수로 ui stage 세팅
    if not testset.branching:
        testset.branching = {"stage_depth": testset.no_of_stages}
    testset_form.testset_id.data = testset.id
    testset_form.testset_name.data = testset.name
    testset_form.test_type.data = testset.test_type
    testset_form.grade.data = testset.grade
    testset_form.subject.data = testset.subject
    testset_form.no_stages.data = testset.no_of_stages
    testset_form.test_duration.data = testset.test_duration
    testset_form.total_score.data = testset.total_score
    if testset.extended_property:
        testset_form.link1.data = testset.extended_property['explanation_link']

    query = Testlet.query
    query = query.filter_by(test_type=testset.test_type, grade=testset.grade, subject=testset.subject, active=True)
    testlet_db = [(row.id, row.name) for row in query.order_by(Testlet.name.desc()).all()]
    if len(testlet_db) == 0:
        flash("Please check testlets if exists. No testlets found.")
    return render_template('testset/edit.html', testset_form=testset_form, stageData=testset.branching,
                           testlets=testlet_db)


'''Edit Testset Page - insert (versioned) row into DB'''


@testset.route('/manage/update', methods=['POST'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def update():
    if request.json:
        import json
        json_data = request.json
        testset_data = json_data.get("stageData")
        testset_id = json_data.get('testset_id')
        testset_name = json_data.get('testset_name')
        test_type = json_data.get('test_type')
        grade = json_data.get('grade')
        subject = json_data.get('subject')
        no_stages = json_data.get('no_stages')
        test_duration = json_data.get('test_duration')
        total_score = json_data.get('total_score')
        link_json = {"explanation_link": json_data.get('link1')}

        # Get data from old testset
        testset = Testset.query.filter_by(id=testset_id).first()
        if testset:
            result_grade = None
            result_subject = None
            result_test_type = None
            if testset.is_versioning(testset_id, testset_name, grade, subject,
                                     test_type, no_stages, test_duration, total_score, testset_data):
                new_testset = testset.versioning()
                # Update old testset set active false
                testset.active = False
                # Update new testlet set changed information
                new_testset.name = testset_name
                new_testset.grade = grade
                new_testset.subject = subject
                new_testset.test_type = test_type
                new_testset.test_duration = test_duration
                new_testset.no_of_stages = no_stages
                if total_score != '':
                    new_testset.total_score = total_score
                else:
                    new_testset.total_score = 100
                new_testset.extended_property = link_json
                new_testset.branching = testset_data
                new_testset.modified_by = current_user.id
                new_testset.modified_time = datetime.now(pytz.utc)
                if testset_data:
                    new_testset.completed = True
                    new_testset.active = True
                db.session.add(new_testset)
                flash('New version of testset has been created.')
                result_grade = new_testset.grade
                result_subject = new_testset.subject
                result_test_type = new_testset.test_type
            else:
                testset.name = testset_name
                testset.grade = grade
                testset.subject = subject
                testset.test_type = test_type
                testset.test_duration = test_duration
                testset.no_of_stages = no_stages
                if total_score != '':
                    testset.total_score = total_score
                else:
                    testset.total_score = 100
                testset.extended_property = link_json
                testset.branching = testset_data
                testset.modified_by = current_user.id
                testset.modified_time = datetime.now(pytz.utc)
                if testset_data:
                    testset.completed = True
                    testset.active = True
                flash('Testset has been updated.')
                result_grade = testset.grade
                result_subject = testset.subject
                result_test_type = testset.test_type
            db.session.commit()
            return json.dumps(
                url_for('testset.manage', grade=result_grade, subject=result_subject, test_type=result_test_type))
    return redirect(url_for('testset.manage', error="Testset %s not found" % testset_id))


'''Clone Testlet Page - rendering template'''


@testset.route('/manage/clone/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def clone(id):
    form = TestsetCreateForm()
    testset = Testset.query.filter_by(id=id).first()
    # 사용자가 입력한 stage 수로 ui stage 세팅
    if not testset.branching:
        testset.branching = {"stage_depth": testset.no_of_stages}
    form.testset_id.data = testset.id
    form.testset_name.data = testset.name + '_cloned'
    form.test_type.data = testset.test_type
    form.grade.data = testset.grade
    form.subject.data = testset.subject
    form.no_stages.data = testset.no_of_stages
    form.test_duration.data = testset.test_duration
    form.total_score.data = testset.total_score
    form.link1.data = testset.extended_property['explanation_link']

    query = Testlet.query
    query = query.filter_by(test_type=testset.test_type, grade=testset.grade, subject=testset.subject, active=True)
    testlet_db = [(row.id, row.name) for row in query.order_by(Testlet.name.desc()).all()]
    if len(testlet_db) == 0:
        flash("Please check testlets if exists. No testlets found.")
    return render_template('testset/clone.html', testset_form=form, stageData=testset.branching,
                           testlets=testlet_db)


'''Clone Testset Page - insert new (cloned) row into DB'''


@testset.route('/manage/clone', methods=['POST'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def clone_insert():
    if request.json:
        import json
        json_data = request.json
        testset_data = json_data.get("stageData")
        testset_id = json_data.get('testset_id')
        testset_name = json_data.get('testset_name')
        test_type = json_data.get('test_type')
        grade = json_data.get('grade')
        subject = json_data.get('subject')
        no_stages = json_data.get('no_stages')
        test_duration = json_data.get('test_duration')
        total_score = json_data.get('total_score')
        link_json = {"explanation_link": json_data.get('link1')}

        len_testlets = db.session.query(Testlet.id).filter_by(test_type=test_type).filter_by(grade=grade).filter_by(
            subject=subject).filter_by(active=True).count()
        if (len_testlets == 0):
            flash("No testlets found having the same condition - Test Type{}, Grade:{}, Subject{}".format(
                test_type, grade, subject
            ))
            return json.dumps(url_for('testset.new'))
        else:
            my_guid = str(uuid.uuid4())
            testset = Testset(GUID=my_guid,
                              name=testset_name,
                              test_type=test_type,
                              grade=grade,
                              subject=subject,
                              no_of_stages=no_stages,
                              test_duration=test_duration,
                              extended_property=link_json,
                              branching=testset_data,
                              modified_by=current_user.id)
            if total_score != '':
                testset.total_score = total_score
            else:
                testset.total_score = 100
            if testset_data:
                testset.completed = True
                testset.active = True
            db.session.add(testset)
            db.session.commit()
            flash('Testset has been cloned.')
            return json.dumps(
                url_for('testset.manage', grade=testset.grade, subject=testset.subject, test_type=testset.test_type))
    return redirect(url_for('testset.manage', error="Clone - Form validation error"))


'''Testset Manage Page - rendering template'''


@testset.route('/manage', methods=['GET'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def manage():
    testset_name = request.args.get("testset_name")
    grade = request.args.get("grade")
    subject = request.args.get("subject")
    test_type = request.args.get("test_type")
    active = request.args.get("active")
    completed = request.args.get("completed")
    if testset_name or grade or subject or test_type or active or completed:
        flag = True
    else:
        flag = False
    error = request.args.get("error")
    if error:
        flash(error)
    search_form = TestsetSearchForm()
    search_form.testset_name.data = testset_name
    if grade:
        grade = int(grade)
    search_form.grade.data = grade
    if subject:
        subject = int(subject)
    search_form.subject.data = subject
    if test_type:
        test_type = int(test_type)
        search_form.test_type.data = test_type
    else:
        search_form.test_type.data = Codebook.get_code_id('Naplan')
    if active is not None:
        search_form.active.data = active
    search_form.completed.data = completed
    stageData = None
    rows = None
    #query = Testset.query.filter(Testset.active.isnot(False))
    query = Testset.query
    if flag:
        if testset_name:
            query = query.filter(Testset.name.ilike('%{}%'.format(testset_name)))
        if grade:
            query = query.filter_by(grade=grade)
        if subject:
            query = query.filter_by(subject=subject)
        if test_type:
            query = query.filter_by(test_type=test_type)
        if active:
            query = query.filter(Testset.active.is_(bool(int(active))))
        if completed:
            query = query.filter_by(active=completed)
        rows = query.order_by(Testset.id.desc()).all()
        if not rows:
            flag = False
        flash('Found {} testset(s)'.format(len(rows)))
    return render_template('testset/manage.html', is_rows=flag, form=search_form, stageData=stageData, testsets=rows)

@testset.route('/manage/questions', methods=['GET'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def question_list():
    testset_id = request.args.get('testset_id', 0, type=int)
    testset = Testset.query.filter_by(id=testset_id).first()
    result = []
    bind = None
    if testset:
        branching = json.dumps(testset.branching)
        ends = [m.end() for m in re.finditer('"id":', branching)]
        for end in ends:
            comma = branching.find(',', end)
            testlet_id = int(branching[end:comma])

            items = db.session.query(*Item.__table__.columns). \
                select_from(Item). \
                join(TestletHasItem, Item.id == TestletHasItem.item_id). \
                filter(TestletHasItem.testlet_id == testlet_id).order_by(TestletHasItem.order).all()

            for i in items:

                qti_item_obj = Item.query.filter_by(id=i.id).first()
                item_service = ItemService(qti_item_obj.file_link)
                qti_item = item_service.get_item()
                data = {
                    'item_id': i.id,
                    'html': str(qti_item.to_html())
                }
                result.append(data)
        bind = TestsetBinding.query.filter_by(testset_id=testset_id).all()
        rows = [(row.question_no, row.testset_id, row.bind_id, row.item_id) for row in bind]
    response = jsonify({'ques': result, 'bind': rows})
    return jsonify(result)

@testset.route('/manage/bind/add', methods=['GET'])
@login_required
@permission_required(Permission.TESTSET_MANAGE)
def add_bind():
    testset_id = request.args.get('testset_id', 0, type=int)
    question_no = request.args.get('question_no', '', type=str)
    item_id = request.args.get('item_id', '', type=str)
    bind_id = request.args.get('bind_id', 0, type=int)

    if question_no:
        question_no = question_no.split(',')
    if item_id:
        item_id = item_id.split(',')

    for idx, item in  enumerate(item_id):
        testset = TestsetBinding(question_no=question_no[idx],
                          testset_id=testset_id,
                          item_id=item,
                          bind_id=bind_id)
        db.session.add(testset)
    db.session.commit()

    data = {
        'status': 'success'
    }

    return jsonify(data)



'''Search testset Page - rendering template'''


@testset.route('/list', methods=['GET'])
@login_required
@permission_required(Permission.TESTSET_READ)
def list():
    testset_name = request.args.get("testset_name")
    grade = request.args.get("grade")
    subject = request.args.get("subject")
    test_type = request.args.get("test_type")
    completed = request.args.get("completed")
    if testset_name or grade or subject or test_type or completed:
        flag = True
    else:
        flag = False
    search_form = TestsetSearchForm()
    search_form.testset_name.data = testset_name
    if grade:
        grade = int(grade)
    search_form.grade.data = grade
    if subject:
        subject = int(subject)
    search_form.subject.data = subject
    if test_type:
        test_type = int(test_type)
        search_form.test_type.data = test_type
    else:
        search_form.test_type.data = Codebook.get_code_id('Naplan')
    search_form.completed.data = completed
    rows = None
    query = Testset.query.filter(Testset.active.isnot(False))
    if flag:
        if testset_name:
            query = query.filter(Testset.name.ilike('%{}%'.format(testset_name)))
        if grade:
            query = query.filter_by(grade=grade)
        if subject:
            query = query.filter_by(subject=subject)
        if test_type:
            query = query.filter_by(test_type=test_type)
        if completed:
            query = query.filter_by(active=completed)
        rows = query.order_by(Testset.id.desc()).all()
        flash('Found {} testset(s)'.format(len(rows)))
    return render_template('testset/list.html', form=search_form, testsets=rows)
