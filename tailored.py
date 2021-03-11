import logging
import os
import random
import string
import time
from logging.handlers import TimedRotatingFileHandler

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# For Test Coverage
# 'coverage' package installed on 'development': requirements/dev.txt
COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage

    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()

import click
from flask import request, g
from flask_migrate import Migrate
from flask_login import current_user
from app import create_app, db
from app.models import User, Role, Permission, Codebook

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db, compare_type=True)

r_handler = TimedRotatingFileHandler(os.path.join(app.config['LOGS_DIR'], 'request.log'), when='W0')
request_logger = logging.getLogger('__name__')
request_logger.setLevel(logging.DEBUG)
request_logger.addHandler(r_handler)


# e_handler = TimedRotatingFileHandler(os.path.join(app.config['LOGS_DIR'], 'error.log'), when='W0')
# error_logger = logging.getLogger('__name__' + 'error')
# error_logger.setLevel(logging.ERROR)
# error_logger.addHandler(e_handler)


@app.before_request
def before_request():
    if g.get('start_time') is None:
        g.start_time = time.time()
    g.sidebar_show = request.cookies.get('sidebar-show', 'show') == 'show'
    g.sidebar_mini = request.cookies.get('sidebar-size', 'full') == 'mini'


@app.after_request
def after_request(response):
    import json
    if request.path.startswith('/static') or request.path.startswith('/itemstatic') \
            or request.path.startswith('/favicon.ico'):
        return response

    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    public_ip = (request.headers.environ['HTTP_X_FORWARDED_FOR']
                 if 'HTTP_X_FORWARDED_FOR' in request.headers.environ
                 else request.headers.environ['REMOTE_ADDR']
                 )
    start_time = g.get('start_time') or 0
    lapsed_time = time.time() - start_time
    user_id = current_user.id if not current_user.is_anonymous else 0
    if 'tailored_id' in request.cookies:
        tailored_id = request.cookies.get('tailored_id')
    else:
        tailored_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
        response.set_cookie('tailored_id', tailored_id)
    try:
        log_msg = {
            'time': ts,
            'ip': public_ip,
            'tailored_id': tailored_id,
            'user_id': user_id,
            # 'user_name': User.getUserName(user_id),
            'user_name': "{}".format(user_id),
            'start_time': g.start_time,
            'lapsed_time': lapsed_time,
            'method': request.method,
            'path': request.path,
            'param': request.args,
            'content_type': request.content_type,
            'user_agent': request.user_agent.string,
            'response_status': response.status_code,
            'body': {},
            'files': {},
        }
        if request.method == 'POST' or request.method == 'PUT':
            if request.is_json:
                log_msg['body'] = request.json
            else:
                log_msg['body'] = request.form.to_dict()
                log_msg['files'] = {f.name: f.filename for f in request.files.values()}

        if log_msg['body'].get('password'):
            log_msg['body']['password'] = '********'
        msg = json.dumps(log_msg)
    except TypeError as e:
        msg = '{"time": %s, "ip": %s, "tailored_id": %s, "start_time": %s, "lapsed_time": %s, "path": %s, ' \
              '"method": %s, "response_status": %s, ' \
              '"log_error": "%s"}' \
              % (ts, public_ip, tailored_id, g.start_time, lapsed_time, request.path, request.method,
                 response.status_code, e)
    except Exception as e:
        msg = '{"time": %s, "ip": %s, "tailored_id": %s, "start_time": %s, "lapsed_time": %s, "path": %s, ' \
              '"method": %s, "response_status": %s, ' \
              '"log_error": "%s"}' \
              % (ts, public_ip, tailored_id, g.start_time, lapsed_time, request.path, request.method,
                 response.status_code, e)

    request_logger.debug(msg)
    return response


