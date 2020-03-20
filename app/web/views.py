import base64
import json
import random
import string
from datetime import datetime, timedelta

import pytz
import requests
from flask import render_template, request, redirect, flash, url_for
from flask_login import login_required, login_user, current_user

from app import db
from app.testset.forms import TestsetSearchForm
from app.web.errors import forbidden, page_not_found, internal_server_error
from . import web
from .forms import StartOnlineTestForm
from ..auth.views import get_student_info, get_campuses
from ..decorators import permission_required
from ..models import Codebook, Testset, Permission, Assessment, AssessmentEnroll, Student, \
    User, Role, EducationPlan, EducationPlanDetail

"""sample usage for decorator
    @web.route('/admin')
    @login_required
    @admin_required
    def for_admins_only():
        return "For administrators!"
        
    @web.route'/testlet')
    @login_required
    @permission_required(Permission.TESTSET_MANAGEMENT)
    def itembank_testlet():
        return "For Item Bank Manager Only!"        
"""


@web.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if current_user.is_student():
        return redirect(url_for('report.list_my_report'))
    return render_template('index.html')


@web.route('/testset_simulator', methods=['GET', 'POST'])
@login_required
def testset_simulator():
    search_form = TestsetSearchForm()
    search_form.test_type.data = Codebook.get_code_id('Naplan')
    testset_name = request.args.get("testset_name")
    grade = request.args.get("grade")
    subject = request.args.get("subject")
    test_type = request.args.get("test_type")
    completed = request.args.get("completed")

    error = request.args.get("error")
    if error:
        flash(error)

    search_form.testset_name.data = testset_name
    if grade:
        grade = int(grade)
    search_form.grade.data = grade
    if subject:
        subject = int(subject)
    search_form.subject.data = subject
    if test_type:
        search_form.test_type.data = int(test_type)
    search_form.completed.data = completed

    rows = None
    flag = False
    query = Testset.query

    if (subject == 0 or grade == 0 or test_type == 0 or testset_name == ''):
        flag = True
    if testset_name:
        query = query.filter(Testset.name.ilike('%{}%'.format(testset_name)))
        flag = True
    if grade:
        query = query.filter_by(grade=grade)
        flag = True
    if subject:
        query = query.filter_by(subject=subject)
        flag = True
    if completed:
        query = query.filter_by(active=completed)
        flag = True
    if flag:
        rows = query.order_by(Testset.modified_time.desc()).all()

    return render_template('simulator.html', form=search_form, testsets=rows)


def is_authorised(student, timeout=120):
    # Get session info
    student_session = student['session']
    if student_session:
        # Check IP matching
        server_public_ip = requests.get('https://api.ipify.org').text
        public_ip = request.headers.environ[
            'HTTP_X_FORWARDED_FOR'] if 'HTTP_X_FORWARDED_FOR' in request.headers.environ else request.headers.environ[
            'REMOTE_ADDR']
        if student_session['IP'] in ("127.0.0.1", "1.158.42.34", public_ip, server_public_ip):
            # Check session expiration. Default 120min
            REG_DT = datetime.strptime(student_session['REG_DT'], "%a, %d %b %Y %H:%M:%S %Z")
            session_time = pytz.utc.localize(REG_DT)  # Change to UTC. %Z doesn't work due to a bug
            session_age = datetime.now(pytz.utc) - session_time
            if timedelta(minutes=0) < session_age < timedelta(minutes=timeout):
                return True
    return False


def update_campus_info():
    campuses = get_campuses()
    for c in campuses:
        # Skip existing campus with correct prefix
        if Codebook.query.filter(Codebook.code_type == 'test_center', Codebook.code_name == c['campus_title'],
                                 Codebook.additional_info.contains({"campus_prefix": c['campus_prefix']})).first():
            continue
        # Check one with title and update prefix
        campus = Codebook.query.filter_by(code_type='test_center', code_name=c['campus_title']).first()
        if campus:
            campus.additional_info = c
        else:
            # Register new campus
            campus = Codebook(code_type='test_center',
                              code_name=c['campus_title'],
                              additional_info=c)
            db.session.add(campus)


