import logging
import os
import random
import shutil
import string
import time
from getpass import getpass
from glob import glob
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
from app import create_app, db
from app.models import User, Role, Permission, Codebook

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db, compare_type=True)

r_handler = TimedRotatingFileHandler(os.path.join(app.config['LOGS_DIR'], 'request.log'), when='W0')
e_handler = TimedRotatingFileHandler(os.path.join(app.config['LOGS_DIR'], 'error.log'), when='W0')
request_logger = logging.getLogger('__name__')
request_logger.setLevel(logging.ERROR)
request_logger.addHandler(r_handler)
error_logger = logging.getLogger('__name__' + 'error')
error_logger.setLevel(logging.ERROR)
error_logger.addHandler(e_handler)


@app.before_request
def before_request():
    if g.get('start_time') is None:
        g.start_time = time.time()
    g.sidebar_show = request.cookies.get('sidebar-show', 'show') == 'show'
    g.sidebar_mini = request.cookies.get('sidebar-size', 'full') == 'mini'


@app.after_request
def after_request(response):
    if request.path.startswith('/static'):
        return response
    return response


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
    with open('admin.txt', 'w') as f:
        f.write('username: %s\npassword: %s' % (username, password))
    print('Create default admin user: <email:%s> <password saved in admin.txt>' % username)
    User.create_default_admin(username, password)

    print('Create default users(except Administrator):<password:{}>'.format("welcome"))
    User.create_default_user("welcome")
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

    print('Inserting Test Center into Codebook table')
    Codebook.create_default_codeset(None, "test_center", "CS Online School", "Norwest", "Castle Hill", "All")

    # Create DB views
    create_views()


def create_views():
    print('Creating views and function for report ')
    run_sqlfile('csedu_education_plan_v.sql')
    run_sqlfile('csedu_plan_assessment_testsets_enrolled_v.sql')
    run_sqlfile('function_get_marking_item_percentile.sql')
    run_sqlfile('item_score_summary_v.sql')
    run_sqlfile('marking_summary_360_degree_mview.sql')
    run_sqlfile('marking_summary_by_category_360_degree_mview.sql')
    run_sqlfile('test_summary_mview.sql')
    run_sqlfile('test_summary_all_subjects_v.sql')
    run_sqlfile('test_summary_by_assessment_v.sql')
    run_sqlfile('test_summary_by_category_v.sql')
    run_sqlfile('test_summary_by_plan_v.sql')
    run_sqlfile('test_summary_by_subject_v.sql')
    run_sqlfile('my_report_body_v.sql')
    run_sqlfile('my_report_list_v.sql')
    run_sqlfile('my_report_progress_summary_v.sql')
    run_sqlfile('test_summary_by_center_v.sql')


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


@app.cli.command()
def destroy():
    secret = getpass("This will delete all data files and DB, The secret key: ")
    if secret == app.config['DELETE_SECRET_KEY']:
        destroy_sql = run_sqlfile('destroy.sql')
        for sql in destroy_sql:
            print('Executing %s' % sql[0])
            db.engine.execute(sql[0])
        try:
            print('Removing the migrations folder')
            shutil.rmtree('migrations', ignore_errors=True)
            print('Removing the storage folder')
            shutil.rmtree('storage', ignore_errors=True)
            print('Removing the storage.* folders')
            for folder in glob('storage.*'):
                shutil.rmtree(folder, ignore_errors=True)
        except:
            pass
