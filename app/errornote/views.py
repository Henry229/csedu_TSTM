from flask import render_template, flash, request, current_app, redirect
from flask_login import login_required, current_user
from sqlalchemy import desc, or_, and_

from . import errornote
from ..decorators import permission_required
from ..models import Codebook, Permission, AssessmentEnroll, Assessment, Testset, refresh_mviews, AssessmentRetry, \
    Marking, Item, RetryMarking
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

    # 한번이라도 retry 를 한 question_no 를 찾는다.
    retried_questions = RetryMarking.query.with_entities(RetryMarking.question_no)\
        .join(AssessmentRetry,
              and_(AssessmentRetry.assessment_enroll_id == assessment_enroll_id,
                   RetryMarking.assessment_retry_id == AssessmentRetry.id,
                   or_(AssessmentRetry.is_single_retry == True, AssessmentRetry.finish_time != None)))\
        .distinct().all()
    retried_questions = [q.question_no for q in retried_questions]

    marking_query = Marking.query.join(Item, Marking.item_id == Item.id)\
        .outerjoin(Codebook, Item.category == Codebook.id).add_columns(Codebook.code_name)\
        .filter(Marking.assessment_enroll_id == assessment_enroll_id).order_by(Marking.question_no).all()
    markings = []
    question_count, correct_count = 0, 0
    for marking, code_name in marking_query:
        question_count = question_count + 1
        marking.category_name = code_name
        if is_blank_answer(marking.candidate_r_value):
            marking.candidate_r_value = ''
        if is_blank_answer(marking.last_r_value):
            marking.last_r_value = ''
        # retry 를 한번이라도 끝내야 설명을 볼 수 있다.
        if marking.is_correct is True:
            correct_count = correct_count + 1
        else:
            marking.explanation_link = view_explanation(testset_id=ts_id, item_id=marking.item_id)
            marking.explanation_link_enable = marking.question_no in retried_questions
        markings.append(marking)
    correct_percent = correct_count * 100.0 / question_count
    score = '{} out of {} ({:.2f}%)'.format(correct_count, question_count, correct_percent)
    last_error_count = Marking.query.filter(Marking.assessment_enroll_id == assessment_enroll_id,
                                            or_(Marking.last_is_correct == False, Marking.last_is_correct == None)) \
        .count()
    retry_session_key = None
    if last_error_count > 0:
        # Error note retry status: 가장 최근 것.
        retry = AssessmentRetry.query.filter_by(assessment_enroll_id=assessment_enroll_id, is_single_retry=False)\
            .order_by(desc(AssessmentRetry.start_time)).first()
        if retry is not None and retry.finish_time is None:
            retry_session_key = retry.session_key

    test_datetime = assessment_enroll.start_time.strftime("%d/%m/%Y %H:%M:%S")
    template_file = 'errornote/error_note.html'
    rendered_template = render_template(template_file, assessment_name=assessment_name,
                                        assessment_enroll_id=assessment_enroll_id,
                                        subject=test_subject_string,
                                        score=score, markings=markings, retry_session_key=retry_session_key,
                                        last_error_count=last_error_count, test_datetime=test_datetime,
                                        student_user_id=student_user_id, static_folder=current_app.static_folder,
                                        grade=grade)
    return rendered_template


def is_blank_answer(answer):
    if answer is None:
        return True
    if type(answer) is not list:
        return False
    if len(answer) != 1:
        return False
    if answer[0] == '':
        return True
    return False