@app.errorhandler(Exception)
def exceptions(e):
    import json
    import traceback
    ts = time.strftime('%Y-%b-%d %H:%M:%S')
    public_ip = (request.headers.environ['HTTP_X_FORWARDED_FOR']
                 if 'HTTP_X_FORWARDED_FOR' in request.headers.environ
                 else request.headers.environ['REMOTE_ADDR']
                 )
    if 'tailored_id' in request.cookies:
        tailored_id = request.cookies.get('tailored_id')
    else:
        tailored_id = ''
    body, files = {}, {}
    if request.method == 'POST' or request.method == 'PUT':
        if request.is_json:
            body = request.json
        else:
            body = request.form.to_dict()
            files = {f.name: f.filename for f in request.files.values()}
            files = json.dumps(files)

    if body.get('password'):
        body['password'] = '********'
    body = json.dumps(body)
    user_id = current_user.id if not current_user.is_anonymous else 0
    tb = {"traceback": traceback.format_exc()}
    tb = json.dumps(tb)
    msg = '{"time": %s, "ip": %s, "tailored_id": %s, "user_id": %s, "path": %s, ' \
          '"method": %s, "response_status": %s, "body": %s, "files": %s, ' \
          '"error": %s}' \
          % (ts, public_ip, tailored_id, user_id, request.path, request.method,
             500, body, files, tb)
    request_logger.error(msg)
    request_logger.error(traceback.format_exc())
    return "Internal Server Error", 500


# ---------------------------------
# Cli Commands
# ---------------------------------

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, Permission=Permission)


