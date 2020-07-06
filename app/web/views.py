import base64
import json
import random
import string
from datetime import datetime, timedelta

import pytz
import requests
from flask import render_template, request, redirect, flash, url_for
from flask_login import login_required, login_user, current_user, logout_user

from app import db
from app.testset.forms import TestsetSearchForm
from app.web.errors import forbidden, page_not_found, internal_server_error
from common.logger import log
from config import Config
from . import web
from .forms import StartOnlineTestForm
from ..auth.views import get_student_info, get_campuses
from ..decorators import permission_required
from ..models import Codebook, Testset, Permission, Assessment, AssessmentEnroll, Student, \
    User, Role, EducationPlan, EducationPlanDetail, ItemExplanation, MarkingForWriting, Marking

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
    elif current_user.is_writing_marker():
        return redirect(url_for('writing.manage'))
    return render_template('index.html')


@web.route('/loggedout', methods=['GET'])
def loggedout():
    return render_template('loggedout.html')


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
    errors = []
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
                return True, errors
            else:
                errors.append("Student's CSOnlineSchool session has been expired")
        else:
            errors.append("Student logged in different IP address from CSOnlineSchool")
    else:
        errors.append("Student not logged into CSOnlineSchool")
    return False, errors


def update_campus_info(state):
    campuses = get_campuses(state)
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
            c['branch_state'] = state
            campus = Codebook(code_type='test_center',
                              code_name=c['campus_title'],
                              additional_info=c)
            db.session.add(campus)


@web.route('/inward', methods=['GET'])
def process_inward():
    if current_user.is_authenticated:
        log.info("A user is logged in. Logging the user out first")
        logout_user()

    error = request.args.get("error")
    if error:
        flash(error)

    try:
        token = base64.urlsafe_b64decode(request.args.get("token"))
    except:
        return internal_server_error('Wrong token')

    args = json.loads(token.decode('UTF-8'))
    log.debug("Inward: %s" % args)
    state = list(Config.CS_BRANCH_STATES.keys())[0]  # Set default state
    if "state" in args.keys():
        state = args["state"]
    student_id = args["sid"]
    test_guid = args["aid"]
    session_timeout = int(args["sto"]) if args["sto"] else 120  # Minutes

    try:
        member = get_student_info(state, student_id)
    except:
        return forbidden("Invalid Request")
    authorised, errors = is_authorised(member, session_timeout)
    if authorised:
        registered_student = Student.query.filter(Student.student_id.ilike(student_id), Student.state == state).first()
        if registered_student:
            student_user = User.query.filter_by(id=registered_student.user_id).first()
            # Update username and branch for every login to be used in display and report
            student_user.username = "%s %s (%s)" % (
                member['member']['stud_first_name'], member['member']['stud_last_name'], student_id)
            student_user.last_seen = datetime.now(pytz.utc)
            registered_student.last_access = datetime.now(pytz.utc)
            registered_student.branch = member['member']['branch']
        else:
            role = Role.query.filter_by(name='Test_taker').first()
            student_user = User(
                username="%s %s (%s)" % (
                    member['member']['stud_first_name'], member['member']['stud_last_name'], student_id),
                role=role,
                confirmed=True,
                active=True)
            student_user.password = ''.join(
                random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))
            db.session.add(student_user)
            db.session.commit()  # Commit to get the student_user.id

            student = Student(student_id=student_id,
                              user_id=student_user.id,
                              branch=member['member']['branch'],
                              state=state)
            db.session.add(student)

        # Update campus info in the code book
        update_campus_info(state)
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
            else:
                logout_user()
                return forbidden('No available test found')
    return forbidden('<br>'.join(errors))


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


