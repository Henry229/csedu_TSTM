import json
import os
from collections import namedtuple
from datetime import datetime, date, timedelta

import pytz
from flask import render_template, flash, request, current_app, redirect, url_for, jsonify, send_file
from flask_jsontools import jsonapi
from flask_login import login_required, current_user
from sqlalchemy import func, text

from common.logger import log
from . import report
from .forms import ReportSearchForm, ItemSearchForm
from .. import db
from ..api.reports import query_my_report_list_v, query_my_report_header, query_my_report_body, query_report_graph, \
    make_naplan_student_report, query_all_report_data, \
    query_individual_progress_summary_report_list, \
    query_test_ranking_subject_list, query_test_ranking_data, build_test_ranking_excel_response, \
    query_item_score_summary_data, query_individual_progress_summary_report_header, \
    query_individual_progress_summary_report_by_assessment, query_individual_progress_summary_report_by_plan, \
    query_individual_progress_summary_by_subject_v, query_individual_progress_summary_by_plan_v, \
    build_test_results_pdf_response, build_test_results_zipper, \
    build_individual_progress_pdf_response, build_individual_progress_zipper, \
    draw_individual_progress_by_subject, draw_individual_progress_by_set, query_my_report_footer, search_assessment
from ..decorators import permission_required, permission_required_or_multiple
from ..models import Codebook, Permission, AssessmentEnroll, Assessment, EducationPlanDetail, \
    Item, Marking, EducationPlan, Student, Testset, AssessmentHasTestset, refresh_mviews, User, MarkingForWriting, \
    TestletHasItem, Choices
from ..web.views import view_explanation

''' 
 @report.route('/full_report/<int:student_id>', methods=['GET'])
 full_report() : Administration > User Manage > Student List > request Full_Report 
'''


@jsonapi
@report.route('/full_report/<int:student_user_id>', methods=['GET'])
@login_required
@permission_required(Permission.ADMIN)
def full_report(student_user_id):
    error = request.args.get("error")
    if error:
        flash(error)
    result = full_report_data(student_user_id)
    # result.headers["Content-Disposition"] = \
    #     "attachment;" \
    #     "attachment;filename=full_report.json"
    return result


def full_report_data(student_user_id):
    # student_user_id=15, 54, 58, 1, 73, 74
    student = Student.query.filter_by(user_id=58).first()

    assessment = []
    # ToDo: Temporarily query guid_list from AssessmentEnroll table. List should be from csonlineschool(API)
    guid_list = [sub.assessment_guid for sub in db.session.query(AssessmentEnroll.assessment_guid).
        filter(AssessmentEnroll.student_user_id == student_user_id).all()]

    assessment_enrolls = AssessmentEnroll.query.filter(AssessmentEnroll.assessment_guid.in_(guid_list)). \
        filter_by(student_user_id=student_user_id).order_by(AssessmentEnroll.assessment_guid.asc()).all()
    for assessment_enroll in assessment_enrolls:
        assessment.append(assessment_enroll)
    my_report_list = query_my_report_list_v(student_user_id)
    return jsonify(student, assessment, my_report_list)


''' 
 @report.route('/my_report', methods=['GET'])
 list_my_report() : Student Login > My Report 
    - List all enrolled assessment
    - Provide link to Student Report by assessment (all subject)
    - Provide link to Subject Report 
'''


