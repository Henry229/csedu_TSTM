import os
from datetime import datetime

from flask import render_template, flash, request, current_app, redirect, url_for, Response, jsonify, send_file
from flask_jsontools import jsonapi
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
    build_test_results_pdf_response, build_test_results_zipper, \
    build_individual_progress_pdf_response, build_individual_progress_zipper, \
    draw_individual_progress_by_subject, draw_individual_progress_by_set
from ..decorators import permission_required
from ..models import Codebook, Permission, AssessmentEnroll, Assessment, EducationPlanDetail, \
    refresh_mviews, Item, Marking, EducationPlan, Student, Testset, AssessmentHasTestset
from ..auth.views import get_student_info

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
        filter(AssessmentEnroll.student_user_id==student_user_id).all()]

    assessment_enrolls = AssessmentEnroll.query.filter(AssessmentEnroll.assessment_guid.in_(guid_list)).\
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

    # My Report List : 'id', 'assessment_id', 'student_user_id', 'year', 'test_type', 'name', 'branch_id',
    #                'subject_1', 'subject_2', 'subject_3', 'subject_4', 'subject_5'
    rows = query_my_report_list_v(student_user_id)
    return render_template("report/my_report_list.html", assessment_enrolls=rows)


@report.route('/ts/<int:assessment_enroll_id>/<int:assessment_id>/<int:ts_id>/<student_user_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def my_report(assessment_enroll_id, assessment_id, ts_id, student_user_id):
    '''
     @report.route('/ts/<int:assessment_id>/<int:ts_id>/<int:student_user_id>', methods=['GET'])
     my_report() : Student Login > My Report > Report
        - Execute: Provide link to Subject Report
    '''
    # Todo: Check accessibility to get report
    # refresh_mviews()

    pdf = False
    pdf_url = "%s?type=pdf" % request.url
    if 'type' in request.args.keys():
        pdf = request.args['type'] == 'pdf'

    row = AssessmentEnroll.query.with_entities(AssessmentEnroll.id, AssessmentEnroll.testset_id). \
        filter_by(id=assessment_enroll_id). \
        filter_by(assessment_id=assessment_id). \
        filter_by(testset_id=ts_id). \
        filter_by(student_user_id=student_user_id).order_by(AssessmentEnroll.id.desc()).first()
    if row is None:
        url = request.referrer
        flash('Assessment Enroll data not available')
        return redirect(url)

    assessment_enroll_id = row.id
    assessment_name = (Assessment.query.with_entities(Assessment.name).filter_by(id=assessment_id).first()).name
    test_subject_string = Codebook.get_code_name((Testset.query.with_entities(Testset.subject).filter_by(id=row.testset_id).first()).subject)
    # My Report : Header - 'total_students', 'student_rank', 'score', 'total_score', 'percentile_score'
    ts_header = query_my_report_header(assessment_enroll_id, assessment_id, ts_id, student_user_id)
    if ts_header is None:
        url = request.referrer
        flash('Marking data not available')
        return redirect(url)

    score = '{} out of {} ({}%)'.format(ts_header.score, ts_header.total_score, ts_header.percentile_score)
    rank = '{} out of {}'.format(ts_header.student_rank, ts_header.total_students)
    # My Report : Body - Item ID/Candidate Value/IsCorrect/Correct_Value, Correct_percentile, Item Category
    #                       'assessment_enroll_id', 'testset_id', 'candidate_r_value', 'student_user_id', 'grade',
    #                       "created_time", 'is_correct', 'correct_r_value', 'item_percentile', 'item_id', 'category'
    markings = query_my_report_body(assessment_enroll_id, ts_id)
    # My Report : Footer - Candidate Avg Score / Total Avg Score by Item Category
    #                       'code_name as category', 'score', 'total_score', 'avg_score', 'percentile_score'
    ts_by_category = query_my_report_footer(assessment_id, student_user_id)
    if test_subject_string == 'Writing':
        marking_writing_id = 0
        url_i = url_for('writing.w_report',assessment_enroll_id=assessment_enroll_id,
                                student_user_id=student_user_id, marking_writing_id=marking_writing_id)
        return redirect(url_i)

    template_file = 'report/my_report.html'
    if pdf:
        template_file = 'report/my_report_pdf.html',

    rendered_template_pdf = render_template(template_file, assessment_name=assessment_name, rank=rank,
                                            score=score, markings=markings, ts_by_category=ts_by_category,
                                            student_user_id=student_user_id, static_folder=current_app.static_folder,
                                            pdf_url=pdf_url)
    if not pdf:
        # return render_template('report/my_report.html', assessment_name=assessment_name, rank=rank,
        #                        score=score, markings=markings, ts_by_category=ts_by_category,
        #                        student_user_id=student_user_id, static_folder=current_app.static_folder,
        #                        pdf_url=pdf_url)
        return rendered_template_pdf
    # PDF download
    from weasyprint import HTML

    html = HTML(string=rendered_template_pdf)


    pdf_file_path = os.path.join(os.path.dirname(current_app.root_path), current_app.config['USER_DATA_FOLDER'],
                                 str(student_user_id),
                                 "report",
                                 "test_report_%s_%s_%s_%s.pdf" % (assessment_enroll_id, assessment_id, ts_id, student_user_id))

    os.chdir(current_app.config['USER_DATA_FOLDER'])
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
                                         db.func.max(AssessmentEnroll.attempt_count).label("attempt_count")).\
                        group_by(AssessmentEnroll.assessment_id,
                                         AssessmentEnroll.testset_id,
                                         AssessmentEnroll.student_user_id).subquery()
    assessment_enrolls = AssessmentEnroll.query.join(latest_attempt_tests,
                                         AssessmentEnroll.assessment_id==latest_attempt_tests.c.assessment_id). \
                        filter(AssessmentEnroll.testset_id == latest_attempt_tests.c.testset_id,
                              AssessmentEnroll.student_user_id == latest_attempt_tests.c.student_user_id). \
                        filter_by(assessment_id=assessment_id).\
                        filter_by(student_user_id=student_user_id).\
                        order_by(AssessmentEnroll.testset_id.asc(), AssessmentEnroll.attempt_count.desc()).all()

    if assessment_enrolls:
        # ToDo: Decide which grade should be taken
        # grade = EducationPlanDetail.get_grade(assessment_id)
        # grade = assessment_enrolls[0].grade
        grade = Codebook.get_code_name(((AssessmentHasTestset.query.filter_by(assessment_id=assessment_id).first()).testset).grade)

        assessment_GUID = assessment_enrolls[0].assessment_guid
        test_type_string = Codebook.get_code_name(assessment_enrolls[0].assessment.test_type)
        if test_type_string == 'Naplan':
            # Student Report : Generate image file for  Naplan student Report
            #                   saved into /static/report/naplan_result/naplan-*.png
            if grade=='-':
                return redirect(url_for('report.list_my_report', error='No report generated due to lack of information - grade'))
            else:
                file_name = make_naplan_student_report(assessment_enrolls, assessment_id, student_user_id, assessment_GUID, grade)
                if file_name is None:
                    url = request.referrer
                    flash('Marking data not available')
                    return redirect(url)
        else:
            # For selective test or other test type
            test_type_string = 'other'
        template_html_name = 'report/my_report_' + test_type_string + '.html'
        web_file_path = url_for("api.get_naplan", file=file_name)
        return render_template(template_html_name, image_file_path=web_file_path, grade=grade, student_user_id=student_user_id)
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
        if Codebook.get_code_name(test_center)!='All':
            query = query.filter(AssessmentEnroll.test_center==test_center)
        assessments = query.order_by(Assessment.id.asc()).all()

        all_subject_r_list = []
        for assessment in assessments:
            if Codebook.get_code_name(test_center) == 'All':
                assessment_enrolls = AssessmentEnroll.query.filter_by(assessment_id=assessment.id). \
                    order_by(AssessmentEnroll.testset_id.asc()).all()
            else:
                assessment_enrolls = AssessmentEnroll.query.filter_by(assessment_id=assessment.id).\
                    filter_by(test_center=test_center).\
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
                        testset_json_str["students"]=student_list
                        testset_list.append(testset_json_str)
                        student_list = []
                        testset_json_str = []

                    old_testset_id = testset_id
                    testset_json_str = {"testset_id":testset_id}
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
            assessment_json_str = { "year": assessment.year,
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
        _testset_id, _test_center, _assessment_year, _assessment_order =  0, 0, 0, 0
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

            students.append({"student_user_id": row.student_user_id,"assessment_enroll_id": row.assessment_enroll_id})
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
        pdf_file_path = os.path.join(os.path.dirname(current_app.root_path), current_app.config['USER_DATA_FOLDER'],
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
    by_subject_web_path = url_for("api.get_naplan", file=by_subject_file_name)
    by_subject_local_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                                  naplan_folder,
                                                  by_subject_file_name)
    by_set_web_path = url_for("api.get_naplan", file=by_set_file_name)
    by_set_local_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                              naplan_folder,
                                              by_set_file_name)

    success = build_individual_progress_pdf_response(template_file_name, static_folder=current_app.static_folder,
                           by_subject_file_name=by_subject_local_path, by_set_file_name=by_set_local_path,
                           ts_header=ts_header,
                           num_of_assessments=num_of_assessments, num_of_subjects=num_of_subjects,
                           subject_names=subject_names,
                           subjects=subjects, my_set_score=my_set_score,
                           avg_set_score=avg_set_score, my_set_rank=my_set_rank,
                           score_summaries=score_summaries, plan_id=plan_id, plan_GUID=plan_GUID, student_user_id=student_user_id)

    if success != 'success':
        return None # plan_GUID
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
            student_user_id = enrolled_student.student_user_id
            enrollment = AssessmentEnroll.query.filter_by(assessment_id=assessment_id).filter_by(
                student_user_id=student_user_id).all()
            if enrollment:
                if test_type_string == 'Naplan':
                    # Student Report : Generate image file for  Naplan student Report
                    #                   saved into /static/report/naplan_result/naplan-*.png
                    file_name = make_naplan_student_report(enrollment, assessment_id, student_user_id, assessment_GUID, grade)

                else:
                    # For selective test or other test type
                    test_type_string = 'other'
                template_file_name = 'report/my_report_' + test_type_string + '.html'
                naplan_folder = os.path.join(current_app.config['USER_DATA_FOLDER'], str(current_user.id), "naplan")

                local_file_path = 'file:///%s/%s/%s' % (os.path.dirname(current_app.instance_path).replace('\\', '/'),
                                                        naplan_folder,
                                                        file_name)
                success = build_test_results_pdf_response(template_file_name, image_file_path=local_file_path, assessment_GUID=assessment_GUID, student_user_id=student_user_id)
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
    if type=='individual_progress_report':
        template_file = 'report/individual_progress_Naplan_pdf_test.html'
        rendered_template_pdf = render_template(template_file)

        html = HTML(string=rendered_template_pdf)

        pdf_file_path = os.path.join(os.path.dirname(current_app.root_path), current_app.config['USER_DATA_FOLDER'],
                                     "report_test",
                                     "individual_progress_Naplan_pdf_test.pdf")
    elif type=='test_ranking':
        template_file = 'report/test_result_Naplan_pdf_test.html'
        rendered_template_pdf = render_template(template_file)

        html = HTML(string=rendered_template_pdf)

        pdf_file_path = os.path.join(os.path.dirname(current_app.root_path), current_app.config['USER_DATA_FOLDER'],
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
