import uuid
from datetime import datetime

import pytz
import requests
from flask import render_template, flash, request, redirect, url_for, jsonify
from flask_login import login_required, current_user

from config import Config
from . import assessment
from .forms import AssessmentCreateForm, AssessmentSearchForm, AssessmentTestsetCreateForm, TestsetSearchForm
from .. import db
from ..api.httpstatus import is_success
from ..decorators import permission_required
from ..models import Codebook, Permission, Assessment, AssessmentHasTestset, EducationPlan, EducationPlanDetail, \
    AssessmentEnroll, Testset


@assessment.route('/manage/new', methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_MANAGE)
def new():
    """
    New Assessment Page - rendering template
    :return: A page to create an assessment
    """
    form = AssessmentCreateForm()
    form.test_type.data = Codebook.get_code_id('Naplan')
    # Todo: Need testcenter info
    # form.test_center.data = test_center
    return render_template("assessment/new.html", assessment_form=form)


'''New Assessment Page - insert new row into DB'''


@assessment.route('/manage/new', methods=['POST'])
@login_required
@permission_required(Permission.ASSESSMENT_MANAGE)
def insert():
    form = AssessmentCreateForm()
    if form.validate_on_submit():
        print(form.year.data)
        print(form.review_period.data)
        assessment = Assessment(GUID=str(uuid.uuid4()),
                                version=1,
                                name=form.assessment_name.data,
                                branch_id=form.test_center.data,
                                test_type=form.test_type.data,
                                year=form.year.data,
                                review_period=form.review_period.data,
                                modified_by=current_user.id,
                                modified_time=datetime.now(pytz.utc),
                                created_time=datetime.now(pytz.utc))
        # assessment.session_date = form.session_date.data
        # assessment.session_start_time = form.session_start_time.data
        # assessment.session_end_time = form.session_end_time.data
        db.session.add(assessment)
        db.session.commit()
        register_to_csonlineschool(assessment)
        flash('Assessment {} has been created.'.format(assessment.id))
        return redirect(url_for('assessment.manage', test_type=assessment.test_type, test_center=assessment.branch_id))
    return redirect(url_for('assessment.manage'), error="Assessment New - Form validation Error")


'''Delete Assessment Page - update row set delete True'''


@assessment.route('/manage/delete', methods=['POST'])
@login_required
@permission_required(Permission.ASSESSMENT_MANAGE)
def delete():
    id = request.form.get('assessment_id')
    if id and request.method == 'POST':
        row = Assessment.query.filter(Assessment.id == int(id)).filter(Assessment.delete.isnot(True)).first()
        if row:
            row.delete = True
            row.modified_time = datetime.utcnow()
            row.modified_by = current_user.id
            db.session.commit()
            flash("{} has been deleted".format(row.name))
        return redirect(url_for('assessment.manage', test_type=row.test_type, test_center=row.branch_id))
    return redirect(url_for('assessment.manage', error="Assessment Delete validation error!"))


'''Recover Assessment Page - update row set delete False'''


@assessment.route('/manage/recover', methods=['POST'])
@login_required
@permission_required(Permission.ASSESSMENT_MANAGE)
def recover():
    id = request.form.get('id')
    if id and request.method == 'POST':
        row = Assessment.query.filter(Assessment.id == int(id)).filter(Assessment.delete.is_(True)).first()
        if row:
            row.delete = False
            row.modified_date = datetime.utcnow()
            row.modified_by = current_user.id
            db.session.commit()
            register_to_csonlineschool(assessment)
            flash("{} has been recovered".format(row.name))
            return redirect(url_for('assessment.manage', test_type=row.test_type, test_center=row.branch_id))
    return redirect(url_for('assessment.manage', error="Assessment Recovery validation error!"))


'''Edit Assessment Page - rendering template'''