@web.route('/inward', methods=['GET'])
def process_inward():
    error = request.args.get("error")
    if error:
        flash(error)

    try:
        token = base64.urlsafe_b64decode(request.args.get("token"))
    except:
        return internal_server_error('Wrong token')

    args = json.loads(token.decode('UTF-8'))
    student_id = args["sid"]
    test_guid = args["aid"]
    session_timeout = int(args["sto"]) if args["sto"] else 120  # Minutes

    member = get_student_info(student_id)
    if is_authorised(member, session_timeout):
        registered_student = Student.query.filter(Student.student_id.ilike(student_id)).first()
        if registered_student:
            student_user = User.query.filter_by(id=registered_student.user_id).first()
            # Update username and branch for every login to be used in display and report
            student_user.username = "%s %s" % (member['member']['stud_first_name'], member['member']['stud_last_name'])
            student_user.last_seen = datetime.now(pytz.utc)
            registered_student.last_access = datetime.now(pytz.utc)
            registered_student.branch = member['member']['branch']
        else:
            role = Role.query.filter_by(name='Test_taker').first()
            student_user = User(
                username="%s %s" % (member['member']['stud_first_name'], member['member']['stud_last_name']),
                role=role,
                confirmed=True,
                active=True)
            student_user.password = ''.join(
                random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))
            db.session.add(student_user)
            db.session.commit()  # Commit to get the student_user.id

            student = Student(student_id=student_id,
                              user_id=student_user.id,
                              branch=member['member']['branch'])
            db.session.add(student)

        # Update campus info in the code book
        update_campus_info()
        db.session.commit()
        login_user(student_user)
        # student_data = get_member_info(student_user_id)

        # test_guid can be a plan or an assessment.
        if test_guid:
            guids = get_assessment_guids(test_guid)
            return redirect(url_for('web.assessment_list', guid_list=",".join(guids)))
        else:
            if member['sales']:
                guid_list = [sale['test_type']['title_a'] for sale in member['sales']]
                if len(guid_list):
                    all_guids = []
                    for guid in guid_list:
                        all_guids += get_assessment_guids(guid)
                    return redirect(url_for('web.assessment_list', guid_list=",".join(all_guids)))
                else:
                    return redirect(url_for('web.index'))  # TODO use report.my_report# TODO use report.my_report
    return forbidden('Insufficient permissions or no available test')


def get_assessment_guids(guid):
    """
    Get assessments guids
    :param guid: GUID of an assessment or a plan
    :return: list of assessments guids
    """
    if Assessment.query.filter_by(GUID=guid).first():
        return [guid]

    plan = EducationPlan.query.filter_by(GUID=guid).first()
    if plan:
        assessments = [item.Assessment for item in db.session.query(Assessment, EducationPlanDetail).filter(
            EducationPlanDetail.plan_id == plan.id).filter(Assessment.id == EducationPlanDetail.assessment_id).all()]
        return [assessment.GUID for assessment in assessments]