@report.route('/my_report', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def list_my_report():
    student_user_id = current_user.id
    error = request.args.get("error")
    if error:
        flash(error)

    # Change My Report page to sync with assessment_list
    #
    #     My Report List : 'id', 'assessment_id', 'student_user_id', 'year', 'test_type', 'name', 'branch_id',
    #                    'subject_1', 'subject_2', 'subject_3', 'subject_4', 'subject_5'
    #     rows = query_my_report_list_v(student_user_id)
    #     return render_template("report/my_report_list.html", assessment_enrolls=rows)
    #
    rows = db.session.query(AssessmentEnroll.assessment_guid).distinct().filter_by(
        student_user_id=student_user_id).all()
    if not rows:
        error = "Your account[{}] is not open for assessments yet. Please contact your branch office.".format(
            Student.getCSStudentName(student_user_id))
        return render_template('404_student.html', error=error), 404
    guid_list = [row.assessment_guid for row in rows]
    guid_list = ','.join(guid_list)
    return redirect(url_for('web.assessment_list', guid_list=guid_list))


@report.route('/grf/<int:assessment_id>/<int:ts_id>/<student_user_id>', methods=['GET'])
@login_required
# @permission_required(Permission.ITEM_EXEC)
@permission_required_or_multiple(Permission.ITEM_EXEC, Permission.ASSESSMENT_READ)
def my_graph_report(assessment_id, ts_id, student_user_id):
    testset = Testset.query.with_entities(Testset.subject, Testset.grade, Testset.test_type).filter_by(id=ts_id).first()
    if testset is None:
        url = request.referrer
        flash('testset data is not available')
        return redirect(url)

    test_subject_string = Codebook.get_code_name(testset.subject)
    grade = Codebook.get_code_name(testset.grade)
    test_type = testset.test_type

    assessment_name = (Assessment.query.with_entities(Assessment.name).filter_by(id=assessment_id).first()).name

    rows = query_report_graph(assessment_id, student_user_id)
    subject1 = ''
    subject2 = ''
    subject3 = ''
    subject4 = ''
    percent1 = ''
    percent2 = ''
    percent3 = ''
    percent4 = ''

    i = 0
    for row in rows:
        if i == 0:
            subject1 = row.subject
            percent1 = row.my_pecent
        elif i == 1:
            subject2 = row.subject
            percent2 = row.my_pecent
        elif i == 2:
            subject3 = row.subject
            percent3 = row.my_pecent
        elif i == 3:
            subject4 = row.subject
            percent4 = row.my_pecent
        i += 1

    template_file = 'report/my_report_graph.html'
    return render_template(template_file, assessment_name=assessment_name, grade=grade,
                           subject=test_subject_string, test_type=test_type, student_user_id=student_user_id,
                           subject1=subject1,
                           percent1=percent1, subject2=subject2, percent2=percent2, subject3=subject3,
                           percent3=percent3,
                           subject4=subject4, percent4=percent4)


@report.route('/ts/<int:assessment_id>/<int:ts_id>/<student_user_id>', methods=['GET'])
@login_required
# @permission_required(Permission.ITEM_EXEC)
@permission_required_or_multiple(Permission.ITEM_EXEC, Permission.ASSESSMENT_READ)
def my_report(assessment_id, ts_id, student_user_id):
    '''
     @report.route('/ts/<int:assessment_id>/<int:ts_id>/<int:student_user_id>', methods=['GET'])
     my_report() : Student Login > My Report > Report
        - Execute: Provide link to Subject Report
    '''
    # Todo: Check accessibility to get report
    # refresh_mviews()

    # in the case that subject is Vocabulary, the source is separated
    testset = Testset.query.with_entities(Testset.subject, Testset.grade, Testset.test_type).filter_by(id=ts_id).first()
    if testset is None:
        url = request.referrer
        flash('testset data is not available')
        return redirect(url)

    test_subject_string = Codebook.get_code_name(testset.subject)
    # if test_subject_string.lower() == 'vocabulary':
    #    return vocabulary_report(request, assessment_id, ts_id, student_user_id, testset, test_subject_string)

    grade = Codebook.get_code_name(testset.grade)
    test_type = testset.test_type

    pdf = False
    pdf_url = "%s?type=pdf" % request.url
    if 'type' in request.args.keys():
        pdf = request.args['type'] == 'pdf'

    query = AssessmentEnroll.query.with_entities(AssessmentEnroll.id, AssessmentEnroll.testset_id,
                                                 AssessmentEnroll.finish_time, AssessmentEnroll.start_time). \
        filter_by(assessment_id=assessment_id). \
        filter_by(testset_id=ts_id). \
        filter_by(student_user_id=student_user_id)
    row = query.order_by(AssessmentEnroll.id.desc()).first()
    if row is None:
        url = request.referrer
        flash('Assessment Enroll data not available')
        return redirect(url)

    assessment_enroll_id = row.id

    finish_time = row.finish_time
    if finish_time is None: finish_time = row.start_time

    is_7days_after_finished = (pytz.utc.localize(finish_time) + timedelta(days=7)) >= datetime.now(pytz.utc)
    assessment_name = (Assessment.query.with_entities(Assessment.name).filter_by(id=assessment_id).first()).name

    # setting review period for Holiday course
    enable_holiday = False
    period_holiday_review = 0
    test_type_additional_info = Codebook.get_additional_info(test_type)

    # show video to only incorrect queston
    video_for_incorrect = True
    if test_type_additional_info is not None:
        if test_type_additional_info.get('video_for_incorrect'):
            if test_type_additional_info['video_for_incorrect'] == "false":
                video_for_incorrect = False

    if test_type_additional_info is not None and 'enable_holiday' in test_type_additional_info:
        if test_type_additional_info['enable_holiday'] == "true":
            enable_holiday = True
            # change review time for Holiday course's incorrect questions and videos
            if test_type_additional_info['period_holiday_review']:
                period_holiday_review = test_type_additional_info['period_holiday_review']
                is_7days_after_finished = (pytz.utc.localize(finish_time) + timedelta(
                    days=period_holiday_review)) >= datetime.now(pytz.utc)

    # My Report : Header - 'total_students', 'student_rank', 'score', 'total_score', 'percentile_score'

    ts_header = query_my_report_header(assessment_enroll_id, assessment_id, ts_id, student_user_id)
    if ts_header is None:
        url = request.referrer
        flash('Marking data not available')
        # refresh materialized view takes 5 minutes
        # flash('Please wait. It will take about 5 minutes to get the test results.')
        return redirect(url)

    score = '{} out of {} ({}%)'.format(ts_header.score, ts_header.total_score, ts_header.percentile_score)
    '''
    if ts_header.student_rank1 is None:
        rank = '{} out of {}'.format(ts_header.student_rank, ts_header.total_students)
    else:
        rank = '{} out of {}'.format(ts_header.student_rank1, ts_header.total_students1)
    '''
    rank = '{} out of {}'.format(ts_header.student_rank, ts_header.total_students)

    # My Report : Body - Item ID/Candidate Value/IsCorrect/Correct_Value, Correct_percentile, Item Category
    #                       'assessment_enroll_id', 'testset_id', 'candidate_r_value', 'student_user_id', 'grade',
    #                       "created_time", 'is_correct', 'correct_r_value', 'item_percentile', 'item_id', 'category'
    markings = query_my_report_body(assessment_enroll_id, ts_id, assessment_id)
    explanation_link = {}
    for marking in markings:
        explanation_link[marking.question_no] = view_explanation(testset_id=ts_id, item_id=marking.item_id)
        '''
        if marking.correct_r_value is not None:
            if isinstance(marking.correct_r_value, list):
                if len(marking.correct_r_value) > 0:
                    gap_exists = False
                    gap_list = []
                    for v in marking.correct_r_value:
                        if " gap_" in v:
                            gap_exists = True
                            gap_list.append(v[:v.rfind(" gap_")])
                    if gap_exists:
                        marking.correct_r_value = gap_list
        '''

    # My Report : Footer - Candidate Avg Score / Total Avg Score by Item Category
    #                       'code_name as category', 'score', 'total_score', 'avg_score', 'percentile_score'
    # ToDo: ts_by_category unavailable until finalise all student's mark and calculate average data
    #       so it need to be discussed to branch out in "test analysed report"
    # ts_by_category = None
    ts_by_category = query_my_report_footer(assessment_id, student_user_id, assessment_enroll_id, ts_id)

    if test_subject_string == 'Writing':
        marking_writing_id = 0
        url_i = url_for('writing.w_report', assessment_enroll_id=assessment_enroll_id,
                        student_user_id=student_user_id, marking_writing_id=marking_writing_id)
        return redirect(url_i)

    template_file = 'report/my_report.html'
    if pdf:
        template_file = 'report/my_report_pdf.html',
    rendered_template_pdf = render_template(template_file, assessment_name=assessment_name,
                                            subject=test_subject_string, rank=rank,
                                            is_7days_after_finished=is_7days_after_finished,
                                            score=score, markings=markings, ts_by_category=ts_by_category,
                                            student_user_id=student_user_id, static_folder=current_app.static_folder,
                                            pdf_url=pdf_url, grade=grade, video_for_incorrect=video_for_incorrect,
                                            explanation_link=explanation_link, test_type=test_type,
                                            r_value=modifying_r_value)
    if not pdf:
        return rendered_template_pdf
    # PDF download
    from weasyprint import HTML

    html = HTML(string=rendered_template_pdf)

    pdf_file_path = os.path.join(current_app.config['USER_DATA_FOLDER'],
                                 str(student_user_id),
                                 "report",
                                 "test_report_%s_%s_%s_%s.pdf" % (
                                     assessment_enroll_id, assessment_id, ts_id, student_user_id))

    os.chdir(os.path.join(current_app.config['USER_DATA_FOLDER']))
    if not os.path.exists(str(student_user_id)):
        os.makedirs(str(student_user_id))
    os.chdir(str(student_user_id))
    if not os.path.exists("report"):
        os.makedirs("report")

    html.write_pdf(target=pdf_file_path, presentational_hints=True)
    rsp = send_file(
        pdf_file_path,
        mimetype='application/pdf',
        as_attachment=True,
        attachment_filename=pdf_file_path)

    return rsp

def modifying_r_value(value):
    if value is None:
        return value
    elif isinstance(value, list):
        if len(value) > 0:
            result = []
            for v in value:
                if " gap_" in v:
                    result.append(v[v.rfind("_") + 1:] + '. ' + v[:v.rfind(" gap_")])
                else:
                    result.append(v)
            return result
        else:
            return value
    else:
        return value


def vocabulary_report(request, assessment_id, ts_id, student_user_id, testset, test_subject_string):
    grade = Codebook.get_code_name(testset.grade)
    test_type = testset.test_type

    pdf = False
    pdf_url = "%s?type=pdf" % request.url
    if 'type' in request.args.keys():
        pdf = request.args['type'] == 'pdf'

    query = AssessmentEnroll.query.with_entities(AssessmentEnroll.id, AssessmentEnroll.testset_id,
                                                 AssessmentEnroll.finish_time, AssessmentEnroll.start_time). \
        filter_by(assessment_id=assessment_id). \
        filter_by(testset_id=ts_id). \
        filter_by(student_user_id=student_user_id)
    row = query.order_by(AssessmentEnroll.id.desc()).first()
    if row is None:
        url = request.referrer
        flash('Assessment Enroll data not available')
        return redirect(url)

    assessment_enroll_id = row.id

    assessment_name = (Assessment.query.with_entities(Assessment.name).filter_by(id=assessment_id).first()).name

    '''
    markings = query_my_report_body(assessment_enroll_id, ts_id)
    markings = db.session.query(Marking.assessment_enroll_id, Marking.testset_id,
                                         Marking.read_time, Marking.candidate_r_value, Marking.is_correct, Marking.correct_r_value,
                                         Marking.question_no). \
        join(AssessmentEnroll, Marking.assessment_enroll_id == AssessmentEnroll.id). \
        filter(Marking.assessment_enroll_id == assessment_enroll_id).first()
    '''
    marking = Marking.query.filter(Marking.assessment_enroll_id == assessment_enroll_id).first()
    if marking is None:
        url = request.referrer
        flash('Marking data is not available')
        return redirect(url)

    read_time = marking.read_time.strftime("%Y-%m-%d %a")
    item_id = marking.item_id

    sql = 'select a.id, a.value as correct_r_value, b.value as candidate_r_value ' \
          'from ' \
          '(select row_number() over() as id, value from json_array_elements(:correct_r_value)) a ' \
          'left join ' \
          '(select row_number() over() as id, value from json_array_elements(:candidate_r_value)) b ' \
          'on a.id = b.id'
    cursor_1 = db.engine.execute(text(sql), {'correct_r_value': json.dumps(marking.correct_r_value),
                                             'candidate_r_value': json.dumps(marking.candidate_r_value)})
    Record = namedtuple('Record', cursor_1.keys())
    rows = [Record(*r) for r in cursor_1.fetchall()]

    list = []
    for row in rows:
        correct_r_value = json.dumps(row.correct_r_value)
        value_num = correct_r_value[correct_r_value.rfind('_') + 1:]
        if correct_r_value.find(" gap_") > -1:
            end = correct_r_value.index(" gap_")
            correct_r_value = correct_r_value[1:end]

        candidate_r_value = ''
        for r in rows:
            if r.candidate_r_value:
                student_value = json.dumps(r.candidate_r_value)
                if student_value[student_value.rfind('_') + 1:] == value_num:
                    end = student_value.index(" gap_")
                    candidate_r_value = student_value[1:end]

        if correct_r_value == candidate_r_value:
            is_correct = True
        else:
            is_correct = False

        list.append({'correct_r_value': correct_r_value,
                     'candidate_r_value': candidate_r_value,
                     'id': row.id,
                     'is_correct': is_correct})

    correct_count = len([item['id'] for item in list if item['is_correct']])
    score = '{} out of {}'.format(correct_count, len(list))

    template_file = 'report/my_report_vocabulary.html'
    if pdf:
        template_file = 'report/my_report_vocabulary_pdf.html',

    rendered_template_pdf = render_template(template_file, assessment_name=assessment_name,
                                            subject=test_subject_string, score=score,
                                            markings=list, read_time=read_time, item_id=item_id,
                                            student_user_id=student_user_id, static_folder=current_app.static_folder,
                                            pdf_url=pdf_url, grade=grade,
                                            test_type=test_type)
    if not pdf:
        return rendered_template_pdf
    # PDF download
    from weasyprint import HTML

    html = HTML(string=rendered_template_pdf)

    pdf_file_path = os.path.join(current_app.config['USER_DATA_FOLDER'],
                                 str(student_user_id),
                                 "report",
                                 "test_report_%s_%s_%s_%s.pdf" % (
                                     assessment_enroll_id, assessment_id, ts_id, student_user_id))

    os.chdir(os.path.join(current_app.config['USER_DATA_FOLDER']))
    if not os.path.exists(str(student_user_id)):
        os.makedirs(str(student_user_id))
    os.chdir(str(student_user_id))
    if not os.path.exists("report"):
        os.makedirs("report")

    html.write_pdf(target=pdf_file_path, presentational_hints=True)
    rsp = send_file(
        pdf_file_path,
        mimetype='application/pdf',
        as_attachment=True,
        attachment_filename=pdf_file_path)
    return rsp


@report.route('/ts_v2/<int:assessment_id>/<int:ts_id>/<student_user_id>', methods=['GET'])
@login_required
# @permission_required(Permission.ITEM_EXEC)
@permission_required_or_multiple(Permission.ITEM_EXEC, Permission.ASSESSMENT_READ)
def my_report_v2(assessment_id, ts_id, student_user_id):
    '''
     @report.route('/ts_v2/<int:assessment_id>/<int:ts_id>/<int:student_user_id>', methods=['GET'])
     my_report() : Student Login > My Report > Report
        - Execute: Provide link to Subject Report
    '''
    # Todo: Check accessibility to get report
    # refresh_mviews()
    # url = request.referrer
    # flash('refresh_mviews')
    # return redirect(url)

    pdf = False
    pdf_url = "%s?type=pdf" % request.url
    if 'type' in request.args.keys():
        pdf = request.args['type'] == 'pdf'

    query = AssessmentEnroll.query.with_entities(AssessmentEnroll.id, AssessmentEnroll.testset_id). \
        filter_by(assessment_id=assessment_id). \
        filter_by(testset_id=ts_id). \
        filter_by(student_user_id=student_user_id)
    row = query.order_by(AssessmentEnroll.id.desc()).first()
    if row is None:
        url = request.referrer
        flash('Assessment Enroll data not available')
        return redirect(url)

    assessment_enroll_id = row.id
    assessment_name = (Assessment.query.with_entities(Assessment.name).filter_by(id=assessment_id).first()).name
    testset = Testset.query.with_entities(Testset.subject, Testset.grade, Testset.test_type).filter_by(
        id=row.testset_id).first()
    test_subject_string = Codebook.get_code_name(testset.subject)
    grade = Codebook.get_code_name(testset.grade)
    test_type = testset.test_type
    # My Report : Header - 'total_students', 'student_rank', 'score', 'total_score', 'percentile_score'

    ts_header = query_my_report_header(assessment_enroll_id, assessment_id, ts_id, student_user_id)
    if ts_header is None:
        url = request.referrer
        flash('Marking data not available')
        return redirect(url)
    score = '{} out of {} ({}%)'.format(ts_header.score, ts_header.total_score, ts_header.percentile_score)
    rank = '{} out of {}'.format(ts_header.student_rank1, ts_header.total_students1)
    # My Report : Body - Item ID/Candidate Value/IsCorrect/Correct_Value, Correct_percentile, Item Category
    #                       'assessment_enroll_id', 'testset_id', 'candidate_r_value', 'student_user_id', 'grade',
    #                       "created_time", 'is_correct', 'correct_r_value', 'item_percentile', 'item_id', 'category'
    markings = query_my_report_body(assessment_enroll_id, ts_id)
    explanation_link = {}
    for marking in markings:
        explanation_link[marking.question_no] = view_explanation(testset_id=ts_id, item_id=marking.item_id)

    # My Report : Footer - Candidate Avg Score / Total Avg Score by Item Category
    #                       'code_name as category', 'score', 'total_score', 'avg_score', 'percentile_score'
    # ToDo: ts_by_category unavailable until finalise all student's mark and calculate average data
    #       so it need to be discussed to branch out in "test analysed report"
    # ts_by_category = None
    ts_by_category = query_my_report_footer(assessment_id, student_user_id, assessment_enroll_id)

    if test_subject_string == 'Writing':
        marking_writing_id = 0
        url_i = url_for('writing.w_report', assessment_enroll_id=assessment_enroll_id,
                        student_user_id=student_user_id, marking_writing_id=marking_writing_id)
        return redirect(url_i)

    template_file = 'report/my_report.html'
    if pdf:
        template_file = 'report/my_report_pdf.html',

    rendered_template_pdf = render_template(template_file, assessment_name=assessment_name,
                                            subject=test_subject_string, rank=rank,
                                            score=score, markings=markings, ts_by_category=ts_by_category,
                                            student_user_id=student_user_id, static_folder=current_app.static_folder,
                                            pdf_url=pdf_url, grade=grade,
                                            explanation_link=explanation_link, test_type=test_type)
    if not pdf:
        return rendered_template_pdf
    # PDF download
    from weasyprint import HTML

    html = HTML(string=rendered_template_pdf)

    pdf_file_path = os.path.join(current_app.config['USER_DATA_FOLDER'],
                                 str(student_user_id),
                                 "report",
                                 "test_report_%s_%s_%s_%s.pdf" % (
                                     assessment_enroll_id, assessment_id, ts_id, student_user_id))

    os.chdir(os.path.join(current_app.config['USER_DATA_FOLDER']))
    if not os.path.exists(str(student_user_id)):
        os.makedirs(str(student_user_id))
    os.chdir(str(student_user_id))
    if not os.path.exists("report"):
        os.makedirs("report")

    html.write_pdf(target=pdf_file_path, presentational_hints=True)
    rsp = send_file(
        pdf_file_path,
        mimetype='application/pdf',
        as_attachment=True,
        attachment_filename=pdf_file_path)
    return rsp


@report.route('/student/set/<int:assessment_id>/<student_user_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def my_student_set_report(assessment_id, student_user_id):
    '''
     @report.route('/student/set/<int:assessment_id>/<int:student_user_id>', methods=['GET'])
     my_student_set_report() : Student Login > My Report > Student Report
        - Execute: Provide link to Student Report by assessment (all subject)
    '''
    # ToDO: Check accessbility to get Report
    # ToDo: when tester attempt to test multiple, the latest one will be taken for report
    latest_attempt_tests = db.session.query(AssessmentEnroll.assessment_id,
                                            AssessmentEnroll.testset_id,
                                            AssessmentEnroll.student_user_id,
                                            db.func.max(AssessmentEnroll.attempt_count).label("attempt_count")). \
        group_by(AssessmentEnroll.assessment_id,
                 AssessmentEnroll.testset_id,
                 AssessmentEnroll.student_user_id).subquery()
    assessment_enrolls = AssessmentEnroll.query.join(latest_attempt_tests,
                                                     AssessmentEnroll.assessment_id == latest_attempt_tests.c.assessment_id). \
        filter(AssessmentEnroll.testset_id == latest_attempt_tests.c.testset_id,
               AssessmentEnroll.student_user_id == latest_attempt_tests.c.student_user_id). \
        filter_by(assessment_id=assessment_id). \
        filter_by(student_user_id=student_user_id). \
        order_by(AssessmentEnroll.testset_id.asc(), AssessmentEnroll.attempt_count.desc()).all()

    web_file_path = None
    if assessment_enrolls:
        # ToDo: Decide which grade should be taken
        # grade = EducationPlanDetail.get_grade(assessment_id)
        # grade = assessment_enrolls[0].grade
        grade = Codebook.get_code_name(
            ((AssessmentHasTestset.query.filter_by(assessment_id=assessment_id).first()).testset).grade)

        assessment_GUID = assessment_enrolls[0].assessment_guid
        test_type_string = Codebook.get_code_name(assessment_enrolls[0].assessment.test_type)
        if test_type_string == 'Naplan':
            # Student Report : Generate image file for  Naplan student Report
            #                   saved into /static/report/naplan_result/naplan-*.png
            if grade == '-':
                return redirect(
                    url_for('report.list_my_report', error='No report generated due to lack of information - grade'))
            else:
                file_name = make_naplan_student_report(assessment_enrolls, assessment_id, student_user_id,
                                                       assessment_GUID, grade)
                if file_name is None:
                    url = request.referrer
                    flash('Marking data not available')
                    return redirect(url)
            web_file_path = url_for("api.get_naplan", student_user_id=student_user_id, file=file_name)
        else:
            # For selective test or other test type
            test_type_string = 'other'
        template_html_name = 'report/my_report_' + test_type_string + '.html'

        return render_template(template_html_name, image_file_path=web_file_path,
                               grade=grade, test_type=test_type_string,
                               student_user_id=student_user_id)
    else:
        return redirect(url_for('report.list_my_report', error='Report data not available'))


''' 
 @report.route('/manage', methods=['GET'])
 manage() : Report user Login > Report By Centre 
    - Search Report 
    - Provide link to Test Summary Report by test package (all assessments)
    - Provide link to Download: Test Summary report for all students    
    - Provide link to Test Ranking Report by assessment 
    - Provide link to Download: individual Subject Report for all students    
'''


@report.route('/manage', methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_READ)
def manage():
    test_type = request.args.get("test_type")
    test_center = request.args.get("test_center")
    year = request.args.get("year")
    if test_type or test_center or year:
        flag = True
    else:
        flag = False

    error = request.args.get("error")
    if error:
        flash(error)
    if test_type:
        test_type = int(test_type)
    if test_center:
        test_center = int(test_center)

    search_form = ReportSearchForm()
    if test_type is None:
        search_form.test_type.data = Codebook.get_code_id('Naplan')
    else:
        search_form.test_type.data = test_type
    search_form.test_center.data = test_center
    search_form.year.data = year
    rows, reports, students, testsets, test_summaries = [], [], [], [], []
    assessment_r_list = []
    if flag:
        #
        # By Assessment: Report List
        #
        query = Assessment.query.join(AssessmentEnroll, Assessment.id == AssessmentEnroll.assessment_id). \
            filter(AssessmentEnroll.start_time_client > datetime(int(year), 1, 1)). \
            filter(Assessment.test_type == test_type)
        # Query enroll data filter by test center
        # If test_center 'All', query all
        if Codebook.get_code_name(test_center) != 'All':
            query = query.filter(AssessmentEnroll.test_center == test_center)
        assessments = query.order_by(Assessment.id.asc()).all()

        all_subject_r_list = []
        for assessment in assessments:
            if Codebook.get_code_name(test_center) == 'All':
                assessment_enrolls = AssessmentEnroll.query.filter_by(assessment_id=assessment.id). \
                    order_by(AssessmentEnroll.testset_id.asc()).all()
            else:
                assessment_enrolls = AssessmentEnroll.query.filter_by(assessment_id=assessment.id). \
                    filter_by(test_center=test_center). \
                    order_by(AssessmentEnroll.testset_id.asc()).all()
            #
            # all_subjects data
            #
            all_subject_student_list = []
            for assessment_enroll in assessment_enrolls:
                all_subject_student_list.append(assessment_enroll.student_user_id)
                # if x!=0:)
            all_subject_student_list.sort()
            all_subject_student_list = list(set(all_subject_student_list))

            #
            # individual_subjects data
            #
            old_testset_id, testset_id = 0, 0
            testset_json_str = {}
            student_list = []
            testset_list = []
            for assessment_enroll in assessment_enrolls:
                testset_id = assessment_enroll.testset_id

                if old_testset_id != testset_id:
                    if old_testset_id > 0:
                        testset_json_str["students"] = student_list
                        testset_list.append(testset_json_str)
                        student_list = []
                        testset_json_str = []

                    old_testset_id = testset_id
                    testset_json_str = {"testset_id": testset_id}
                    student_list.append({"student_user_id": assessment_enroll.student_user_id,
                                         "assessment_enroll_id": assessment_enroll.id,
                                         "test_time": assessment_enroll.start_time_client})
                else:
                    # student_json_str = {"student_user_id": assessment_enroll.student_user_id,
                    #                     "assessment_enroll_id": assessment_enroll.id,
                    #                     "test_time": assessment_enroll.start_time_client}
                    student_list.append({"student_user_id": assessment_enroll.student_user_id,
                                         "assessment_enroll_id": assessment_enroll.id,
                                         "test_time": assessment_enroll.start_time_client})

            testset_json_str["students"] = student_list
            testset_list.append(testset_json_str)
            assessment_json_str = {"year": assessment.year,
                                   "assessment_id": assessment.id,
                                   "assessment_name": assessment.name,
                                   "test_type": assessment.test_type,
                                   "test_center": assessment.branch_id,
                                   "all_subject_student_list": all_subject_student_list,
                                   "testsets": testset_list}
            assessment_r_list.append(assessment_json_str)
        #
        # By Plan: Report List
        #
        # Query Report : 'plan_id', 'plan_name', 'assessment_year', 'grade', 'test_type','assessment_order',
        #                 'assessment_id', 'testset_id', 'assessment_enroll_id', 'student_user_id', 'attempt_count',
        #                 'test_center', 'start_time_client'
        rows = query_all_report_data(test_type, test_center, year)
        # Re-construct "Reports" with query result
        index = 0
        _testset_id, _test_center, _assessment_year, _assessment_order = 0, 0, 0, 0
        _assessment_id, _grade, _test_type = 0, 0, 0
        for row in rows:
            if index > 0 and \
                    (_testset_id != row.testset_id or row.assessment_enroll_id is None):
                testset_json_string = {"testset_id": _testset_id,
                                       "test_center": _test_center,
                                       "students": students
                                       }
                testsets.append(testset_json_string)
                if (_assessment_id != row.assessment_id):
                    json_string = {"assessment_year": _assessment_year,
                                   "grade": _grade,
                                   "test_type": _test_type,
                                   "assessment_order": _assessment_order,
                                   "assessment_id": _assessment_id,
                                   "testsets": testsets
                                   }
                    reports.append(json_string)
                    testsets = []
                students = []

            students.append({"student_user_id": row.student_user_id, "assessment_enroll_id": row.assessment_enroll_id})
            _assessment_year = row.assessment_year
            _grade = row.grade
            _test_type = row.test_type
            _assessment_order = row.assessment_order
            _assessment_id = row.assessment_id
            _testset_id = row.testset_id
            _test_center = row.test_center
            index += 1
        testset_json_string = {"testset_id": _testset_id,
                               "test_center": _test_center,
                               "students": students
                               }
        testsets.append(testset_json_string)
        json_string = {"assessment_year": _assessment_year,
                       "grade": _grade,
                       "test_type": _test_type,
                       "assessment_order": _assessment_order,
                       "assessment_id": _assessment_id,
                       "testsets": testsets
                       }
        reports.append(json_string)

        # Test Summary Report list for All Students: 'student_user_id','plan_id','plan_name',
        #                           'year','grade','test_type'
        test_summaries = query_individual_progress_summary_report_list()

    return render_template('report/manage.html', form=search_form, assessment_r_list=assessment_r_list, reports=reports,
                           test_summaries=test_summaries, test_center=test_center)


@report.route('/center', methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_READ)
def center():
    test_type = request.args.get("test_type")
    test_center = request.args.get("test_center")
    year = request.args.get("year")
    assessment = request.args.get("assessment")  # "assessment_id testset_id"
    if assessment is not None and assessment is not 0 and "_" in assessment:
        assessment_id = assessment.split("_")[0]
        testset_id = assessment.split("_")[1]
    else:
        assessment_id = 0
        testset_id = 0
    if test_type or test_center or year:
        flag = True
    else:
        flag = False

    error = request.args.get("error")
    if error:
        flash(error)
    if test_type:
        test_type = int(test_type)
    if test_center:
        test_center = int(test_center)

    search_form = ReportSearchForm()
    if test_type is None:
        search_form.test_type.data = Codebook.get_code_id('Naplan')
    else:
        search_form.test_type.data = test_type
    # default setting value into test_center list
    branch_id = current_user.get_branch_id()
    if branch_id and current_user.username != 'All':
        search_form.test_center.data = branch_id
    else:
        search_form.test_center.data = test_center
    search_form.year.data = year

    if assessment_id == 0:
        search_form.assessment.choices = []
        search_form.assessment.data = None
        return render_template('report/report_center.html', form=search_form, report_list='', columns_list='')

    assessments = search_assessment()
    assessments_codesets = []
    for d in assessments.json['data']:
        code = (str(d['assessment_id']) + '_' + str(d['testset_id']),
                d['assessment_name'] + ' : ' + d['testset_name'] + ' v.' + str(d['testset_version']))
        assessments_codesets.append(code)

    search_form.assessment.choices = assessments_codesets
    search_form.assessment.data = assessment

    # query = AssessmentEnroll.query.filter_by(assessment_id=assessment_id). \
    #    filter_by(testset_id=testset_id)

    assessment_name = Assessment.query.filter_by(id=assessment_id).first().name

    add_query_str = ''
    # Query current_user's test center
    # If test_center 'All', query all
    # If test_center 'Administrator', query all
    if not current_user.is_administrator() and \
            (current_user.username != 'All' and current_user.get_branch_id() != test_center):
        query = query.filter(1 == 0)
        # new_query = query.filter(1 == 0)
        flash("Forbidden branch data!")
    else:
        if Codebook.get_code_name(test_center) != 'All':
            # query = query.filter(AssessmentEnroll.test_center == test_center)
            s_branch = Codebook.query.filter_by(id=test_center).first()
            campus_prefix = s_branch.additional_info['campus_prefix']
            add_query_str = " and s.branch=\'\'" + str(campus_prefix) + "\'\' "

    t_items = AssessmentHasTestset.query.filter_by(assessment_id=assessment_id).all()
    testset_name_list = ''
    columns_query = ''
    columns_list = []
    testset_dic = {}
    t_items_count = 0
    for i in t_items:
        i_testset = Testset.query.filter_by(id=i.testset_id).first()
        i_testset_name = i_testset.name + ' (Ranking)'
        testset_name_list += '\"' + i_testset.name + '\"'
        columns_query += '\"' + i_testset_name + '\" VARCHAR'
        columns_list.append(i_testset_name)
        testset_dic[i_testset.id] = {"name": i_testset_name, "subject": Codebook.get_code_name(i_testset.subject)}
        # testset_list[t_items_count]['id'] = i_testset.id
        t_items_count = t_items_count + 1
        if len(t_items) > t_items_count:
            testset_name_list += ','
            columns_query += ','

    '''
    codebook.code_type = test_type 
    Naplan, OC, Selective, Naplan-P, Homework, V_Y5 Scholarshop, V_Y7 Scholarship, V_Selective
    Online OC, Summative test, Entry Test, Holiday OC, Extra OC, Selective Lesson, 
    Preliminary Selective, Selective Sample
    '''
    score_query = '{' + testset_name_list + '}'  # candidate score by testset

    # tuning
    '''
    new_query = text("SELECT  * FROM CROSSTAB \
        ('select s.student_id, s.user_id, u.username, s.branch, ae.test_center, a2.name, \
        a2.id,t2.name, \
        CONCAT( CASE WHEN sum(m.outcome_score) <> 0 THEN round(sum(m.candidate_mark)/sum(m.outcome_score) * 100) \
        ELSE 0 END, ''('', Max(ts.rank_v), '')'')  score \
        from marking m \
        join assessment_enroll ae ON m.assessment_enroll_id = ae.id \
        join student s on ae.student_user_id = s.user_id \
        join users u on s.user_id = u.id \
        join assessment a2 on ae.assessment_id = a2.id \
        join assessment_testsets at2 on a2.id = at2.assessment_id \
        join testset t2 on ae.testset_id = t2.id \
        join codebook c2 on t2.subject = c2.id and c2.code_type = \'\'subject\'\' \
        join test_summary_mview ts on m.assessment_enroll_id= ts.assessment_enroll_id   \
        where a2.name = \'\'" + assessment_name + "\'\'" + add_query_str + " \
        group by s.student_id, s.user_id, u.username, a2.name, a2.id, s.branch, ae.test_center, \
        t2.name \
        order by s.student_id',\
        $$SELECT unnest(\'" + score_query + "\'::varchar[])$$) \
        AS ct(student_id VARCHAR ,user_id VARCHAR, username VARCHAR, branch VARCHAR, test_center VARCHAR, \
        assessment_name VARCHAR, assessment_id integer, \
        " + columns_query + ");")
    '''

    '''
    new_query = text("SELECT  * FROM CROSSTAB \
        ('select s.student_id, s.user_id, u.username, s.branch, ae.test_center, a2.name, \
        a2.id,t2.name, \
        CONCAT( CASE WHEN sum(m.outcome_score) <> 0 THEN round(sum(m.candidate_mark)/sum(m.outcome_score) * 100) \
        ELSE 0 END, ''('', (select Max(rank_v) from test_summary_mview where assessment_enroll_id = max(m.assessment_enroll_id)), '')'')  score \
        from marking m \
        join assessment_enroll ae ON m.assessment_enroll_id = ae.id \
        join student s on ae.student_user_id = s.user_id \
        join users u on s.user_id = u.id \
        join assessment a2 on ae.assessment_id = a2.id \
        join assessment_testsets at2 on a2.id = at2.assessment_id \
        join testset t2 on ae.testset_id = t2.id \
        join codebook c2 on t2.subject = c2.id and c2.code_type = \'\'subject\'\' \
        where a2.name = \'\'" + assessment_name + "\'\'" + add_query_str + " \
        group by s.student_id, s.user_id, u.username, a2.name, a2.id, s.branch, ae.test_center, \
        t2.name \
        order by s.student_id',\
        $$SELECT unnest(\'" + score_query + "\'::varchar[])$$) \
        AS ct(student_id VARCHAR ,user_id VARCHAR, username VARCHAR, branch VARCHAR, test_center VARCHAR, \
        assessment_name VARCHAR, assessment_id integer, \
        " + columns_query + ");")
    '''

    # if homework, only data in 4months because the assessment used again and again every year.
    if str(test_type) == '307':
        add_query_str = add_query_str + " and ae.start_time >= NOW()::DATE - 120 "

    '''
    new_query = text("SELECT  * FROM CROSSTAB \
        ('select s.student_id, s.user_id, u.username, s.branch, ae.test_center, a2.name, \
        a2.id,t2.name, \
        CONCAT( CASE WHEN sum(m.outcome_score) <> 0 THEN round(sum(m.candidate_mark)/sum(m.outcome_score) * 100) \
        ELSE 0 END, ''('', (select Max(rank_v) from test_summary_mview where assessment_enroll_id = max(m.assessment_enroll_id)), '')'')  score \
        from marking m \
        join assessment_enroll ae ON m.assessment_enroll_id = ae.id \
        join student s on ae.student_user_id = s.user_id \
        join users u on s.user_id = u.id \
        join assessment a2 on ae.assessment_id = a2.id \
        join assessment_testsets at2 on a2.id = at2.assessment_id \
        join testset t2 on ae.testset_id = t2.id \
        join codebook c2 on t2.subject = c2.id and c2.code_type = \'\'subject\'\' \
        where a2.id = " + assessment_id + " " + add_query_str + " \
        group by s.student_id, s.user_id, u.username, a2.name, a2.id, s.branch, ae.test_center, \
        t2.name \
        order by s.student_id',\
        $$SELECT unnest(\'" + score_query + "\'::varchar[])$$) \
        AS ct(student_id VARCHAR ,user_id VARCHAR, username VARCHAR, branch VARCHAR, test_center VARCHAR, \
        assessment_name VARCHAR, assessment_id integer, \
        " + columns_query + ");")
    '''

    new_query = text("SELECT  * FROM CROSSTAB \
        ('select s.student_id, s.user_id, u.username, s.branch, ae.test_center, a2.name, \
        a2.id,t2.name, \
        CONCAT( CASE WHEN MAX(ae.total_score) is null or MAX(ae.total_score)=0 then 0 else round((MAX(ae.score)/MAX(ae.total_score)) * 100) end,  \
        ''('', (select rnk from (select id, RANK () OVER (order by score desc) as rnk from assessment_enroll where assessment_id = a2.id and testset_id = max(t2.id)) tt \
	    where id = max(ae.id)), '')'') as score \
        from  (select * from assessment where id = " + assessment_id + ") a2 \
        join assessment_enroll ae ON a2.id = ae.assessment_id \
        join student s on ae.student_user_id = s.user_id \
        join users u on s.user_id = u.id \
        join testset t2 on ae.testset_id = t2.id \
        where 1 = 1 " + add_query_str + " \
        group by s.student_id, s.user_id, u.username, a2.name, a2.id, s.branch, ae.test_center, \
        t2.name \
        order by s.student_id',\
        $$SELECT unnest(\'" + score_query + "\'::varchar[])$$) \
        AS ct(student_id VARCHAR ,user_id VARCHAR, username VARCHAR, branch VARCHAR, test_center VARCHAR, \
        assessment_name VARCHAR, assessment_id integer, \
        " + columns_query + ");")

    cursor = db.session.execute(new_query)
    report_list = list(cursor.fetchall())

    if int(testset_id) > 0:
        testset = Testset.query.with_entities(Testset.subject, Testset.grade, Testset.branching).filter_by(
            id=testset_id).first()
        branching = testset.branching.get("data")
        testlet_id = branching[0].get("id")
        # testlet_id = 426
        review_items = TestletHasItem.query.filter_by(testlet_id=testlet_id).order_by(TestletHasItem.order.asc()).all()
        # flash(review_items)

    # for tsset in testset_dic:
    #    log.debug("testset_dic tsset: %s , %s " % (testset_dic[tsset]["name"], testset_dic[tsset]["subject"]))
    '''
    for enroll in enrolls:
        # If subject is 'Writing', report enabled:
        #   - True when Marker's comment existing for 'ALL' items in Testset
        #   - False when Marker's comment not existing
        enroll.enable_writing_report = False
        enroll.is_writing = False
        subject = Codebook.get_code_name(enroll.testset.subject)
        if subject == 'Writing':
            enroll.is_writing = True
            mws = db.session.query(MarkingForWriting.markers_comment).join(Marking). \
                filter(Marking.id == MarkingForWriting.marking_id). \
                filter(Marking.assessment_enroll_id == enroll.id).all()
            for mw in mws:
                enroll.enable_writing_report = True if mw.markers_comment else False
                if not enroll.enable_writing_report:
                    break
    '''
    return render_template('report/report_center.html', form=search_form, report_list=report_list, \
                           columns_list=columns_list, testset_dic=testset_dic, review_items=review_items, \
                           test_type=test_type, assessment=assessment)


@report.route('/center_old', methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_READ)
def center_old():
    test_type = request.args.get("test_type")
    test_center = request.args.get("test_center")
    year = request.args.get("year")
    assessment = request.args.get("assessment")  # "assessment_id testset_id"
    if assessment:
        assessment_id = assessment.split("_")[0]
        testset_id = assessment.split("_")[1]
    else:
        assessment_id = 0
        testset_id = 0
    if test_type or test_center or year:
        flag = True
    else:
        flag = False

    error = request.args.get("error")
    if error:
        flash(error)
    if test_type:
        test_type = int(test_type)
    if test_center:
        test_center = int(test_center)

    search_form = ReportSearchForm()
    if test_type is None:
        search_form.test_type.data = Codebook.get_code_id('Naplan')
    else:
        search_form.test_type.data = test_type
    # default setting value into test_center list
    branch_id = current_user.get_branch_id()
    if branch_id:
        search_form.test_center.data = branch_id
    else:
        search_form.test_center.data = test_center
    search_form.year.data = year

    query = AssessmentEnroll.query.filter_by(assessment_id=assessment_id). \
        filter_by(testset_id=testset_id)
    # Query current_user's test center
    # If test_center 'All', query all
    # If test_center 'Administrator', query all
    if not current_user.is_administrator() and \
            current_user.get_branch_id() != test_center:
        query = query.filter(1 == 0)
        flash("Forbidden branch data!")
    else:
        if Codebook.get_code_name(test_center) != 'All':
            query = query.filter(AssessmentEnroll.test_center == test_center)
    enrolls = query.order_by(AssessmentEnroll.student_user_id.asc()).all()

    for enroll in enrolls:
        # If subject is 'Writing', report enabled:
        #   - True when Marker's comment existing for 'ALL' items in Testset
        #   - False when Marker's comment not existing
        enroll.enable_writing_report = False
        enroll.is_writing = False
        subject = Codebook.get_code_name(enroll.testset.subject)
        if subject == 'Writing':
            enroll.is_writing = True
            mws = db.session.query(MarkingForWriting.markers_comment).join(Marking). \
                filter(Marking.id == MarkingForWriting.marking_id). \
                filter(Marking.assessment_enroll_id == enroll.id).all()
            for mw in mws:
                enroll.enable_writing_report = True if mw.markers_comment else False
                if not enroll.enable_writing_report:
                    break

    return render_template('report/report_center_old.html', form=search_form, enrolls=enrolls)


@report.route('/test_ranking/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:test_center>',
              methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_READ)
def test_ranking_report(year, test_type, sequence, assessment_id, test_center):
    '''
     @report.route('/test_ranking/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:test_center>',
                  methods=['GET'])
     test_ranking_report() : Report user Login > Report By Centre > Search
        - Execute: Provide link to Test Ranking Report by assessment
    '''

    # Test Ranking Report - subject list : 'testset_id', 'subject_name'
    subjects = query_test_ranking_subject_list(assessment_id)

    # rank students from all test candidates
    #            data : 'student_user_id', 'cs_student_id', 'student_name', 'assessment_id',
    #            'test_center', 'subject_1', 'subject_2', 'subject_3', 'total_mark', 'student_rank'
    rows = query_test_ranking_data(subjects, assessment_id)

    # pop rows to list up only students by test_center
    # If user has role 'admin' or 'moderator', can see all candidates rank
    i = 0
    test_summaries = []
    for r in rows:
        if current_user.role.name == 'Administrator' or current_user.role.name == 'Moderator':
            test_summaries = rows
            break
        if r.test_center == test_center:
            test_summaries.append(r)
    assessment_name = (Assessment.query.with_entities(Assessment.name).filter_by(id=assessment_id).first()).name

    template_file = 'report/test_result_' + Codebook.get_code_name(test_type) + '.html'
    if request.args.get('pdf-download') == "1":
        template_file = 'report/test_result_' + Codebook.get_code_name(test_type) + '_pdf.html'
    rendered_template_pdf = render_template(template_file,
                                            year=year, test_type=test_type, sequence=sequence,
                                            assessment_name=assessment_name, subject_names=subjects,
                                            test_summaries=test_summaries, now=datetime.utcnow(),
                                            static_folder=current_app.static_folder)

    if request.args.get('pdf-download') == "1":
        from weasyprint import HTML
        html = HTML(string=rendered_template_pdf)
        pdf_file_path = os.path.join(current_app.config['USER_DATA_FOLDER'],
                                     str(current_user.id),
                                     "test_ranking",
                                     "%s_%s.pdf" % (assessment_id, sequence))
        html.write_pdf(target=pdf_file_path, presentational_hints=True)
        rsp = send_file(
            pdf_file_path,
            mimetype='application/pdf',
            as_attachment=True,
            attachment_filename=pdf_file_path)
        return rsp
    if request.args.get('excel-download') == "1":
        rsp = build_test_ranking_excel_response(subjects, test_summaries, year, test_type, sequence)
        return rsp
    return rendered_template_pdf


''' 
 @report.route('/summary/<int:plan_id>/<int:branch_id>', methods=['GET'])
 summary_report() : Report user Login > Report By Centre > Search
    - Execute: Provide link to Download: individual Subject Report for all students 
'''


@report.route('/summary/<int:plan_id>/<int:branch_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def summary_report(plan_id, branch_id):
    plan_GUID, test_type_string, grade = '', '', ''
    assessment_ids = [row.assessment_id for row in EducationPlanDetail.query.filter_by(plan_id=plan_id).all()]
    query = db.session.query(AssessmentEnroll.student_user_id).distinct()
    # Todo: Need to check if current_user have access right on queried data
    test_center = Codebook.get_testcenter_of_current_user()
    # Remove: "not test_center" because of 'admin' user has already registered to test_center 'Castle Hill'
    # if not test_center and (current_user.role.name == 'Moderator' or current_user.role.name == 'Administrator'):
    if (current_user.role.name == 'Moderator' or current_user.role.name == 'Administrator'):
        test_center = Codebook.query.filter_by(code_type='test_center').filter_by(code_name='All').first()
    if (test_center.id == branch_id):
        if not (test_center.code_name == 'All'):
            query = query.filter(AssessmentEnroll.test_center == branch_id)
        query = query.filter(AssessmentEnroll.assessment_id.in_(assessment_ids))
        enrolled_students = query.all()
        for enrolled_student in enrolled_students:
            student_user_id = enrolled_student.student_user_id
            plan_GUID = individual_progress_summary_report(plan_id, student_user_id)
            if plan_GUID is None:
                return redirect(url_for('report.manage', error='Error during generating pdf files'))
        rsp = build_individual_progress_zipper(plan_GUID)
        return rsp
    else:
        return 'Invalid Request: No data for current user'


def individual_progress_summary_report(plan_id, student_user_id):
    plan_GUID = (EducationPlan.query.filter_by(id=plan_id).first()).GUID
    # ##
    # Header - 'year', 'grade', 'test_type'
    ts_header = query_individual_progress_summary_report_header(plan_id)
    test_type_string = Codebook.get_code_name(ts_header.test_type)
    if test_type_string != 'Naplan':
        test_type_string = 'other'
    # ##
    # Body - Summary Report by assessment/test - 'p.plan_id', 'p."order"', 'p.assessment_id',
    #                     'p.student_user_id', 'my_set_score', 'p.rank_v', 'avg_set_score'
    #        Summary Report by plan - 'p.plan_id', 'p."order"', 'p.assessment_id',
    #                     'p.testset_id', 'ts.student_user_id', 'score', 'total_score'
    #                     'avg_score', 'percentile_score', 'rank_v', 'total_students'
    # ##
    # Construct 'my_assessment' - 'my_testset' which are displayed as individual subject score on report
    rows_all = query_individual_progress_summary_report_by_assessment(plan_id, student_user_id)
    rows = query_individual_progress_summary_report_by_plan(plan_id, student_user_id)

    my_assessment, my_subject_score, avg_subject_score = [], [], []  # my_score by subject, avg_score
    my_set_score, my_set_rank, avg_set_score = [], [], []
    assessment_order_index = 1
    for ts in rows:
        if assessment_order_index != ts.order:
            ts_all = rows_all[assessment_order_index - 1]
            # set values into my_assessment detail, sum of set score
            my_assessment.append(my_subject_score)
            my_set_score.append(float(ts_all.my_set_score))
            my_set_rank.append(ts_all.rank_v)
            avg_set_score.append(float(ts_all.avg_set_score))
            # initialization of temporary variable
            my_subject_score = []
            assessment_order_index = ts.order
        my_subject_score.append({'subject': ts.testset_id, 'my_score': ts.percentile_score})
        avg_subject_score.append(ts.avg_score)
    if len(my_subject_score) != 0:
        my_assessment.append(my_subject_score)
        my_set_score.append(float(rows_all[len(rows_all) - 1].my_set_score))
        my_set_rank.append(rows_all[len(rows_all) - 1].rank_v)
        avg_set_score.append(float(rows_all[len(rows_all) - 1].avg_set_score))

    # #
    # re-construct data "subjects" to display properly on the template html page
    subject_names, subject_score_by_assessment, subjects = [], [], []
    num_of_subjects = 0
    num_of_assessments = len(my_assessment)
    for _assessment in my_assessment:
        for _subject in _assessment:
            subject_names.append(Codebook.get_subject_name(_subject.get('subject')))
            subject_names.append(Codebook.get_subject_name(_subject.get('subject')) + ' Average')
            num_of_subjects += 1
        break
    # subjects : subject_1_score - subject_1_avg - subject_2_score - subject_2_avg ....
    for i in range(0, num_of_subjects):
        for j in range(0, num_of_assessments):
            my_score_obj = my_assessment[j][i]
            subject_score_by_assessment.append(my_score_obj.get('my_score'))
        subjects.insert(i, subject_score_by_assessment)
        subject_score_by_assessment = []
    for i in range(0, num_of_subjects):
        subject_avg_score_by_assessment = []
        subject_avg_score_by_assessment.append(avg_subject_score[i])
        # subject_avg_score_by_assessment.append(avg_subject_score[i + num_of_subjects])
        subjects.insert(i * 2 + 1, subject_avg_score_by_assessment)

    # ##
    # Graph - Summary Report by subject( 학생이 친 시험 과목별 평균점수, rank, 최저점, 최고점 )
    #               'plan_id', 'testset_id', 'student_user_id', 'rank_v', 'subject_avg_my_score',
    #               'subject_avg_avg_score', 'subject_avg_min_score', 'subject_avg_max_score'
    #         Summary Report by plan( 학생이 친 시험 전체(plan package단위) 점수, rank, 최저점, 최고점 )
    #               'plan_id', 'student_user_id', 'rank_v', 'sum_my_score',
    #               'sum_avg_score', 'sum_min_score', 'sum_max_score'
    # ##
    total_subject_scores = query_individual_progress_summary_by_subject_v(plan_id, student_user_id)
    total_score = query_individual_progress_summary_by_plan_v(plan_id, student_user_id, num_of_assessments)

    # #
    # re-construct data "score_summaries" to display properly on the template html page
    score_summaries = []
    index = 0
    for s in total_subject_scores:
        _my_score = s.subject_avg_my_score
        _avg = s.subject_avg_avg_score
        _min = s.subject_avg_min_score
        _max = s.subject_avg_max_score
        _rank = s.rank_v
        _subject_name = Codebook.get_subject_name(s.testset_id)
        avg_score_summary = {"subject": _subject_name,
                             "total_score": 100,
                             "my_score_range": _my_score,
                             "my_avg_range": _avg,
                             "my_score": _my_score,
                             "average": _avg,
                             "min": _min,
                             "max": _max,
                             "rank": _rank}
        score_summaries.append(avg_score_summary)
        index += 1
    score_summaries.append({"subject": 'Total',
                            "total_score": 100,
                            "my_score_range": str(float(total_score.sum_my_score) / num_of_assessments),
                            "my_avg_range": str(float(total_score.sum_avg_score) / num_of_assessments),
                            "my_score": total_score.sum_my_score,
                            "average": total_score.sum_avg_score,
                            "min": total_score.sum_min_score,
                            "max": total_score.sum_max_score,
                            "rank": total_score.rank_v})

    plan_GUID = (EducationPlan.query.filter_by(id=plan_id).first()).GUID
    by_subject_file_name = draw_individual_progress_by_subject(score_summaries, plan_GUID, student_user_id)
    by_set_file_name = draw_individual_progress_by_set(my_set_score, avg_set_score, plan_GUID, student_user_id)

    template_file_name = 'report/individual_progress_' + test_type_string + '_pdf.html'
    naplan_folder = os.path.join(current_app.config['USER_DATA_FOLDER'], str(current_user.id), "naplan")

    logo_web_path = os.path.join(current_app.config['CSEDU_IMG_DIR'].lstrip('app'), 'CSEducation.png')
    logo_local_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                            current_app.config['CSEDU_IMG_DIR'],
                                            'CSEducation.png')
    by_subject_web_path = url_for("api.get_naplan", student_user_id=student_user_id, file=by_subject_file_name)
    by_subject_local_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                                  naplan_folder,
                                                  by_subject_file_name)
    by_set_web_path = url_for("api.get_naplan", student_user_id=student_user_id, file=by_set_file_name)
    by_set_local_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                              naplan_folder,
                                              by_set_file_name)

    success = build_individual_progress_pdf_response(template_file_name, static_folder=current_app.static_folder,
                                                     by_subject_file_name=by_subject_local_path,
                                                     by_set_file_name=by_set_local_path,
                                                     ts_header=ts_header,
                                                     num_of_assessments=num_of_assessments,
                                                     num_of_subjects=num_of_subjects,
                                                     subject_names=subject_names,
                                                     subjects=subjects, my_set_score=my_set_score,
                                                     avg_set_score=avg_set_score, my_set_rank=my_set_rank,
                                                     score_summaries=score_summaries, plan_id=plan_id,
                                                     plan_GUID=plan_GUID, student_user_id=student_user_id)

    if success != 'success':
        return None  # plan_GUID
    return plan_GUID