@web.route('/tests/assessments', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def assessment_list():
    import os
    from config import basedir
    from ..api.assessmentsession import AssessmentSession
    # Parameter check
    guid_list = request.args.get("guid_list")
    if guid_list is not None:
        # it's coming from external link like cs online school
        guid_list = guid_list.split(",")
    else:
        # it's coming from internal link like finishing test or errors.
        assessment_guid = request.args.get("assessment_guid")
        session_id = request.args.get("session")
        if assessment_guid is not None:
            guid_list = [assessment_guid]
        elif session_id is not None:
            # Exam is finished. it has only session key as a parameter.
            assessment_session = AssessmentSession(key=session_id)
            if assessment_session.assessment is None:
                return page_not_found(e="Invalid request - assessment information")
            enroll = AssessmentEnroll.query.filter_by(id=assessment_session.get_value('assessment_enroll_id')).first()
            assessment_guid = enroll.assessment_guid
            guid_list = [assessment_guid]
        else:
            # Show all assessment enrols if there is no guid parameter.
            enrols = AssessmentEnroll.query.filter_by(student_user_id=current_user.id).all()
            guid_list = list({e.assessment_guid for e in enrols})

    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return page_not_found(e="Login user not registered as student")

    assessments, finished_assessments = [], []
    assessments_list = {}
    exam_count, homework_count = 0, 0
    for assessment_guid in guid_list:
        # Check if there is an assessment with the guid
        assessment = Assessment.query.filter_by(GUID=assessment_guid).order_by(Assessment.version.desc()).first()
        if assessment is None:
            continue
            # return page_not_found(e="Invalid request - assessment enroll information")
        elif assessment.session_date:
            # if assessment session_date is comming after today, skip to display on student's assessment list page
            if assessment.session_date > datetime.today():
                continue

        # Get all assessment enroll to get testsets the student enrolled in already.
        enrolled = AssessmentEnroll.query.join(Testset, Testset.id == AssessmentEnroll.testset_id)\
            .filter(AssessmentEnroll.assessment_guid == assessment_guid,
                    AssessmentEnroll.student_user_id == current_user.id).all()
        enrolled_guid_assessment_types = {en.testset.GUID: en.assessment_type for en in enrolled}

        # Get testsets in enrolled
        # enrolled_testsets = {en.testset_id: en.testset for en in enrolled}
        enrolled_testsets = {}
        for en in enrolled:
            en.testset.resumable = False
            en.testset.enroll_id = en.id
            if en.finish_time is None and en.test_duration is not None:
                elapsed = datetime.utcnow() - en.start_time
                if elapsed.total_seconds() < en.test_duration * 60:
                    en.testset.resumable = True
                    en.testset.session_key = en.session_key
            enrolled_testsets[en.testset_id] = en.testset

        student_testsets = []
        # 전체 testset 에서 학생이 아직 시험을 안 본 것을 우선 모든다.
        for tset in assessment.testsets:
            if tset.GUID not in enrolled_guid_assessment_types:
                tset.resumable = False
                student_testsets.append(tset)
        # 이미 시험을 본 것을 모은다.
        for ts_id in enrolled_testsets:
            student_testsets.append(enrolled_testsets[ts_id])
        new_test_sets = []
        flag_finish_assessment = True
        assessment_type_name = Codebook.get_code_name(assessment.test_type)
        if assessment_type_name == 'Homework':
            homework_count += 1
            assessment.assessment_type_name = 'Homework'
            assessment.assessment_type_class = 'assessment-homework'
        else:
            exam_count += 1
            assessment.assessment_type_name = 'Exam'
            assessment.assessment_type_class = 'assessment-exam'
        for tset in student_testsets:
            # Compare GUID to check enrollment status
            is_enrolled = tset.GUID in enrolled_guid_assessment_types
            # 시험을 보지 않았는데, active 가 아니라는 말은 testset 이 그동안 버전이 변경되었다는 것이다.
            if not is_enrolled and not tset.active:
                # 최신 test set version 을 찾는다.
                # tset_with_guid = Testset.query.filter_by(id=tset.id).first()
                tset = Testset.query.filter_by(GUID=tset.GUID, active=True).first()
            if not is_enrolled or tset.resumable:
                flag_finish_assessment = False
            # if is_enrolled:
            #     assessment_type = enrolled_guid_assessment_types[tset.GUID]
            #     tset.report_type = 'error-note' if assessment_type == 'Homework' else 'report'
            tset.report_type = 'error-note' if assessment_type_name == 'Homework' else 'report'
            new_test_sets.append(tset)
            tset.enrolled = is_enrolled
            test_type = Codebook.get_code_name(tset.test_type)
            tset.enable_report = True if test_type in ['Naplan', 'Online OC', 'Homework'] else Config.ENABLE_STUDENT_REPORT
            # If subject is 'Writing', report enabled:
            #   - True when Marker's comment existing for 'ALL' items in Testset
            #   - False when Marker's comment not existing
            tset.enable_writing_report = False
            subject = Codebook.get_code_name(tset.subject)
            additional_info = Codebook.get_additional_info(tset.subject)
            tset.sort_key = additional_info['subject_order'] if additional_info else 1
            if subject == 'Writing' and tset.enable_report:
                mws = db.session.query(MarkingForWriting.markers_comment).join(Marking). \
                    join(AssessmentEnroll). \
                    filter(Marking.id == MarkingForWriting.marking_id). \
                    filter(AssessmentEnroll.id == Marking.assessment_enroll_id). \
                    filter(AssessmentEnroll.student_user_id == current_user.id). \
                    filter(Marking.testset_id == tset.id).all()
                for mw in mws:
                    tset.enable_writing_report = True if mw.markers_comment else False
                    if not tset.enable_writing_report:
                        break
            tset.explanation_link = view_explanation(tset.id)
        # sorted_testsets = sorted(new_test_sets, key=lambda x: x.name)
        sorted_testsets = sorted(new_test_sets, key=lambda x:x.sort_key)
        assessment.testsets = sorted_testsets

        # Split assessments and finished_assessments
        if flag_finish_assessment:
            finished_assessments.append(assessment)
        else:
            assessments.append(assessment)
        assessments_list = {"Assessments": assessments, "Finished - Assessments": finished_assessments}
        log.debug("Student report: %s" % Config.ENABLE_STUDENT_REPORT)

    if homework_count is 0 and exam_count is 0:
        btn_group = ''
        btn_all = {'active': '', 'display': 'style="display:none"', 'checked': ''}
        btn_exam = {'active': '', 'display': 'style="display:none"', 'checked': ''}
        btn_homework = {'active': '', 'display': 'style="display:none"', 'checked': ''}
    elif homework_count is 0:
        btn_group = ''
        btn_all = {'active': '', 'display': 'style="display:none"', 'checked': ''}
        btn_exam = {'active': 'active', 'display': '', 'checked': 'checked'}
        btn_homework = {'active': '', 'display': 'style="display:none"', 'checked': ''}
    elif exam_count is 0:
        btn_group = ''
        btn_all = {'active': '', 'display': 'style="display:none"', 'checked': ''}
        btn_exam = {'active': '', 'display': 'style="display:none"', 'checked': ''}
        btn_homework = {'active': 'active', 'display': '', 'checked': 'checked'}
    else:
        btn_group = 'btn-group'
        btn_all = {'active': 'active', 'display': '', 'checked': 'checked'}
        btn_exam = {'active': '', 'display': '', 'checked': ''}
        btn_homework = {'active': '', 'display': '', 'checked': ''}
    # return render_template('web/assessments.html', student_user_id=current_user.id, assessments=assessments,
    # finished_assessments=finished_assessments)
    try:
        with open(os.path.join(basedir, 'runner_version.txt')) as f:
            runner_version = f.readline().strip()
    except FileNotFoundError:
        runner_version = str(int(datetime.utcnow().timestamp()))
    return render_template('web/assessments.html', student_user_id=current_user.id, assessments_list=assessments_list,
                           runner_version=runner_version, btn_all=btn_all, btn_exam=btn_exam,
                           btn_homework=btn_homework, btn_group=btn_group)


@web.route('/testing', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def testing():
    """
    o testset 에서 start 를 클릭해서 들어오는 경우
        - session_id is None을
        - assessment_guid is not None
    o testset 에서 resume 을 클릭해서 들어오는 경우
    o 문제 화면에서 refresh 를 하는 경우
        - session_id is not None
        - assessment_guid is None

    """
    import os
    from app.api.assessmentsession import AssessmentSession
    from config import basedir

    session_id = request.args.get("session")
    testset_id = request.args.get("testset_id")
    assessment_guid = request.args.get("assessment")
    # assessment_guid 가 없으면 session key 로 부터 enroll id 를 찾아서 알아 낸다.
    if assessment_guid is None and session_id is not None:
        enroll_id = AssessmentSession.enrol_id_from_session_key(session_id)
        enroll = AssessmentEnroll.query.filter_by(id=enroll_id).first()
        assessment_guid = enroll.assessment_guid
    student = Student.query.filter_by(user_id=current_user.id).first()
    if student is None:
        return page_not_found(e="Login user not registered as student")
    context = {
        'session_id': session_id,
        'student_user_id': student.user_id,
        'student_external_id': student.student_id,
        'student_branch': student.getCSCampusName(student.user_id),
        'assessment_guid': assessment_guid,
    }

    if testset_id is not None:
        testset = Testset.query.filter_by(id=testset_id).first()
        if testset is None:
            return redirect(url_for('web.testset_list', error="Invalid testset requested!"))
        context['testset'] = testset

    try:
        with open(os.path.join(basedir, 'runner_version.txt')) as f:
            runner_version = f.readline().strip()
    except FileNotFoundError:
        runner_version = str(int(datetime.utcnow().timestamp()))
    context['runner_version'] = runner_version

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


def view_explanation(testset_id, item_id=None):
    url = None
    if item_id:
        item = ItemExplanation.query.filter_by(item_id=item_id).first()
        if item and item.links:
            url = item.links['link1']
            url2 = item.links['link2']
            url3 = item.links['link3']
            url4 = item.links['link4']
            url5 = item.links['link5']
    else:
        testset = Testset.query.filter_by(id=testset_id).first()
        if testset.extended_property:
            url = testset.extended_property['explanation_link']
    return url


@web.route('/tests/modal', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def modal_test():
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
        enrolled = AssessmentEnroll.query.join(Testset, Testset.id==AssessmentEnroll.testset_id)\
            .filter(AssessmentEnroll.assessment_guid==assessment_guid,
                    AssessmentEnroll.student_user_id==current_user.id).all()
        enrolled_guids = [en.testset.GUID for en in enrolled]

        # Get testsets in enrolled
        enrolled_testsets = {en.testset_id: en.testset for en in enrolled}
        student_testsets = []
        for tset in assessment.testsets:
            if tset.GUID not in enrolled_guids:
                student_testsets.append(tset)
        for ts_id in enrolled_testsets:
            student_testsets.append(enrolled_testsets[ts_id])
        new_test_sets = []
        for tset in student_testsets:
            # Compare GUID to check enrollment status
            enrolled = tset.GUID in enrolled_guids
            if not enrolled and not tset.active:
                tset_with_guid = Testset.query.filter_by(id=tset.id).first()
                tset = Testset.query.filter_by(GUID=tset_with_guid.GUID, active=True).first()
            new_test_sets.append(tset)
            tset.enrolled = enrolled
            test_type = Codebook.get_code_name(tset.test_type)
            additional_info = Codebook.get_additional_info(tset.subject)
            tset.sort_key = additional_info['subject_order'] if additional_info else 1
            tset.enable_report = True if (test_type == 'Naplan' or test_type == 'Online OC') else Config.ENABLE_STUDENT_REPORT
            tset.explanation_link = view_explanation(tset.id)
        # sorted_testsets = sorted(new_test_sets, key=lambda x: x.name)
        sorted_testsets = sorted(new_test_sets, key=lambda x:x.sort_key)
        assessment.testsets = sorted_testsets
        assessments.append(assessment)
        log.debug("Student report: %s" % Config.ENABLE_STUDENT_REPORT)

    return render_template('web/test_modal_video_assessments.html', student_user_id=current_user.id, assessments=assessments)


@web.route('/tests/mp4_testing', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def mp4_testing():
    return render_template('web/testing.html')