@web.route('/tests/testsets', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def testset_list():
    from ..api.assessmentsession import AssessmentSession
    assessment_guid = request.args.get("assessment_guid")
    # If assessment_guid in None, try to find it from session.
    if assessment_guid is None:
        session_id = request.args.get("session")
        if session_id is None:
            return page_not_found(e="Invalid request - session")
        assessment_session = AssessmentSession(key=session_id)
        if assessment_session.assessment is None:
            return page_not_found(e="Invalid request - assessment information")
        enroll = AssessmentEnroll.query.filter_by(id=assessment_session.get_value('assessment_enroll_id')).first()
        assessment_guid = enroll.assessment_guid

    # Parameter check
    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return page_not_found(e="Login user not registered as student")

    # Check if there is an assessment with the guid
    assessment = Assessment.query.filter_by(GUID=assessment_guid).order_by(Assessment.version.desc()).first()
    if assessment is None:
        return page_not_found(e="Invalid request - assessment information")

    # Get all assessment enroll to get testsets the student enrolled in already.
    enrolled = AssessmentEnroll.query.filter_by(assessment_guid=assessment_guid, student_user_id=student.user_id).all()
    testset_enrolled = {en.testset_id: en.id for en in enrolled}

    # Get all testset the assessment has
    testsets = assessment.testsets
    for tsets in testsets:
        tsets.enrolled = tsets.id in testset_enrolled
    sorted_testsets = sorted(testsets, key=lambda x: x.name)

    return render_template('web/testsets.html', student_user_id=student.user_id, assessment_guid=assessment_guid,
                           testsets=sorted_testsets, assessment_id=assessment.id)


@web.route('/tests/assessments', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def assessment_list():
    # Parameter check
    guid_list = request.args.get("guid_list").split(",")
    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return page_not_found(e="Login user not registered as student")

    assessments = []
    for assessment_guid in guid_list:
        # Check if there is an assessment with the guid
        assessment = Assessment.query.filter_by(GUID=assessment_guid).order_by(Assessment.version.desc()).first()
        if assessment is None:
            return page_not_found(e="Invalid request - assessment enroll information")

        # Get all assessment enroll to get testsets the student enrolled in already.
        enrolled = AssessmentEnroll.query.filter_by(assessment_guid=assessment_guid,
                                                    student_user_id=current_user.id).all()
        testset_enrolled = {en.testset_id: en.id for en in enrolled}

        # Get all testset the assessment has
        for tset in assessment.testsets:
            tset.enrolled = tset.id in testset_enrolled
        assessments.append(assessment)

    return render_template('web/assessments.html', student_user_id=current_user.id, assessments=assessments )


@web.route('/testing', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def testing():
    session_id = request.args.get("session")
    testset_id = request.args.get("testset_id")
    assessment_guid = request.args.get("assessment")
    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return page_not_found(e="Login user not registered as student")
    context = {
        'session_id': session_id,
        'student_user_id': student.user_id,
        'student_external_id': student.student_id,
        'student_branch': student.getCSCampusName(student.user_id)
    }

    if testset_id is not None:
        testset = Testset.query.filter_by(id=testset_id).first()
        if testset is None:
            return redirect(url_for('web.testset_list', error="Invalid testset requested!"))
        context['testset'] = testset
        context['assessment_guid'] = assessment_guid

    return render_template('runner/test_runner.html', **context)


@web.route('/naplan', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def start_test_manager():
    form = StartOnlineTestForm()
    assessment_guid = form.assessment_guid.data
    st_id = form.student_user_id.data
    testsets = []
    guid_list = [(a.GUID) for a in Assessment.query.distinct(Assessment.GUID).all()]
    if form.validate_on_submit():
        # Parameter check
        student = Student.query.filter_by(user_id=st_id).first()
        if student is None:
            return page_not_found(e="Invalid request - not found student information")

        # Check if there is an assessment with the guid
        assessment = Assessment.query.filter_by(GUID=assessment_guid).order_by(Assessment.version.desc()).first()
        if assessment is None:
            return page_not_found(e="Invalid request - not found assessment information")

        # Get all assessment enroll to get testsets the student enrolled in already.
        enrolled = AssessmentEnroll.query.filter_by(assessment_guid=assessment_guid, student_user_id=st_id).all()
        testset_enrolled = {en.testset_id: en.id for en in enrolled}

        # Get all testset the assessment has
        testsets = assessment.testsets
        for tsets in testsets:
            tsets.enrolled = tsets.id in testset_enrolled
    return render_template('web/start_online_test.html', guid_list=guid_list, form=form, testsets=testsets)