''' 
 @report.route('/results/pdf/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:branch_id>',
              methods=['GET'])
 report_results_pdf() : Report user Login > Report By Centre 
    - Execute: Provide link to Download: Test Summary report for all students    
'''


@report.route('/results/pdf/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:branch_id>',
              methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_READ)
def report_results_pdf(year, test_type, sequence, assessment_id, branch_id):
    # ##
    # Get Assessment Enrolled Students list "enrolled_students" enrolled at test_center
    # If students, Get Assessment general information for report
    assessment_GUID, test_type_string, grade = '', '', ''
    query = db.session.query(AssessmentEnroll.student_user_id).distinct()
    # Todo: Need to check if current_user have access right on queried data
    test_center = Codebook.get_testcenter_of_current_user()
    # Remove: condition "not test_center" because of 'admin' user has already registered to test_center 'Castle Hill'
    # if not test_center and (current_user.role.name == 'Moderator' or current_user.role.name == 'Administrator'):
    if (current_user.role.name == 'Moderator' or current_user.role.name == 'Administrator'):
        test_center = Codebook.query.filter_by(code_type='test_center').filter_by(code_name='All').first()
    if (test_center.id == branch_id):
        if not (test_center.code_name == 'All'):
            query = query.filter(AssessmentEnroll.test_center == branch_id)
        query = query.filter(AssessmentEnroll.assessment_id == assessment_id)
        enrolled_students = query.all()
        if enrolled_students:
            assessment = db.session.query(Assessment.GUID, Assessment.test_type).filter(
                Assessment.id == assessment_id).first()
            assessment_GUID = assessment.GUID
            test_type_string = Codebook.get_code_name(assessment.test_type)
            grade = EducationPlanDetail.get_grade(assessment_id)
        else:
            return redirect(url_for('report.manage', error='Not found enroll data'))

        for enrolled_student in enrolled_students:
            student_user_id = enrolled_student.student_user_id
            enrollment = AssessmentEnroll.query.filter_by(assessment_id=assessment_id).filter_by(
                student_user_id=student_user_id).all()
            if enrollment:
                if test_type_string == 'Naplan':
                    # Student Report : Generate image file for  Naplan student Report
                    #                   saved into /static/report/naplan_result/naplan-*.png
                    file_name = make_naplan_student_report(enrollment, assessment_id, student_user_id, assessment_GUID,
                                                           grade)

                else:
                    # For selective test or other test type
                    test_type_string = 'other'
                template_file_name = 'report/my_report_' + test_type_string + '.html'
                naplan_folder = os.path.join(current_app.config['USER_DATA_FOLDER'], str(current_user.id), "naplan")

                local_file_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                                        naplan_folder,
                                                        file_name)
                success = build_test_results_pdf_response(template_file_name, image_file_path=local_file_path,
                                                          assessment_GUID=assessment_GUID,
                                                          student_user_id=student_user_id)
                if success != 'success':
                    return redirect(url_for('report.manage', error='Error during generating pdf files'))
            else:
                return redirect(url_for('report.manage', error='Not found enroll data'))

        rsp = build_test_results_zipper(assessment_GUID)
        return rsp
    else:
        return 'Invalid Request: No data for current user'


