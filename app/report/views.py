import os
from collections import namedtuple
from datetime import datetime

from flask import render_template, flash, request, current_app, redirect, url_for
from flask_login import login_required, current_user

from . import report
from .forms import ReportSearchForm, ItemSearchForm
from .. import db
from ..api.reports import draw_report, query_my_report_list_v, query_my_report_header, query_my_report_body, \
    query_my_report_footer, make_naplan_student_report, query_all_report_data, query_individual_progress_summary_report_list, \
    query_test_ranking_subject_list, query_test_ranking_data, build_test_ranking_excel_response,\
    query_item_score_summary_data, query_individual_progress_summary_report_header, \
    query_individual_progress_summary_report_by_assessment, query_individual_progress_summary_report_by_plan, \
    query_individual_progress_summary_by_subject_v, query_individual_progress_summary_by_plan_v, \
    build_test_ranking_pdf_response, build_test_results_pdf_response, build_test_results_zipper, \
    build_individual_progress_pdf_response, build_individual_progress_zipper, \
    draw_individual_progress_by_subject, draw_individual_progress_by_set
from ..decorators import permission_required
from ..models import Codebook, Permission, AssessmentEnroll, Assessment, EducationPlanDetail, \
    refresh_mviews, Item, Marking, EducationPlan

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
    student_id = current_user.id
    error = request.args.get("error")
    if error:
        flash(error)

    # My Report List : 'id', 'assessment_id', 'student_id', 'year', 'test_type', 'name', 'branch_id',
    #                'subject_1', 'subject_2', 'subject_3', 'subject_4', 'subject_5'
    rows = query_my_report_list_v(student_id)
    return render_template("report/my_report_list.html", assessment_enrolls=rows)