@assessment.route('/manage/update/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_MANAGE)
def edit(id):
    form = AssessmentCreateForm()
    assessment = Assessment.query.filter_by(id=id).first()
    form.test_type.default = assessment.test_type
    form.test_center.default = assessment.branch_id
    form.process()
    form.assessment_id.data = id
    form.assessment_name.data = assessment.name
    form.year.data = assessment.year
    form.review_period.data = assessment.review_period
    # form.session_date.data = assessment.session_date
    # form.session_start_time.data = assessment.session_start_time
    # form.session_end_time.data = assessment.session_end_time
    return render_template("assessment/new.html", assessment_form=form)


# Todo: Update source codes to new add and detail clone
'''Edit Assessment Page - insert (versioned) row into DB'''


@assessment.route('/manage/update', methods=['POST'])
@login_required
@permission_required(Permission.ASSESSMENT_MANAGE)
def update():
    form = AssessmentCreateForm()
    id = form.assessment_id.data
    if form.validate_on_submit():
        # Get data from old assessment
        assessment = Assessment.query.filter_by(id=id).first()
        if assessment:
            result_test_type = None
            result_test_center = None
            if assessment.is_versioning(id, form.assessment_name.data, form.test_type.data,
                                        form.test_center.data, form.year.data,
                                        form.review_period.data):
                new_assessment = assessment.versioning()
                # Update old assessment set active false
                assessment.active = False
                # Update new assessment set changed information
                new_assessment.name = form.assessment_name.data
                new_assessment.branch_id = form.test_center.data
                new_assessment.test_type = form.test_type.data
                new_assessment.year = form.year.data
                new_assessment.review_period = form.review_period.data
                # new_assessment.session_date = form.session_date.data
                # new_assessment.session_start_time = form.session_start_time.data
                # new_assessment.session_end_time = form.session_end_time.data
                new_assessment.modified_by = current_user.id
                new_assessment.modified_time = datetime.now(pytz.utc)
                db.session.add(new_assessment)
                # ToDo: decide if details row cloned or not when master update
                # Get old assessment details and clone those as new assessment details
                details = AssessmentHasTestset.query.filter_by(assessment_id=id).all()
                for d in details:
                    new_d = d.clone()
                    new_d.assessment_id = new_assessment.id
                    db.session.add(new_d)
                flash('Assessment has been updated.')
                result_test_type = new_assessment.test_type
                result_test_center = new_assessment.branch_id
            else:
                assessment.name = form.assessment_name.data
                assessment.year = form.year.data
                assessment.review_period = form.review_period.data
                # assessment.session_date = form.session_date.data
                # assessment.session_start_time = form.session_start_time.data
                # assessment.session_end_time = form.session_end_time.data
                assessment.modified_by = current_user.id
                assessment.modified_time = datetime.now(pytz.utc)
                flash('Assessment has been updated.')
                result_test_type = assessment.test_type
                result_test_center = assessment.branch_id
            db.session.commit()
            register_to_csonlineschool(assessment)
            return redirect(url_for('assessment.manage', test_type=result_test_type, test_center=result_test_center))
    return redirect(url_for('assessment.manage', error="Assessment %s not found" % id))


'''Clone Assessment Page - rendering template'''


@assessment.route('/manage/clone/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_MANAGE)
def clone(id):
    form = AssessmentCreateForm()
    assessment = Assessment.query.filter_by(id=id).first()
    form.test_type.default = assessment.test_type
    form.test_center.default = assessment.branch_id
    form.process()
    form.assessment_id.data = id
    form.assessment_name.data = assessment.name + '_cloned'
    form.year.data = assessment.year
    form.review_period.data = assessment.review_period
    # form.session_date.data = assessment.session_date
    # form.session_start_time.data = assessment.session_start_time
    # form.session_end_time.data = assessment.session_end_time
    return render_template("assessment/clone.html", assessment_form=form)


'''Clone Assessment Page - insert new (cloned) row into DB'''


@assessment.route('/manage/clone', methods=['POST'])
@login_required
@permission_required(Permission.ASSESSMENT_MANAGE)
def clone_insert():
    form = AssessmentCreateForm()
    if form.validate_on_submit():
        assessment = Assessment(GUID=str(uuid.uuid4()),
                                version=1,
                                name=form.assessment_name.data,
                                branch_id=form.test_center.data,
                                test_type=form.test_type.data,
                                year=form.year.data,
                                review_period=form.review_period.data,
                                modified_by=current_user.id,
                                modified_time=datetime.now(pytz.utc),
                                created_time=datetime.now(pytz.utc))
        # assessment.session_date = form.session_date.data
        # assessment.session_start_time = form.session_start_time.data
        # assessment.session_end_time = form.session_end_time.data
        db.session.add(assessment)

        details = AssessmentHasTestset.query.filter_by(assessment_id=form.assessment_id.data).all()
        for d in details:
            new_d = d.clone()
            new_d.assessment_id = assessment.id
            db.session.add(new_d)
        flash('Assessment {} has been cloned.'.format(assessment.id))
        db.session.commit()
        register_to_csonlineschool(assessment)
        return redirect(url_for('assessment.manage', test_type=assessment.test_type,
                                test_center=assessment.branch_id))
    return redirect(url_for('assessment.manage', error="Assessment Clone - Form validation error"))


'''Search Testsets(detail) for Assessment(master) Page - rendering template'''


@assessment.route('/manage/testsets/<int:id>', methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_MANAGE)
def search_detail(id):
    form = TestsetSearchForm()
    form.test_type.data = Codebook.get_code_id('Naplan')
    form.assessment_id.data = id
    return render_template('assessment/testsets.html', form=form)


# ToDo: decide if insert(=update) new master data when detail update
'''Add Testsets(detail) for Assessment(master) Page - insert or update or delete row into DB'''


@assessment.route('/manage/testsets', methods=['POST'])
@login_required
@permission_required(Permission.ASSESSMENT_MANAGE)
def add_detail():
    form = AssessmentTestsetCreateForm()
    if form.validate_on_submit():
        assessment_id = form.ordered_assessment_id.data
        test_type, test_center = 0, 0
        if len(form.ordered_ids.data):
            testset_list = form.ordered_ids.data.lstrip(',').split(',')  # for db query

            for testset_id in testset_list:
                testset = AssessmentHasTestset.query.filter_by(assessment_id=assessment_id).filter_by(
                    testset_id=testset_id).first()
                if testset is None:
                    testset = AssessmentHasTestset(assessment_id=assessment_id,
                                                   testset_id=testset_id,
                                                   modified_by=current_user.id)
                    db.session.add(testset)
                    db.session.commit()
                test_type = testset.assessment.test_type
                test_center = testset.assessment.branch_id
            t_items = AssessmentHasTestset.query.filter_by(assessment_id=assessment_id).filter(
                AssessmentHasTestset.testset_id.notin_(testset_list)).all()
        else:
            t_items = AssessmentHasTestset.query.filter_by(assessment_id=assessment_id).all()
        for i in t_items:
            db.session.delete(i)
        flash('Testsets are saved to Assessment {}.'.format(assessment_id))
        assessment = Assessment.query.filter_by(id=assessment_id).first()
        db.session.commit()
        register_to_csonlineschool(assessment)
        return redirect(url_for('assessment.manage', test_type=test_type,
                                test_center=test_center))
    return redirect(url_for('assessment.manage', error="Assessment Detail - Form validation error"))


'''Manage Assessment Page - rendering template'''


@assessment.route('/manage', methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_MANAGE)
def manage():
    test_type = request.args.get("test_type")
    test_center = request.args.get("test_center")
    if test_type or test_center:
        flag = True
    else:
        flag = False
    error = request.args.get("error")
    if error:
        flash(error)

    search_form = AssessmentSearchForm()
    if test_type:
        test_type = int(test_type)
        search_form.test_type.data = test_type
    else:
        search_form.test_type.data = Codebook.get_code_id('Naplan')
    if test_center:
        test_center = int(test_center)
    search_form.test_center.data = test_center
    rows = None
    item_form = None
    query = Assessment.query.filter_by(active=True)
    if flag:
        if test_type:
            query = query.filter_by(test_type=test_type)
        if test_center:
            query = query.filter_by(branch_id=test_center)
        rows = query.order_by(Assessment.id.desc()).all()
        if rows:
            item_form = AssessmentTestsetCreateForm()
        if not rows:
            flag = False
        flash('Found {} assessment(s)'.format(len(rows)))
    return render_template('assessment/manage.html', is_rows=flag, form=search_form, assessments=rows,
                           item_form=item_form)


'''Search Assessment Page - rendering template'''


@assessment.route('/list', methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_READ)
def list():
    test_type = request.args.get("test_type")
    test_center = request.args.get("test_center")
    if test_type or test_center:
        flag = True
    else:
        flag = False
    error = request.args.get("error")
    if error:
        flash(error)

    search_form = AssessmentSearchForm()
    if test_type:
        test_type = int(test_type)
        search_form.test_type.data = test_type
    else:
        search_form.test_type.data = Codebook.get_code_id('Naplan')
    if test_center:
        test_center = int(test_center)
    search_form.test_center.data = test_center
    rows = None
    query = Assessment.query.filter_by(active=True)
    if flag:
        if test_type:
            query = query.filter_by(test_type=test_type)
        if test_center:
            query = query.filter_by(branch_id=test_center)
        rows = query.order_by(Assessment.id.desc()).all()
        flash('Found {} assessment(s)'.format(len(rows)))
    return render_template('assessment/list.html', form=search_form, assessments=rows)


@assessment.route('/virtual_omr/<string:assessment_id>', methods=['GET'])
@login_required
@permission_required(Permission.ADMIN)
def virtual_omr(assessment_id):
    '''
    Sync marking data to csonlineschool through CS_API
    :return: Sync status page
    '''
    return virtual_omr_sync(assessment_id)


@assessment.route('/virtual_omr_sync', methods=['POST'])
def virtual_omr_sync(assessment_id=None):
    '''
    Sync given or all active assessment markings. Need to manage lock file to prevent surge
    To call this one use curl with post and the json data of SYNC_SECRET_KEY
    :return:
    '''
    process = False
    result = {}

    # Check security key for web request.
    if request:  # Called through the route. Check the security key. Post data type must be json with {'SYNC_SECRET_KEY': 'value....'}
        try:
            # TODO - May accept local IP only
            if request.json['SYNC_SECRET_KEY'] == Config.SYNC_SECRET_KEY:
                process = True
        except:
            pass
    else:  # Direct function call
        process = True

    if process:
        if assessment_id:  # A specific assessement only. called from virtual_omr()
            assessments = Assessment.query.filter_by(id=assessment_id).all()
        else:
            assessments = Assessment.query.filter_by(active=True).all()

        for assessment in assessments:
            enrolls = AssessmentEnroll.query.filter_by(assessment_guid=assessment.GUID).all()
            responses = []
            for enroll in enrolls:
                testset = Testset.query.filter_by(id=enroll.testset_id).first()
                answers = {}
                for m in enroll.marking:
                    # student answer is expected to be A, B, C, D which needs to be converted to 1, 2, 3, 4
                    try:
                        answers[m.question_no] = {'stud_answer': ord(m.candidate_r_value) - 64,
                                                  'end_flag': m.is_read}
                    except:
                        pass

                marking = {
                    'GUID': testset.GUID,
                    'student_user_id': enroll.student.student_id,
                    'answers': answers
                }
                ret = requests.post(Config.CS_API_URL + "/answer_eleven", json=marking, verify=False)
                print(testset.name, testset.GUID, enroll.student.student_id, ret.text)
                responses.append({'testset_name': testset.name,
                                  'testset_guid': testset.GUID,
                                  'student_id': enroll.student.student_id,
                                  'response': ret})

            # There should be only one assessment if an id is given
            if assessment_id:
                return render_template('assessment/virtual_orm.html', name=assessment.name, guid=assessment.GUID,
                                       responses=responses)
            else:
                result[assessment.id] = responses
        return jsonify(result)
    return "Invalid Request", 500


def register_to_csonlineschool(assessment):
    """
    Register an assessment to csonlineschool's DB
    :param assessment: An assessment to register
    :return: True on success
    """

    if Config.CS_API_DISABLE:
        return

    test_detail = []
    grade_table = {"K": "0",
                   "Y1": "1",
                   "Y2": "2",
                   "Y3": "3",
                   "Y4": "4",
                   "Y5": "5",
                   "Y6": "6",
                   "Y7": "7",
                   "Y8": "8",
                   "Y9": "9",
                   "Y10": "10",
                   "Y11": "1",
                   "Y12": "1"
                   }

    # TODO - There could be more than one plan_detail. How to handle the case?
    plan_detail = EducationPlanDetail.query.filter_by(assessment_id=assessment.id).first()
    if plan_detail:
        plan = EducationPlan.query.filter_by(id=plan_detail.plan_id).first()

        # Register the Plan if exists. Existence is checked by cs_api so it's okay to request same Plan multiple times
        if plan:
            test_type = [{
                "kind": "tstmp",
                "testtype": Codebook.get_code_name(plan.test_type),
                "title": plan.name,
                "grade": grade_table[Codebook.get_code_name(plan.grade)],
                "myear": plan.year,
                "title_a": plan.GUID,
                "details": test_detail
            }]

            info = requests.post(Config.CS_API_URL + "/tailored", json=test_type, verify=False)
            if not is_success(info.ok):
                return info.ok

    # Register Assessment and Testsets
    items = AssessmentHasTestset.query.filter_by(assessment_id=assessment.id).all()
    if len(items) > 0:
        # Don't need to register testsets as they are not used by csonlineschool
        # Use the grade of the first item
        grade = grade_table[Codebook.get_code_name(items[0].testset.grade)]
        # for item in items:
        #     grade = grade_table[Codebook.get_code_name(item.testset.grade)]
        #     test_detail.append(
        #         {
        #             "test_kind": "objective",
        #             "test_no": Codebook.get_code_name(plan_detail.order) if plan_detail else None,
        #             "title": item.testset.name,
        #             "subject": Codebook.get_code_name(item.testset.subject),
        #             "myear": assessment.year,
        #             "grade": grade,
        #             "qn_total": 0,
        #             "test_time": item.testset.test_duration,
        #             "title_a": item.testset.GUID
        #         })

        test_type = [{
            "kind": "tstm",
            "testtype": Codebook.get_code_name(assessment.test_type),
            "title": assessment.name,
            "grade": grade,
            "myear": assessment.year,
            "title_a": assessment.GUID,
            "details": test_detail
        }]

        info = requests.post(Config.CS_API_URL + "/tailored", json=test_type, verify=False)
        return info.ok