''' 
 @report.route('/score_summary', methods=['GET'])
 score_summary_list() : Report user Login > Item Score Summary
    - Provide link to Item Runner
    - Provide link to Item Score  
'''


@report.route('/score_summary', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_MANAGE)
def score_summary_list():
    grade = request.args.get("grade")
    subject = request.args.get("subject")
    level = request.args.get("level")
    category = request.args.get("category")
    subcategory = request.args.get("subcategory")
    active_str = request.args.get("active")
    if grade or subject or level or category or subcategory or active_str:
        grade = int(grade)
        subject = int(subject)
        level = int(level)
        category = int(category)
        subcategory = int(subcategory)
        if active_str == 'y':
            active = True
        else:
            active = False
        flag = True
    else:
        active = True
        flag = False
    error = request.args.get("error")
    if error:
        flash(error)

    items = []
    search_form = ItemSearchForm()
    search_form.grade.data = grade
    search_form.subject.data = subject
    search_form.level.data = level
    search_form.category.data = category
    search_form.subcategory.data = subcategory
    search_form.active.data = active
    query = Item.query
    if flag:
        if search_form.grade.data:
            query = query.filter_by(grade=search_form.grade.data)
        if search_form.subject.data:
            query = query.filter_by(subject=search_form.subject.data)
        if search_form.level.data:
            query = query.filter_by(level=search_form.level.data)
        if search_form.category.data:
            query = query.filter_by(category=search_form.category.data)
        if search_form.subcategory.data:
            query = query.filter_by(subcategory=search_form.subcategory.data)
        if search_form.active.data:
            query = query.filter_by(active=search_form.active.data)
        marked_id_list = [r.item_id for r in db.session.query(Marking.item_id).distinct()]
        items = query.filter(Item.id.in_(marked_id_list)).order_by(Item.id.desc()).all()
        flash('Found {} item(s)'.format(len(items)))
    return render_template('report/score_summary_list.html', form=search_form, items=items)