# Test Coverage Report
@app.cli.command()
@click.option('--coverage/-no-coverage', default=False, help='Run tests under code coverage.')
@click.argument('test_names', nargs=-1)
def test(coverage, test_names):
    """Run the unit tests.
    (venv) $ flask test --coverage
    """
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import subprocess, sys
        os.environ['FLASK_COVERAGE'] = '1'
        sys.exit(subprocess.call(sys.argv))

    import unittest
    if test_names:
        tests = unittest.TestLoader().loadTestsFromNames(test_names)
    else:
        tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        COV.stop()
        COV.save()
        print('Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()


# ---------------------------------
# Utils
# ---------------------------------

@app.cli.command()
def deploy():
    print('Inserting roles into Roles table')
    Role.insert_roles()

    username = "admin@cseducation.com.au"
    password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))
    with open('passwords.txt', 'w') as f:
        f.write('username: %s\npassword: %s\n\n' % (username, password))
        print('Create default admin user: <email:%s>' % username)
        User.create_default_admin(username, password)

        print('Create default non admin users')
        for u, p in User.create_default_users():
            f.write('username: %s\npassword: %s\n\n' % (u, p))
        print('User passwords saved in passwords.txt')
    # User.reset_password(token,reset_password) : need generated-token, new password

    print('Create default category: <subject> <categories:...> ')
    Codebook.create_default_category("Math",
                                     "Multiplication", "Position", "Number Sentence",
                                     "Data Analysis", "Graph", "P.S", "Addtion", "Lengh",
                                     "Arithmetic", "Perimeter", "Percentage", "Number pattern",
                                     "Multiplication", "Volume", "Conversion", "Substraction",
                                     "Line Graph")
    Codebook.create_default_category("RC",
                                     "Facts and Detail", "Drawing Conclusion", "Description",
                                     "Definition", "Understanding Lang", "Language", "Understanding",
                                     "Making Predictions", "Comprehension", "Tone", "Identifying",
                                     "Information", "Finding Word Meaning", "Meaning",
                                     "Distinguishing Between", "Author's Purpose", "Reason",
                                     "Main Idea", "Inference")
    Codebook.create_default_category("LC",
                                     "Spelling", "Grammar", "Punctuation")
    Codebook.create_default_category("Part 1",
                                     "GA-Synonym", "Maths-M&D", "GA-Antonym",
                                     "GA-Number Pattern", "Maths-Length", "GA-Alphabet Pattern",
                                     "Maths-Estimation", "GA-Figure Sequence", "GA-Odd One Out",
                                     "GA-Logic", "English-Finding", "English-Summarizing",
                                     "English-Drawing", "Math-Area")
    Codebook.create_default_category("Writing")

    Codebook.create_default_category("Addtion", "Sub1", "Sub2")
    Codebook.create_default_category("English-Drawing", "Sub1", "Sub2")
    Codebook.create_default_category("Author's Purpose", "Sub1", "Sub2")

    # Argument: parent_type, this_type, values
    print('Inserting Grade into Codebook table')
    Codebook.create_default_codeset(None, "grade", "K", "Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "Y7", "Y8", "Y9", "Y10",
                                    "Y11", "Y12")

    print('Inserting Test Type into Codebook table')
    Codebook.create_default_codeset(None, "test_type", "Naplan")
    print('Inserting <Naplan> - Level  into Codebook table')
    Codebook.create_default_codeset("Naplan", "level", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10")

    print('Inserting Test Centre into Codebook table')
    Codebook.create_default_codeset(None, "test_center", "CS Online School", "Norwest", "Castle Hill", "All")

    print('Inserting Writing Criteria into Codebook table')
    Codebook.create_default_codeset(None, "criteria", "Audience", "Text structure", "Ideas", "Persuasive devices",
                                    "Vocabulary", "Cohesion", "Paragraphing", "Sentence structure", "Punctuation",
                                    "Spelling")
    # Create DB views
    create_views()


@app.cli.command()
def reset_views():
    '''Command: $ flask reset-views'''
    remove_views()
    create_views()
    verify_views()


def create_views():
    '''
    Dependencies between tables, views and Mviews, and  ordering for creation objects
        1. marking_summary_360_degree_mview
            - marking
            - assessment_enroll

        2. marking_summary_by_category_360_degree_mview
            - marking
            - assessment_enroll
            - codebook

        3. test_summary_mview
            - marking_summary_360_degree_mview
                - marking
                - assessment_enroll

        4. csedu_education_plan_v
            - education_plan
            - education_plan_details
            - assessment_testsets
            - testset

        5. csedu_plan_assessment_testsets_enrolled_v
            - csedu_education_plan_v
                - education_plan
                - education_plan_details
                - assessment_testsets
                - testset
            - assessment_enroll

        6. Others
        item_score_summary_v
            - marking
            - assessment_enroll
            - assessment
        my_report_body_v
            - marking
            - assessment_enroll
            - item
        my_report_list_v
            - marking
            - assessment_enroll
        my_report_progress_summary_v
            - education_plan
            - education_plan_details
            - assessment_enroll
        test_summary_all_subjects_v
            - marking_summary_360_degree_mview
                - marking
                - assessment_enroll
            - student
        test_summary_by_assessment_v
            - csedu_education_plan_v
                - education_plan
                - education_plan_details
                - assessment_testsets
                - testset
            - test_summary_mview
                - marking_summary_360_degree_mview
                    - marking
                    - assessment_enroll
        test_summary_by_category_v
            - marking_summary_by_category_360_degree_mview
                - marking
                - assessment_enroll
                - codebook
        test_summary_by_center_v
            - education_plan
            - education_plan_details
            - assessment
        test_summary_by_plan_v
            - csedu_education_plan_v
                - education_plan
                - education_plan_details
                - assessment_testsets
                - testset
            - test_summary_mview
                - marking_summary_360_degree_mview
                    - marking
                    - assessment_enroll
        test_summary_by_subject_v
            - csedu_education_plan_v
                - education_plan
                - education_plan_details
                - assessment_testsets
                - testset
            - test_summary_mview
                - marking_summary_360_degree_mview
                    - marking
                    - assessment_enroll
    '''
    print('Creating views and function for report ')
    run_sqlfile('marking_summary_360_degree_mview.sql')
    run_sqlfile('marking_summary_by_category_360_degree_mview.sql')
    run_sqlfile('test_summary_mview.sql')

    run_sqlfile('csedu_education_plan_v.sql')
    run_sqlfile('csedu_plan_assessment_testsets_enrolled_v.sql')
    run_sqlfile('function_get_marking_item_percentile.sql')

    run_sqlfile('item_score_summary_v.sql')
    run_sqlfile('my_report_body_v.sql')
    run_sqlfile('my_report_list_v.sql')
    run_sqlfile('my_report_progress_summary_v.sql')

    run_sqlfile('test_summary_all_subjects_v.sql')
    run_sqlfile('test_summary_by_assessment_v.sql')
    run_sqlfile('test_summary_by_category_v.sql')
    run_sqlfile('test_summary_by_center_v.sql')
    run_sqlfile('test_summary_by_plan_v.sql')
    run_sqlfile('test_summary_by_subject_v.sql')


def run_sqlfile(filename):
    print("Executing %s" % filename)
    with open(os.path.join(app.config['DEPLOY_DATA_DIR'], 'sql', filename), 'r') as f:
        sql = f.read()
        # Try to return where there is a return value
        try:
            r = db.engine.execute(sql)
            if r.returns_rows:
                return r.fetchall()
        except Exception as e:
            print("Error: ", e)
            pass


def remove_views():
    destroy_sql = run_sqlfile('drop_views.sql')
    for sql in destroy_sql:
        print('Executing %s' % sql[0])
        db.engine.execute(sql[0])


def verify_views():
    mview_names = []
    mview_names.append('marking_summary_360_degree_mview')
    mview_names.append('marking_summary_by_category_360_degree_mview')
    mview_names.append('test_summary_mview')

    view_names = []
    view_names.append('csedu_education_plan_v')
    view_names.append('csedu_plan_assessment_testsets_enrolled_v')

    view_names.append('item_score_summary_v')
    view_names.append('my_report_body_v')
    view_names.append('my_report_list_v')
    view_names.append('my_report_progress_summary_v')

    view_names.append('test_summary_all_subjects_v')
    view_names.append('test_summary_by_assessment_v')
    view_names.append('test_summary_by_category_v')
    view_names.append('test_summary_by_center_v')
    view_names.append('test_summary_by_plan_v')
    view_names.append('test_summary_by_subject_v')

    print("Verify Materialized View object existence from DB: ")
    for object_name in mview_names:
        sql_stmt = 'SELECT  ' \
                   'EXISTS(SELECT matviewname' \
                   ' FROM pg_matviews ' \
                   " WHERE matviewname = '{}')".format(object_name)

        try:
            cursor = db.session.execute(sql_stmt)
            row = cursor.fetchone()
            if row.exists:
                print("   MView {} exists.".format(object_name))
            else:
                print(" * MView {} not exists.".format(object_name))
        except Exception as e:
            print("Error: ", e)
            pass

    print("Verify View object existence from DB: ")
    for object_name in view_names:
        sql_stmt = 'SELECT  ' \
                   'EXISTS(SELECT table_name' \
                   ' FROM information_schema.tables ' \
                   " WHERE table_name = '{}')".format(object_name)

        # Try to return where there is a return value
        try:
            cursor = db.session.execute(sql_stmt)
            row = cursor.fetchone()
            if row.exists:
                print("   View {} exists.".format(object_name))
            else:
                print(" * View {} not exists.".format(object_name))
        except Exception as e:
            print("Error: ", e)
            pass


@app.cli.command()
def change_roles():
    '''Command: $ flask change-roles'''
    print('Updating roles into Roles table')
    Role.insert_roles()


@app.cli.command()
def fillout_testcenter():
    '''Command: $ flask fillout-testcenter'''
    from app.models import AssessmentEnroll, Student
    print('Fill out AssessmentEnroll:test_center column')
    test_centers = Codebook.query.filter(Codebook.code_type == 'test_center').all()
    for ts in test_centers:

        if ts.additional_info:
            print("Testcenter {} {} - {}".format(ts.id, ts.code_name, ts.additional_info["campus_prefix"]))
        else:
            print("Testcenter {} {} - {}".format(ts.id, ts.code_name, 'None'))

    print('Fill out AssessmentEnroll:test_center column')

    aes = AssessmentEnroll.query.all()
    for ae in aes:
        student = Student.query.filter_by(user_id=ae.student_user_id).first()
        if student:
            test_center = Codebook.query.filter(Codebook.code_type == 'test_center',
                                                Codebook.additional_info.contains(
                                                    {"campus_prefix": (student.branch).strip()})).first()
            if test_center:
                enrolled = ae
                enrolled.test_center = test_center.id
                db.session.add(enrolled)
                db.session.commit()
                print("Successfully registered branch {} for student <{}>".format(student.branch, ae.student_user_id))
            else:
                print("Not found branch {} for student <{}>".format(student.branch, ae.student_user_id))
        else:
            print("Not found student <{}>".format(student))


@app.cli.command()
def fillout_default_score():
    '''Command: $ flask fillout-default-score'''
    from app.models import Marking, refresh_mviews

    print('Fill out Marking:outcome_score, candidate_mark column to default 0')
    markings = Marking.query.filter(Marking.outcome_score == None).filter(Marking.candidate_mark == None).all()
    print(len(markings))
    for marking in markings:
        print(marking)
        if marking.outcome_score is None:
            marking.outcome_score = 0
        if marking.candidate_mark is None:
            marking.candidate_mark = 0
        db.session.add(marking)
        db.session.commit()
        print("Successfully update marking <id:{}> - candidate_mark {}, outcome_score {}".format(marking.id,
                                                                                                 marking.candidate_mark,
                                                                                                 marking.outcome_score))
    refresh_mviews()


@app.cli.command()
def change_criteria():
    '''Command: $ flask change-criteria'''
    print('Updating writing criteria to be under "Naplan" test type in Codebook table')
    parent_code_id = Codebook.get_code_id('Naplan')
    criteria_list = Codebook.query.filter_by(code_type='criteria', parent_code=None).all()
    for c in criteria_list:
        c.parent_code = parent_code_id
        db.session.add(c)
        print(c)
    db.session.commit()
