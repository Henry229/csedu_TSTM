from flask import render_template, flash, request, current_app, redirect
from flask_login import login_required, current_user
from sqlalchemy import desc

from . import errornote
from ..decorators import permission_required
from ..api.reports import query_my_report_header, query_my_report_body
from ..models import Codebook, Permission, AssessmentEnroll, Assessment, Testset, refresh_mviews, AssessmentRetry, \
    Marking, Item
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

    # 가장 오래된 retry
    retry = AssessmentRetry.query.filter_by(assessment_enroll_id=assessment_enroll_id) \
        .order_by(AssessmentRetry.start_time).first()
    has_finished_retry = retry and retry.finish_time is not None

    marking_query = Marking.query.join(Item, Marking.item_id == Item.id)\
        .join(Codebook, Item.category == Codebook.id).add_columns(Codebook.code_name)\
        .filter(Marking.assessment_enroll_id == assessment_enroll_id).order_by(Marking.question_no).all()
    markings = []
    for marking, code_name in marking_query:
        marking.category_name = code_name
        # retry 를 한번이라도 끝내야 설명을 볼 수 있다.
        if marking.last_is_correct is not True:
            marking.explanation_link = view_explanation(testset_id=ts_id, item_id=marking.item_id)
            marking.explanation_link_enable = has_finished_retry
        markings.append(marking)

    # Error note retry status: 가장 최근 것.
    retry_session_key = None
    retry = AssessmentRetry.query.filter_by(assessment_enroll_id=assessment_enroll_id)\
        .order_by(desc(AssessmentRetry.start_time)).first()
    if retry is not None and retry.finish_time is None:
        retry_session_key = retry.session_key

    template_file = 'errornote/error_note.html'
    rendered_template = render_template(template_file, assessment_name=assessment_name,
                                        assessment_enroll_id=assessment_enroll_id,
                                        subject=test_subject_string,
                                        score=score, markings=markings, retry_session_key=retry_session_key,
                                        student_user_id=student_user_id, static_folder=current_app.static_folder,
                                        grade=grade)
    return rendered_template