''' 
 @report.route('/ts/<int:assessment_id>/<int:ts_id>/<int:student_id>', methods=['GET'])
 my_report() : Student Login > My Report > Report 
    - Execute: Provide link to Subject Report 
'''
@report.route('/ts/<int:assessment_id>/<int:ts_id>/<int:student_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def my_report(assessment_id, ts_id, student_id):
    # Todo: Check accessibility to get report
    refresh_mviews()
    row = AssessmentEnroll.query.with_entities(AssessmentEnroll.id). \
        filter_by(assessment_id=assessment_id). \
        filter_by(testset_id=ts_id). \
        filter_by(student_id=student_id).order_by(AssessmentEnroll.id.desc()).first()
    if row is None:
        return redirect(url_for('report.list_my_report', error='Not found assessment enroll data'))

    assessment_enroll_id = row.id
    assessment_name = (Assessment.query.with_entities(Assessment.name).filter_by(id=assessment_id).first()).name
    # My Report : Header - 'total_students', 'student_rank', 'score', 'total_score', 'percentile_score'
    ts_header = query_my_report_header(assessment_id, ts_id, student_id)
    score = '{} out of {} ({}%)'.format(ts_header.score, ts_header.total_score, ts_header.percentile_score)
    rank = '{} out of {}'.format(ts_header.student_rank, ts_header.total_students)
    # My Report : Body - Item ID/Candidate Value/IsCorrect/Correct_Value, Correct_percentile, Item Category
    #                       'assessment_enroll_id', 'testset_id', 'candidate_r_value', 'student_id', 'grade',
    #                       "created_time", 'is_correct', 'correct_r_value', 'item_percentile', 'item_id', 'category'
    markings = query_my_report_body(assessment_enroll_id, ts_id)
    # My Report : Footer - Candidate Avg Score / Total Avg Score by Item Category
    #                       'code_name as category', 'score', 'total_score', 'avg_score', 'percentile_score'
    ts_by_category = query_my_report_footer(assessment_id, student_id)
    return render_template("report/my_report.html", assessment_name=assessment_name, rank=rank,
                           score=score, markings=markings, ts_by_category=ts_by_category)


''' 
 @report.route('/student/set/<int:assessment_id>/<int:student_id>', methods=['GET'])
 my_student_set_report() : Student Login > My Report > Student Report 
    - Execute: Provide link to Student Report by assessment (all subject)
'''
@report.route('/student/set/<int:assessment_id>/<int:student_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def my_student_set_report(assessment_id, student_id):
    # ToDO: Check accessbility to get Report
    assessment_enrolls = AssessmentEnroll.query.filter_by(assessment_id=assessment_id).filter_by(
        student_id=student_id).all()
    if assessment_enrolls:
        grade = EducationPlanDetail.get_grade(assessment_id)
        assessment_GUID = assessment_enrolls[0].assessment_guid
        test_type_string = Codebook.get_code_name(assessment_enrolls[0].assessment.test_type)
        if test_type_string == 'Naplan':
            # Student Report : Generate image file for  Naplan student Report
            #                   saved into /static/report/naplan_result/naplan-*.png
            file_name = make_naplan_student_report(assessment_enrolls, assessment_id, student_id, assessment_GUID, grade)
        else:
            # For selective test or other test type
            test_type_string = 'other'
        template_html_name = 'report/my_report_' + test_type_string + '.html'
        grade = EducationPlanDetail.get_grade(assessment_id)
        web_file_path = os.path.join(current_app.config['NAPLAN_RESULT_DIR'].lstrip('app'), file_name)
        return render_template(template_html_name, image_file_path=web_file_path, grade=grade)
    else:
        return redirect(url_for('report.list_my_report', error='Not found assessment enroll data'))


''' 
 @report.route('/manage', methods=['GET'])
 manage() : Report user Login > Report By Center 
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
    if flag:
        # Query Report : 'plan_id', 'plan_name', 'assessment_year', 'grade', 'test_type','assessment_order',
        #                 'assessment_id', 'testset_id', 'assessment_enroll_id', 'student_id', 'attempt_count',
        #                 'test_center', 'start_time_client'
        rows = query_all_report_data(test_type, test_center, year)
        # Re-construct "Reports" with query result
        index = 0
        _assessment_enroll_id, _testset_id, _test_center, _assessment_year, _assessment_order = 0, 0, 0, 0, 0
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

            students.append(row.student_id)
            _assessment_year = row.assessment_year
            _grade = row.grade
            _test_type = row.test_type
            _assessment_order = row.assessment_order
            _assessment_id = row.assessment_id
            if row.assessment_enroll_id:
                _assessment_enroll_id = row.assessment_enroll_id
            else:
                _assessment_enroll_id = 0
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

        # Test Summary Report list for All Students: 'student_id','plan_id','plan_name',
        #                           'year','grade','test_type'
        test_summaries = query_individual_progress_summary_report_list()
    return render_template('report/manage.html', form=search_form, reports=reports,
                           test_summaries=test_summaries, test_center=test_center)


''' 
 @report.route('/test_ranking/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:test_center>',
              methods=['GET'])
 test_ranking_report() : Report user Login > Report By Center > Search
    - Execute: Provide link to Test Ranking Report by assessment 
'''
@report.route('/test_ranking/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:test_center>',
              methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_READ)
def test_ranking_report(year, test_type, sequence, assessment_id, test_center):
    # Test Ranking Report - subject list : 'testset_id', 'subject_name'
    subjects = query_test_ranking_subject_list(assessment_id)

    # rank students from all test candidates
    #            data : 'student_id', 'cs_student_id', 'student_name', 'assessment_id',
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
    template_file_name = 'report/test_result_' + Codebook.get_code_name(test_type) + '.html'

    web_file_path = os.path.join(current_app.config['CSEDU_IMG_DIR'].lstrip('app'), 'CSEducation.png')
    local_file_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                            current_app.config['CSEDU_IMG_DIR'],
                                            'CSEducation.png')
    if request.args.get('excel-download') == "1":
        rsp = build_test_ranking_excel_response(subjects, test_summaries, year, test_type, sequence)
        return rsp
    if request.args.get('pdf-download') == "1":
        rsp = build_test_ranking_pdf_response(template_file_name, image_file_path=local_file_path,
                           year=year, test_type=test_type, sequence=sequence,
                           subject_names=subjects,
                           test_summaries=test_summaries, now=datetime.utcnow())
        return rsp
    return render_template(template_file_name, image_file_path=web_file_path,
                           year=year, test_type=test_type, sequence=sequence,
                           subject_names=subjects,
                           test_summaries=test_summaries, now=datetime.utcnow())


''' 
 @report.route('/summary/<int:plan_id>/<int:branch_id>', methods=['GET'])
 summary_report() : Report user Login > Report By Center > Search
    - Execute: Provide link to Download: individual Subject Report for all students 
'''
@report.route('/summary/<int:plan_id>/<int:branch_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def summary_report(plan_id, branch_id):
    plan_GUID, test_type_string, grade = '', '', ''
    assessment_ids = [row.assessment_id for row in EducationPlanDetail.query.filter_by(plan_id=plan_id).all()]
    query = db.session.query(AssessmentEnroll.student_id).distinct()
    # Todo: Need to check if current_user have access right on queried data
    test_center = Codebook.get_testcenter_of_current_user()
    if not test_center and (current_user.role.name == 'Moderator' or current_user.role.name == 'Administrator'):
        test_center = Codebook.query.filter_by(code_type='test_center').filter_by(code_name='All').first()
    if (test_center.id == branch_id):
        if not (test_center.code_name == 'All'):
            query = query.filter(AssessmentEnroll.test_center == branch_id)
        query = query.filter(AssessmentEnroll.assessment_id.in_(assessment_ids))
        enrolled_students = query.all()
        for enrolled_student in enrolled_students:
            student_id = enrolled_student.student_id
            plan_GUID = individual_progress_summary_report(plan_id, student_id)
            if plan_GUID is None:
                return redirect(url_for('report.manage', error='Error during generating pdf files'))
        rsp = build_individual_progress_zipper(plan_GUID)
        return rsp
    else:
        return 'Invalid Request: No data for current user'


def individual_progress_summary_report(plan_id, student_id):
    plan_GUID = (EducationPlan.query.filter_by(id=plan_id).first()).GUID
    # ##
    # Header - 'year', 'grade', 'test_type'
    ts_header = query_individual_progress_summary_report_header(plan_id)
    test_type_string = Codebook.get_code_name(ts_header.test_type)
    if test_type_string != 'Naplan':
        test_type_string = 'other'
    # ##
    # Body - Summary Report by assessment/test - 'p.plan_id', 'p."order"', 'p.assessment_id',
    #                     'p.student_id', 'my_set_score', 'p.rank_v', 'avg_set_score'
    #        Summary Report by plan - 'p.plan_id', 'p."order"', 'p.assessment_id',
    #                     'p.testset_id', 'ts.student_id', 'score', 'total_score'
    #                     'avg_score', 'percentile_score', 'rank_v', 'total_students'
    # ##
    # Construct 'my_assessment' - 'my_testset' which are displayed as individual subject score on report
    rows_all = query_individual_progress_summary_report_by_assessment(plan_id, student_id)
    rows = query_individual_progress_summary_report_by_plan(plan_id, student_id)

    my_assessment, my_subject_score, avg_subject_score = [], [], [] # my_score by subject, avg_score
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
    #               'plan_id', 'testset_id', 'student_id', 'rank_v', 'subject_avg_my_score',
    #               'subject_avg_avg_score', 'subject_avg_min_score', 'subject_avg_max_score'
    #         Summary Report by plan( 학생이 친 시험 전체(plan package단위) 점수, rank, 최저점, 최고점 )
    #               'plan_id', 'student_id', 'rank_v', 'sum_my_score',
    #               'sum_avg_score', 'sum_min_score', 'sum_max_score'
    # ##
    total_subject_scores = query_individual_progress_summary_by_subject_v(plan_id, student_id)
    total_score = query_individual_progress_summary_by_plan_v(plan_id, student_id, num_of_assessments)

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

    # template_file_name = 'report/individual_progress_' + test_type_string + '.html'
    # web_file_path = os.path.join(current_app.config['CSEDU_IMG_DIR'].lstrip('app'), 'CSEducation.png')
    # local_file_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
    #                                         current_app.config['CSEDU_IMG_DIR'],
    #                                         'CSEducation.png')
    #
    # success = build_individual_progress_pdf_response(template_file_name, image_file_path=local_file_path,
    #                                             ts_header=ts_header,
    #                                             num_of_assessments=num_of_assessments, num_of_subjects=num_of_subjects,
    #                                             subject_names=subject_names,
    #                                             subjects=subjects, my_set_score=my_set_score,
    #                                             avg_set_score=avg_set_score, my_set_rank=my_set_rank,
    #                                             score_summaries=score_summaries, plan_id=plan_id,
    #                                             plan_GUID=plan_GUID, student_id=student_id)

    plan_GUID = (EducationPlan.query.filter_by(id=plan_id).first()).GUID
    by_subject_file_name = draw_individual_progress_by_subject(score_summaries, plan_GUID, student_id)
    by_set_file_name = draw_individual_progress_by_set(my_set_score, avg_set_score, plan_GUID, student_id)

    template_file_name = 'report/individual_progress_' + test_type_string + '.html'
    logo_web_path = os.path.join(current_app.config['CSEDU_IMG_DIR'].lstrip('app'), 'CSEducation.png')
    logo_local_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                            current_app.config['CSEDU_IMG_DIR'],
                                            'CSEducation.png')
    by_subject_web_path = os.path.join(current_app.config['NAPLAN_RESULT_DIR'].lstrip('app'), by_subject_file_name)
    by_subject_local_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                                  current_app.config['NAPLAN_RESULT_DIR'],
                                                  by_subject_file_name)
    by_set_web_path = os.path.join(current_app.config['NAPLAN_RESULT_DIR'].lstrip('app'), by_set_file_name)
    by_set_local_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                              current_app.config['NAPLAN_RESULT_DIR'],
                                              by_set_file_name)

    success = build_individual_progress_pdf_response(template_file_name, logo_file_name=logo_local_path,
                           by_subject_file_name=by_subject_local_path, by_set_file_name=by_set_local_path,
                           ts_header=ts_header,
                           num_of_assessments=num_of_assessments, num_of_subjects=num_of_subjects,
                           subject_names=subject_names,
                           subjects=subjects, my_set_score=my_set_score,
                           avg_set_score=avg_set_score, my_set_rank=my_set_rank,
                           score_summaries=score_summaries, plan_id=plan_id, plan_GUID=plan_GUID, student_id=student_id)

    if success != 'success':
        return None # plan_GUID
    return plan_GUID


''' 
 @report.route('/results/pdf/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:branch_id>',
              methods=['GET'])
 report_results_pdf() : Report user Login > Report By Center 
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
    query = db.session.query(AssessmentEnroll.student_id).distinct()
    # Todo: Need to check if current_user have access right on queried data
    test_center = Codebook.get_testcenter_of_current_user()
    if not test_center and (current_user.role.name == 'Moderator' or current_user.role.name == 'Administrator'):
        test_center = Codebook.query.filter_by(code_type='test_center').filter_by(code_name='All').first()
    if (test_center.id == branch_id):
        if not (test_center.code_name == 'All'):
            query = query.filter(AssessmentEnroll.test_center==branch_id)
        query = query.filter(AssessmentEnroll.assessment_id==assessment_id)
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
            student_id = enrolled_student.student_id
            enrollment = AssessmentEnroll.query.filter_by(assessment_id=assessment_id).filter_by(
                student_id=student_id).all()
            if enrollment:
                if test_type_string == 'Naplan':
                    # Student Report : Generate image file for  Naplan student Report
                    #                   saved into /static/report/naplan_result/naplan-*.png
                    file_name = make_naplan_student_report(enrollment, assessment_id, student_id, assessment_GUID, grade)

                else:
                    # For selective test or other test type
                    test_type_string = 'other'
                template_file_name = 'report/my_report_' + test_type_string + '.html'

                local_file_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                                        current_app.config['NAPLAN_RESULT_DIR'],
                                                        file_name)
                success = build_test_results_pdf_response(template_file_name, image_file_path=local_file_path, assessment_GUID=assessment_GUID, student_id=student_id)
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


@report.route('/seaborn_test', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def seaborn_test():
    import numpy as np
    import seaborn as sns
    import matplotlib.pyplot as plt
    import pandas as pd
    sns.set(style="darkgrid")

    # values = []
    # values.append(np.array([30, 35]))
    # values.append(np.array([89, 67]))
    # values.append(np.array([76, 60]))
    # tests = np.array(['Test1', 'Test2', 'Test3'])
    # df = pd.DataFrame(values, tests, columns=['My Score','Avg Score'])
    # sns.lineplot(data=df, palette="tab10", linewidth=2.5)

    # values = []
    # values.append([30, 35])
    # values.append([89, 67])
    # values.append([76, 60])
    # tests = ['Test1', 'Test2', 'Test3']
    values = [[50.0, 25.0],[40.0, 35.0]]
    tests = ['Test0','Test1']
    df = pd.DataFrame(values, tests, columns=['My Score','Avg Score'])
    sns.lineplot(data=df, palette="tab10", linewidth=2.5)

    plt.savefig("mygraph_%s.png" % "Test1")

    return 'Success'


@report.route('/test/summary/<int:plan_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def test_individual_progress_summary_report(plan_id):
    # Todo: change student_id
    student_id = 8
    # student_id = current_user.id
    # ##
    # Header - 'year', 'grade', 'test_type'
    ts_header = query_individual_progress_summary_report_header(plan_id)
    test_type_string = Codebook.get_code_name(ts_header.test_type)
    if test_type_string != 'Naplan':
        test_type_string = 'other'
    # ##
    # Body - Summary Report by assessment/test - 'p.plan_id', 'p."order"', 'p.assessment_id',
    #                     'p.student_id', 'my_set_score', 'p.rank_v', 'avg_set_score'
    #        Summary Report by plan - 'p.plan_id', 'p."order"', 'p.assessment_id',
    #                     'p.testset_id', 'ts.student_id', 'score', 'total_score'
    #                     'avg_score', 'percentile_score', 'rank_v', 'total_students'
    # ##
    # Construct 'my_assessment' - 'my_testset' which are displayed as individual subject score on report
    rows_all = query_individual_progress_summary_report_by_assessment(plan_id, student_id)
    rows = query_individual_progress_summary_report_by_plan(plan_id, student_id)

    my_assessment, my_subject_score, avg_subject_score = [], [], [] # my_score by subject, avg_score
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
    #               'plan_id', 'testset_id', 'student_id', 'rank_v', 'subject_avg_my_score',
    #               'subject_avg_avg_score', 'subject_avg_min_score', 'subject_avg_max_score'
    #         Summary Report by plan( 학생이 친 시험 전체(plan package단위) 점수, rank, 최저점, 최고점 )
    #               'plan_id', 'student_id', 'rank_v', 'sum_my_score',
    #               'sum_avg_score', 'sum_min_score', 'sum_max_score'
    # ##
    total_subject_scores = query_individual_progress_summary_by_subject_v(plan_id, student_id)
    total_score = query_individual_progress_summary_by_plan_v(plan_id, student_id, num_of_assessments)

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
    by_subject_file_name = draw_individual_progress_by_subject(score_summaries, plan_GUID, student_id)
    by_set_file_name = draw_individual_progress_by_set(my_set_score, avg_set_score, plan_GUID, student_id)

    template_file_name = 'report/test_individual_progress_' + test_type_string + '.html'
    logo_web_path = os.path.join(current_app.config['CSEDU_IMG_DIR'].lstrip('app'), 'CSEducation.png')
    logo_local_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                            current_app.config['CSEDU_IMG_DIR'],
                                            'CSEducation.png')
    by_subject_web_path = os.path.join(current_app.config['NAPLAN_RESULT_DIR'].lstrip('app'), by_subject_file_name)
    by_subject_local_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                            current_app.config['NAPLAN_RESULT_DIR'],
                                            by_subject_file_name)
    by_set_web_path = os.path.join(current_app.config['NAPLAN_RESULT_DIR'].lstrip('app'), by_set_file_name)
    by_set_local_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                            current_app.config['NAPLAN_RESULT_DIR'],
                                            by_set_file_name)

    return render_template(template_file_name, logo_file_name = logo_web_path,
                           by_subject_file_name=by_subject_web_path, by_set_file_name = by_set_web_path,
                           ts_header=ts_header,
                           num_of_assessments=num_of_assessments, num_of_subjects=num_of_subjects,
                           subject_names=subject_names,
                           subjects=subjects, my_set_score=my_set_score,
                           avg_set_score=avg_set_score, my_set_rank=my_set_rank,
                           score_summaries=score_summaries, plan_id=plan_id)