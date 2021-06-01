import uuid
from datetime import datetime

import pytz
from flask import render_template, flash, request, redirect, url_for
from flask_login import login_required, current_user

from . import testlet
from .forms import TestletCreateForm, TestletWMForm, ItemSearchForm, TestletItemCreateForm, TestletSearchForm
from .. import db
from ..decorators import permission_required
from ..models import Codebook, Permission, Testlet, TestletWeight, Item, Weights, TestletHasItem

'''Testlet Info Page - rendering template'''


@testlet.route('/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def info(id):
    testlet = Testlet.query.filter_by(id=id).first()
    return render_template("testlet/info.html", testlet=testlet)


'''New Testlet Page - rendering template'''


@testlet.route('/manage/new', methods=['GET'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def new():
    form = TestletCreateForm()
    form.test_type.data = Codebook.get_code_id('Naplan')
    populate_weight_form(form)  # SubForm creation

    return render_template("testlet/new.html", testlet_form=form)


'''New Testlet Page - insert new row into DB'''


@testlet.route('/manage/new', methods=['POST'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def insert():
    form = TestletCreateForm()
    if form.validate_on_submit():
        testlet = Testlet(GUID=str(uuid.uuid4()),
                          version=1,
                          name=form.testlet_name.data,
                          grade=form.grade.data,
                          subject=form.subject.data,
                          test_type=form.test_type.data,
                          no_of_items=form.no_items.data,
                          modified_by=current_user.id
                          )
        db.session.add(testlet)
        for entry in form.weights.entries:
            weight = TestletWeight(testlet_id=testlet.id,
                                   level=Codebook.get_code_id(entry.level.data),
                                   weight=entry.weight.data,
                                   modified_by=current_user.id,
                                   modified_time=datetime.now(pytz.utc))
            db.session.add(weight)
        db.session.commit()
        flash('Testlet {} has been created.'.format(testlet.id))
        return redirect(url_for('testlet.manage', grade=testlet.grade, subject=testlet.subject))
    return redirect(url_for('testlet.manage', error="Testlet New - Form validation Error"))


'''Delete Testlet Page - update row set delete True'''


@testlet.route('/manage/delete', methods=['POST'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def delete():
    id = request.form.get('testlet_id')
    if id and request.method == 'POST':
        row = Testlet.query.filter(Testlet.id == int(id)).filter(Testlet.delete.isnot(True)).first()
        if row:
            row.delete = True
            row.modified_time = datetime.utcnow()
            row.modified_by = current_user.id
            db.session.commit()
            flash("{} has been deleted".format(row.name))
        return redirect(url_for('testlet.manage', grade=row.grade, subject=row.subject))
    return redirect(url_for('testlet.manage', error="Testlet Delete - Form validation error!"))


'''Recover Testlet Page - update row set delete False'''


@testlet.route('/manage/recover', methods=['POST'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def recover():
    id = request.form.get('id')
    if id and request.method == 'POST':
        row = Testlet.query.filter(Testlet.id == int(id)).filter(Testlet.delete.is_(True)).first()
        if row:
            row.delete = False
            row.modified_date = datetime.utcnow()
            row.modified_by = current_user.id
            db.session.commit()
            flash("{} has been recovered".format(row.name))
            return redirect(url_for('testlet.manage', grade=row.grade, subject=row.subject))
    return redirect(url_for('testlet.manage', error="Testlet Recovery validation error!"))


'''Edit Testlet Page - rendering template'''


@testlet.route('/manage/update/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def edit(id):
    form = TestletCreateForm()
    testlet = Testlet.query.filter_by(id=id).first()
    form.grade.default = testlet.grade
    form.subject.default = testlet.subject
    form.test_type.default = testlet.test_type
    form.process()
    form.testlet_id.data = id
    form.testlet_name.data = testlet.name
    form.no_items.data = testlet.no_of_items  # set the proper value after initiation
    populate_weight_form(form, testlet.weights)  # SubForm data populate from the db
    return render_template("testlet/new.html", testlet_form=form)


# Todo: Update source codes to new add and detail clone
'''Edit Testlet Page - insert (versioned) row into DB'''


@testlet.route('/manage/update', methods=['POST'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def update():
    form = TestletCreateForm()
    id = form.testlet_id.data
    current_time = datetime.now(pytz.utc)
    if form.validate_on_submit():
        # Get data from old testlet
        testlet = Testlet.query.filter_by(id=id).first()
        if testlet:
            result_grade = None
            result_subject = None
            if testlet.is_versioning(id, form.testlet_name.data, form.grade.data, form.subject.data,
                                     form.test_type.data, form.no_items.data, form.weights):
                new_testlet = testlet.versioning()
                # Inactivate old testlet
                testlet.active = False
                # Update new testlet completed False when number of items are changed
                if (testlet.no_of_items != form.no_items.data):
                    if (str(len(testlet.items)) == form.no_items.data):
                        new_testlet.completed = True
                    else:
                        new_testlet.completed = False
                        flash("Please make sure that number of items selected to be {}".format(form.no_items.data))
                # Update new testlet set changed information
                new_testlet.name = form.testlet_name.data
                new_testlet.grade = form.grade.data
                new_testlet.subject = form.subject.data
                new_testlet.test_type = form.test_type.data
                new_testlet.no_of_items = form.no_items.data
                new_testlet.modified_by = current_user.id
                new_testlet.modified_time = current_time
                db.session.add(new_testlet)
                # Get old testlet details and clone those as new testlet details
                w_details = TestletWeight.query.filter_by(testlet_id=id).order_by(TestletWeight.id).all()
                for w in w_details:
                    new_w = w.clone()
                    new_w.testlet_id = new_testlet.id
                    db.session.add(new_w)
                details = TestletHasItem.query.filter_by(testlet_id=id).all()
                for d in details:
                    new_d = d.clone()
                    new_d.testlet_id = new_testlet.id
                    db.session.add(new_d)
                # Update new testlet.weights set changed information
                for entry in form.weights.entries:
                    l = Codebook.get_code_id(entry.level.data)
                    weight = TestletWeight.query.filter_by(testlet_id=new_testlet.id).filter_by(level=l).first()
                    if weight.weight != entry.weight.data:
                        weight.weight = entry.weight.data
                        weight.modified_by = current_user.id
                        weight.modified_time = current_time
                        # Update testlet_items with weights
                        for item in new_testlet.items:
                            if item.level == l:
                                row = TestletHasItem.query.filter_by(testlet_id=new_testlet.id).filter_by(
                                    item_id=item.id).first()
                                if row:
                                    row.weight = weight.weight
                                    row.modified_by = current_user.id
                                    row.modified_time = current_time
                                else:
                                    flash("Fail to update weight for item {}".format(item.id))
                flash('New version of testlet has been created.')
                result_grade = new_testlet.grade
                result_subject = new_testlet.subject
            else:
                testlet.name = form.testlet_name.data
                testlet.grade = form.grade.data
                testlet.modified_by = current_user.id
                testlet.modified_time = current_time
                flash('Testlet has been updated.')
                result_grade = testlet.grade
                result_subject = testlet.subject
            db.session.commit()
            return redirect(url_for('testlet.manage', grade=result_grade, subject=result_subject))
    return redirect(url_for('testlet.manage', error="Testlet %s not found" % id))


'''Clone Testlet Page - rendering template'''


@testlet.route('/manage/clone/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def clone(id):
    form = TestletCreateForm()
    testlet = Testlet.query.filter_by(id=id).first()
    form.grade.default = testlet.grade
    form.subject.default = testlet.subject
    form.test_type.default = testlet.test_type
    form.process()
    form.testlet_id.data = id
    form.testlet_name.data = testlet.name + '_cloned'
    form.no_items.data = testlet.no_of_items  # set the proper value after initiation
    populate_weight_form(form, testlet.weights)  # SubForm data populate from the db
    return render_template("testlet/clone.html", testlet_form=form)


'''Clone Testlet Page - insert new (cloned) row into DB'''


@testlet.route('/manage/clone', methods=['POST'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def clone_insert():
    form = TestletCreateForm()
    if form.validate_on_submit():
        testlet = Testlet(GUID=str(uuid.uuid4()),
                          version=1,
                          name=form.testlet_name.data,
                          grade=form.grade.data,
                          subject=form.subject.data,
                          test_type=form.test_type.data,
                          no_of_items=form.no_items.data,
                          modified_by=current_user.id
                          )
        db.session.add(testlet)
        db.session.commit()
        for entry in form.weights.entries:
            weight = TestletWeight(testlet_id=testlet.id,
                                   level=Codebook.get_code_id(entry.level.data),
                                   weight=entry.weight.data,
                                   modified_by=current_user.id,
                                   modified_time=datetime.now(pytz.utc))
            db.session.add(weight)
        details = TestletHasItem.query.filter_by(testlet_id=form.testlet_id.data).all()
        for d in details:
            new_d = d.clone()
            new_d.testlet_id = testlet.id
            db.session.add(new_d)
        db.session.commit()
        flash('Testlet {} has been cloned.'.format(testlet.id))
        return redirect(url_for('testlet.manage', grade=testlet.grade, subject=testlet.subject))
    return redirect(url_for('testlet.manage', error="Clone - Form validation error"))


'''Search Item(detail) for Testlet(master) Page - rendering template'''


@testlet.route('/manage/items/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def search_detail(id):
    form = ItemSearchForm()
    form.category.choices = [(0, ' ')]
    form.testlet_id.data = id
    return render_template('testlet/items.html', form=form)


'''Add Item(detail) for Testlet(master) Page - insert or update or delete row into DB'''


@testlet.route('/manage/items', methods=['POST'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def add_detail():
    form = TestletItemCreateForm()
    current_time = datetime.now(pytz.utc)
    if form.validate_on_submit():
        testlet_id = form.ordered_testlet_id.data
        testlet = Testlet.query.filter_by(id=testlet_id).first()
        if len(form.ordered_ids.data):
            item_list = form.ordered_ids.data.lstrip(',').split(',')
            i = 1
            for item_id in item_list:
                item_level = Item.query.filter_by(id=item_id).first()
                weight = Weights.get_weight(testlet_id, item_level.level)

                item = TestletHasItem.query.filter_by(testlet_id=testlet_id).filter_by(item_id=item_id).first()
                if item:
                    item.order = i
                    item.weight = weight
                    item.modified_by = current_user.id
                    item.modified_time = current_time
                else:
                    item = TestletHasItem(testlet_id=testlet_id,
                                          item_id=item_id,
                                          order=i,
                                          weight=weight,
                                          modified_by=current_user.id)
                    db.session.add(item)
                i = i + 1

            if (i - 1) == testlet.no_of_items:
                testlet.completed = True
                testlet.active = True
            testlet.modified_by = current_user.id
            testlet.modified_time = current_time

            t_items = TestletHasItem.query.filter_by(testlet_id=testlet_id).filter(
                TestletHasItem.item_id.notin_(item_list)).all()
        else:
            t_items = TestletHasItem.query.filter_by(testlet_id=testlet_id).all()
        for i in t_items:
            db.session.delete(i)
        flash('Item(s) saved for Testlet {}.'.format(testlet_id))
        db.session.commit()
        return redirect(url_for('testlet.manage', grade=testlet.grade, subject=testlet.subject))
    return redirect(url_for('testlet.manage', error="Testlet Item Creation - Form Validation Error"))


'''Testlet SubForm Generation: populate weight data for testlet'''


def populate_weight_form(form, weights=None):
    if weights is None:
        levels = Codebook.query.filter_by(code_type='level').order_by(Codebook.id).all()
        while len(form.weights) > 0:
            form.weights.pop_entry()

        for l in levels:
            wm_form = TestletWMForm()  # weight mapping
            wm_form.level = l.code_name
            wm_form.weight = '1.0'
            form.weights.append_entry(wm_form)
    else:
        while len(form.weights) > 0:
            form.weights.pop_entry()
        for w in weights:
            wm_form = TestletWMForm()  # weight mapping
            wm_form.level = Codebook.get_code_name(w.level)
            wm_form.weight = w.weight
            form.weights.append_entry(wm_form)
    return form


'''Testlet Manage Page - rendering template'''


@testlet.route('/manage', methods=['GET'])
@login_required
@permission_required(Permission.TESTLET_MANAGE)
def manage():
    testlet_name = request.args.get("testlet_name")
    grade = request.args.get("grade")
    subject = request.args.get("subject")
    active = request.args.get("active")
    completed = request.args.get("completed")
    if testlet_name or grade or subject or active or completed:
        flag = True
    else:
        flag = False
    error = request.args.get("error")
    if error:
        flash(error)
    search_form = TestletSearchForm()
    search_form.testlet_name.data = testlet_name
    if grade:
        grade = int(grade)
    search_form.grade.data = grade
    if subject:
        subject = int(subject)
    search_form.subject.data = subject
    if active is not None:
        search_form.active.data = active
    search_form.completed.data = completed
    rows = None
    item_form = None
    #query = Testlet.query.filter(Testlet.active.isnot(False))
    query = Testlet.query
    if flag:
        if testlet_name:
            query = query.filter(Testlet.name.ilike('%{}%'.format(testlet_name)))
        if grade:
            query = query.filter_by(grade=grade)
        if subject:
            query = query.filter_by(subject=subject)
        if active:
            query = query.filter(Testlet.active.is_(bool(int(active))))
        if completed:
            query = query.filter_by(completed=completed)
        rows = query.order_by(Testlet.id.desc()).all()
        if rows:
            item_form = TestletItemCreateForm()
        else:
            flag = False
        flash('Found {} testlet(s)'.format(len(rows)))
    return render_template('testlet/manage.html', is_rows=flag, form=search_form, testlets=rows, item_form=item_form)


'''Search testlet Page - rendering template'''


@testlet.route('/list', methods=['GET'])
@login_required
@permission_required(Permission.TESTSET_READ)
def list():
    search_form = TestletSearchForm()
    testlet_name = request.args.get("testlet_name")
    grade = request.args.get("grade")
    subject = request.args.get("subject")
    completed = request.args.get("completed")
    if testlet_name or grade or subject or completed:
        flag = True
    else:
        flag = False
    search_form.testlet_name.data = testlet_name
    if grade:
        grade = int(grade)
    search_form.grade.data = grade
    if subject:
        subject = int(subject)
    search_form.subject.data = subject
    search_form.completed.data = completed
    rows = None
    query = Testlet.query.filter(Testlet.active.isnot(False))
    if flag:
        if testlet_name:
            query = query.filter(Testlet.name.ilike('%{}%'.format(testlet_name)))
        if grade:
            query = query.filter_by(grade=grade)
        if subject:
            query = query.filter_by(subject=subject)
        if completed:
            query = query.filter_by(completed=completed)
        rows = query.order_by(Testlet.id.desc()).all()
        flash('Found {} testlet(s)'.format(len(rows)))
    return render_template('testlet/list.html', form=search_form, testlets=rows)
