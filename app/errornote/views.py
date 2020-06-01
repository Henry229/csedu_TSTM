import os
from flask import render_template, flash, request, current_app, redirect, url_for
from flask_login import login_required, current_user

from . import errornote
from ..decorators import permission_required
from ..api.reports import query_my_report_header, query_my_report_body
from ..models import Codebook, Permission, AssessmentEnroll, Assessment, Testset, refresh_mviews
from ..web.views import view_explanation


@errornote.route('/<int:assessment_enroll_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def error_note(assessment_enroll_id):
    # Todo: Check accessibility to get report
    refresh_mviews()

    assessment_enroll = AssessmentEnroll.query.filter_by(id=assessment_enroll_id).first()
    if assessment_enroll is None:
        url = request.referrer
        flash('Assessment Enroll data not available')
        return redirect(url)

    assessment_id = assessment_enroll.assessment_id
    ts_id = assessment_enroll.testset_id
    student_user_id = current_user.id
    assessment = Assessment.query.filter_by(id=assessment_id).first()
    assessment_name = assessment.name
    testset = Testset.query.with_entities(Testset.subject, Testset.grade)\
        .filter_by(id=assessment_enroll.testset_id).first()
    test_subject_string = Codebook.get_code_name(testset.subject)
    grade = Codebook.get_code_name(testset.grade)

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
    explanation_link = {}
    for marking in markings:
        explanation_link[marking.question_no] = view_explanation(testset_id=ts_id, item_id=marking.item_id)

    # My Report : Footer - Candidate Avg Score / Total Avg Score by Item Category
    #                       'code_name as category', 'score', 'total_score', 'avg_score', 'percentile_score'
    # ToDo: ts_by_category unavailable until finalise all student's mark and calculate average data
    #       so it need to be discussed to branch out in "test analysed report"
    ts_by_category = None
    # ts_by_category = query_my_report_footer(assessment_id, student_user_id)

    if test_subject_string == 'Writing':
        marking_writing_id = 0
        url_i = url_for('writing.w_report', assessment_enroll_id=assessment_enroll_id,
                        student_user_id=student_user_id, marking_writing_id=marking_writing_id)
        return redirect(url_i)

    template_file = 'errornote/error_note.html'
    rendered_template = render_template(template_file, assessment_name=assessment_name,
                                        assessment_enroll_id=assessment_enroll_id,
                                        subject=test_subject_string, rank=rank,
                                        score=score, markings=markings, ts_by_category=ts_by_category,
                                        student_user_id=student_user_id, static_folder=current_app.static_folder,
                                        grade=grade,
                                        explanation_link=explanation_link)
    return rendered_template
