import uuid
from datetime import datetime

import pytz
from flask import render_template, flash, request, redirect, url_for
from flask_login import login_required, current_user

from . import plan
from .forms import EducationPlanCreateForm, EducationPlanDetailCreateForm, EducationPlanSearchForm, \
    AssessmentSearchForm, CodebookForm
from .. import db
from ..decorators import permission_required
from ..models import Permission, EducationPlan, EducationPlanDetail

'''New Education Plan Page - rendering template'''


@plan.route('/manage/new', methods=['GET'])
@login_required
@permission_required(Permission.ADMIN)
def new():
    form = EducationPlanCreateForm()
    return render_template("plan/new.html", plan_form=form)


'''New Education Plan Page - insert new row into DB'''


@plan.route('/manage/new', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def insert():
    form = EducationPlanCreateForm()

    if form.validate_on_submit():
        plan = EducationPlan(GUID=str(uuid.uuid4()),
                             version=1,
                             name=form.plan_name.data,
                             grade=form.grade.data,
                             year=form.year.data,
                             test_type=form.test_type.data,
                             modified_by=current_user.id
                             )
        db.session.add(plan)
        db.session.commit()
        flash('EducationPlan {} has been created.'.format(plan.id))
        return redirect(url_for('plan.manage', year=plan.year, test_type=plan.test_type, grade=plan.grade))
    return redirect(url_for('plan.manage'), error="Education Plan New - Form validation Error")


'''Delete Education Plan Page - update row set delete True'''


@plan.route('/manage/delete', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def delete():
    id = request.form.get('plan_id')
    if id and request.method == 'POST':
        row = EducationPlan.query.filter(EducationPlan.id == int(id)).filter(EducationPlan.delete.isnot(True)).first()
        if row:
            row.delete = True
            row.modified_time = datetime.utcnow()
            row.modified_by = current_user.id
            flash("{} has been deleted".format(row.name))
        db.session.commit()
        return redirect(url_for('plan.manage', year=row.year, test_type=row.test_type, grade=row.grade))
    return redirect(url_for('plan.manage', error="EducationPlan Delete validation error!"))


'''Recover Education Plan Page - update row set delete False'''


@plan.route('/manage/recover', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def recover():
    id = request.form.get('id')
    if id and request.method == 'POST':
        row = EducationPlan.query.filter(EducationPlan.id == int(id)).filter(EducationPlan.delete.is_(True)).first()
        if row:
            row.delete = False
            row.modified_date = datetime.utcnow()
            row.modified_by = current_user.id
            flash("{} has been recovered".format(row.name))
            db.session.commit()
            return redirect(url_for('plan.manage', year=row.year, test_type=row.test_type, grade=row.grade))
    return redirect(url_for('plan.manage', error="EducationPlan Recovery validation error!"))


'''Edit Education Plan Page - rendering template'''


@plan.route('/manage/update/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.ADMIN)
def edit(id):
    form = EducationPlanCreateForm()

    plan = EducationPlan.query.filter_by(id=id).first()
    form.year.default = plan.year
    form.grade.default = plan.grade
    form.test_type.default = plan.test_type
    form.process()
    form.plan_id.data = id
    form.plan_name.data = plan.name

    return render_template("plan/new.html", plan_form=form)


'''Edit Education Plan Page - insert (versioned) row into DB'''


@plan.route('/manage/update', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def update():
    form = EducationPlanCreateForm()
    if form.validate_on_submit():
        # Get data from old plan
        # Check if versioning needed:
        plan = EducationPlan.query.filter_by(id=form.plan_id.data).first()
        if plan:
            result_year = None
            result_test_type = None
            result_grade = None
            if plan.is_versioning(id, form.plan_name.data, form.year.data,
                                  form.grade.data, form.test_type.data):
                new_plan = plan.versioning()
                # Update old plan set active false
                plan.active = False
                # Update new plan set changed information
                new_plan.name = form.plan_name.data
                new_plan.year = form.year.data
                new_plan.grade = form.grade.data
                new_plan.test_type = form.test_type.data
                db.session.add(new_plan)
                # Get old plan details and clone those as new plan details
                details = EducationPlanDetail.query.filter_by(plan_id=form.plan_id.data).all()
                for d in details:
                    new_d = d.clone()
                    new_d.plan_id = new_plan.id
                    db.session.add(new_d)
                flash('Plan has been updated.')
                result_year = new_plan.year
                result_test_type = new_plan.test_type
                result_grade = new_plan.grade
            else:
                plan.name = form.plan_name.data
                plan.modified_by = current_user.id
                plan.modified_time = datetime.now(pytz.utc)
                flash('Plan has been updated.')
                result_year = plan.year
                result_test_type = plan.test_type
                result_grade = plan.grade
            db.session.commit()
            return redirect(url_for('plan.manage', year=result_year, test_type=result_test_type, grade=result_grade))
    return redirect(
        url_for('plan.manage', error="Education Plan Edit Form Validation Error", plan_id=form.plan_id.data))


'''Clone Education Plan Page - rendering template'''


@plan.route('/manage/clone/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.ADMIN)
def clone(id):
    form = EducationPlanCreateForm()

    plan = EducationPlan.query.filter_by(id=id).first()
    form.year.default = plan.year
    form.grade.default = plan.grade
    form.test_type.default = plan.test_type
    form.process()
    form.plan_id.data = id
    form.plan_name.data = plan.name + '_cloned'

    return render_template("plan/clone.html", plan_form=form)


'''Clone Education Plan Page - insert new (cloned) row into DB'''


@plan.route('/manage/clone', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def clone_insert():
    form = EducationPlanCreateForm()
    if form.validate_on_submit():
        plan = EducationPlan(GUID=str(uuid.uuid4()),
                             version=1,
                             name=form.plan_name.data,
                             grade=form.grade.data,
                             year=form.year.data,
                             test_type=form.test_type.data,
                             modified_by=current_user.id
                             )
        db.session.add(plan)
        details = EducationPlanDetail.query.filter_by(plan_id=form.plan_id.data).all()
        for d in details:
            new_d = d.clone()
            new_d.plan_id = plan.id
            db.session.add(new_d)
        db.session.commit()
        flash('EducationPlan {} has been cloned.'.format(plan.id))
        return redirect(url_for('plan.manage', year=plan.year, test_type=plan.test_type, grade=plan.grade))
    return redirect(url_for('plan.manage', error="Clone - Form validation error"))


'''Search Assessment(detail) for Education Plan(master) Page - rendering template'''


@plan.route('/manage/assessments/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.ADMIN)
def search_detail(id):
    assessment_form = AssessmentSearchForm()
    assessment_form.plan_id.data = id
    return render_template('plan/assessments.html', form=assessment_form)


# ToDo: decide if insert(=update) new master data when detail update
'''Add Assessment(detail) for Education Plan(master) Page - insert or update or delete row into DB'''


@plan.route('/manage/assessments', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def add_detail():
    form = EducationPlanDetailCreateForm()

    if form.validate_on_submit():
        plan_id = form.ordered_plan_id.data
        plan = EducationPlan.query.filter_by(id=plan_id).first()
        if len(form.ordered_ids.data):
            assessment_list = form.ordered_ids.data.lstrip(',').split(',')  # for db query
            i = 1
            plan.modified_by = current_user.id
            plan.modified_time = datetime.now(pytz.utc)
            for assessment_id in assessment_list:
                row = EducationPlanDetail.query.filter_by(plan_id=plan_id).filter_by(
                    assessment_id=assessment_id).first()
                if row:
                    row.order = i
                    row.modified_by = current_user.id
                    row.modified_time = datetime.now(pytz.utc)
                else:
                    row = EducationPlanDetail(plan_id=plan_id,
                                              assessment_id=assessment_id,
                                              order=i,
                                              modified_by=current_user.id)
                    db.session.add(row)
                i = i + 1
            d_rows = EducationPlanDetail.query.filter_by(plan_id=plan_id).filter(
                EducationPlanDetail.assessment_id.notin_(assessment_list)).all()
        else:
            d_rows = EducationPlanDetail.query.filter_by(plan_id=plan_id).all()
        for i in d_rows:
            db.session.delete(i)
        db.session.commit()
        flash('Assessment(s) saved to EducationPlan {}.'.format(plan_id))
        return redirect(url_for('plan.manage', year=plan.year, test_type=plan.test_type, grade=plan.grade))
    return redirect(url_for('plan.manage'))


'''Manage Education Plan Page - rendering template'''


@plan.route('/manage', methods=['GET'])
@login_required
@permission_required(Permission.ADMIN)
def manage():
    plan_name = request.args.get("plan_name")
    year = request.args.get("year")
    test_type = request.args.get("test_type")
    grade = request.args.get("grade")
    if plan_name or year or test_type or grade:
        flag = True
    else:
        flag = False
    error = request.args.get("error")
    if error:
        flash(error)

    search_form = EducationPlanSearchForm()
    search_form.plan_name.data = plan_name
    search_form.year.data = year
    if test_type:
        test_type = int(test_type)
    search_form.test_type.data = test_type
    if grade:
        grade = int(grade)
    search_form.grade.data = grade
    rows = None
    item_form = None
    query = EducationPlan.query.filter_by(active=True)
    if flag:
        if plan_name:
            query = query.filter(EducationPlan.name.ilike('%{}%'.format(plan_name)))
        if year:
            query = query.filter_by(year=year)
        if test_type:
            query = query.filter_by(test_type=test_type)
        if grade:
            query = query.filter_by(grade=grade)
        rows = query.order_by(EducationPlan.id.desc()).all()
        if rows:
            item_form = EducationPlanDetailCreateForm()
        else:
            flag = False
        flash('Found {} plan(s)'.format(len(rows)))
    return render_template('plan/manage.html', is_rows=flag, form=search_form, plans=rows, item_form=item_form)


@login_required
@permission_required(Permission.ADMIN)
@plan.route('/code_manage', methods=['GET', 'POST'])
@login_required
def code_manage():
    form = CodebookForm()
    return render_template('plan/code_manage.html', form=form)