''' 
 @report.route('/score_summary/<int:item_id>', methods=['GET'])
 score_summary() : Report user Login > Item Score Summary
    - Execute: Provide link to Item Score  
'''


@report.route('/score_summary/<int:item_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_MANAGE)
def score_summary(item_id):
    rows = query_item_score_summary_data(item_id)
    by_assessment = []
    by_item = None
    for row in rows:
        # rows data grouping : 'by_item_assessment', 'by_item'
        if row.grouping == 'by_item':
            by_item = row
        elif row.grouping == 'by_item_assessment':
            by_assessment.append(row)
    item = Item.query.filter_by(id=item_id).first()
    return render_template('report/score_summary.html', by_item=by_item, by_assessment=by_assessment, item=item)


@report.route('/report_test/<string:type>', methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_READ)
def report_test(type):
    '''
        Report Test
    '''
    from weasyprint import HTML
    if type == 'individual_progress_report':
        template_file = 'report/individual_progress_Naplan_pdf_test.html'
        rendered_template_pdf = render_template(template_file)

        html = HTML(string=rendered_template_pdf)

        pdf_file_path = os.path.join(current_app.config['USER_DATA_FOLDER'],
                                     "report_test",
                                     "individual_progress_Naplan_pdf_test.pdf")
    elif type == 'test_ranking':
        template_file = 'report/test_result_Naplan_pdf_test.html'
        rendered_template_pdf = render_template(template_file)

        html = HTML(string=rendered_template_pdf)

        pdf_file_path = os.path.join(current_app.config['USER_DATA_FOLDER'],
                                     "report_test",
                                     "test_ranking_pdf_test.pdf")
    else:
        return 'Unknown report type'
    html.write_pdf(target=pdf_file_path, presentational_hints=True)
    rsp = send_file(
        pdf_file_path,
        mimetype='application/pdf',
        as_attachment=True,
        attachment_filename=pdf_file_path)
    return rsp


@report.route('/enroll_info/', methods=['GET'])
@permission_required(Permission.ADMIN)
def enroll_info():
    search_date = request.args.get('search_date')
    search_student_id = request.args.get('search_student_id')
    query = db.session.query(AssessmentEnroll)
    if search_student_id:
        student_user_ids = [row.id for row in
                            User.query.filter(User.username.ilike('%{}%'.format(search_student_id))).all()]
        query = query.filter(AssessmentEnroll.student_user_id.in_(student_user_ids))
    if not search_student_id and not search_date:
        query = query.filter(1 == 2)
    elif search_date:
        query = query.filter(func.date(AssessmentEnroll.start_time) == search_date)

    # todays_datetime = datetime(datetime.today().year, datetime.today().month, datetime.today().day)
    # query.filter(AssessmentEnroll.start_time >= todays_datetime)

    if search_date:
        enrolls = query.order_by(AssessmentEnroll.id.desc()).all()
        '''
        enrolls = query.order_by(AssessmentEnroll.assessment_id, AssessmentEnroll.testset_id,
                                 AssessmentEnroll.student_user_id).all()
        '''
    else:
        enrolls = query.order_by(AssessmentEnroll.id.desc()).limit(50).all()
    # Default set date as today
    if not search_student_id and not search_date:
        search_date = date.today().strftime('%Y-%m-%d')

    return render_template('report/assessment_enroll_info.html', enrolls=enrolls, search_date=search_date)


@report.route('/marking_info/<int:id>', methods=['GET'])
@permission_required(Permission.ADMIN)
def marking_info(id):
    enroll = AssessmentEnroll.query.filter_by(id=id).first()
    markings = Marking.query.filter_by(assessment_enroll_id=id). \
        order_by(Marking.question_no).all()

    return render_template('report/marking_info.html', markings=markings, enroll=enroll)


@report.route('/test_results', methods=['GET'])
@permission_required(Permission.ADMIN)
def test_results():
    return render_template('report/test_results.html', year=Choices.get_ty_choices())


@report.route('/test_results_plans', methods=['POST'])
@permission_required(Permission.ADMIN)
def test_results_plans():
    year = request.json.get('year')
    rows = [], []
    plan = EducationPlan.query.filter_by(year=year).order_by(EducationPlan.id.desc()).all()
    if plan is not None:
        rows = [(p.id, p.name) for p in plan]
    return jsonify(rows)


@report.route('/test_results', methods=['POST'])
@permission_required(Permission.ADMIN)
def test_results_post():
    p_year = request.json.get('year')
    p_plan_id = int(request.json.get('type'))
    p_test_detail = request.json.get('detail')
    rows = [], []

    sql_stmt_sub = 'SELECT * FROM test_results(:p_year, :p_plan_id, :p_test_detail)'
    cursor = db.session.execute(sql_stmt_sub,
                                {'p_year': p_year, 'p_plan_id': p_plan_id, 'p_test_detail': p_test_detail})
    if cursor is not None:
        rows = [(r.student_user_id, r.username, r.subject_name1, r.subject_name2,
                 r.subject_name3, r.subject_name4, r.subject_name5, r.subject_name6,
                 r.subject_name7, r.subject_name8, r.subject_name9, r.subject_name10,
                 r.total, r.ranking, r.branchname
                 ) for r in cursor.fetchall()]

    return jsonify(rows)


@report.route('/test_results_detail', methods=['POST'])
@permission_required(Permission.ADMIN)
def test_results_detail():
    plan = request.json.get('plan')
    rows = [], []

    sql_stmt_sub = 'SELECT test_detail FROM assessment a WHERE id in( ' \
                   'SELECT assessment_id FROM education_plan_details aa WHERE plan_id = :plan_id) ' \
                   'GROUP BY test_detail ORDER BY test_detail'
    cursor = db.session.execute(sql_stmt_sub, {'plan_id': plan})
    if cursor is not None:
        rows = [(r.test_detail) for r in cursor.fetchall()]

    return jsonify(rows)
