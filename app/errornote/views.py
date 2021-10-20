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
    #refresh_mviews()

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
    is_verbal = False
    is_verbal_all = True
    for marking, code_name in marking_query:
        question_count = question_count + 1
        marking.category_name = code_name
        if is_blank_answer(marking.candidate_r_value):
            marking.candidate_r_value = ''
        if is_blank_answer(marking.last_r_value):
            marking.last_r_value = ''
        # retry 를 한번이라도 끝내야 설명을 볼 수 있다. (answer as well)
        if marking.is_correct is True:
            correct_count = correct_count + 1
        else:
            marking.explanation_link = view_explanation(testset_id=ts_id, item_id=marking.item_id)
            marking.explanation_link_enable = marking.question_no in retried_questions
            marking.view_answer_enable = marking.question_no in retried_questions

        #if category is verbal, multiple drag drop question.. treating to be shape of box
        if marking.item.category == 281 and marking.item.subcategory != 311:
            correct_r_values = []
            for value in marking.correct_r_value:
                if value.find(" gap_") > -1:
                    ques_no = value[value.rfind('_') + 1:]
                    end = value.index(" gap_")
                    ques_correct_value = value[0:end]
                    correct_r_values.append({'no':str(len(correct_r_values)+1), 'value':ques_correct_value})
            if len(correct_r_values) > 0:
                marking.verbal_correct_r_value = correct_r_values
                is_verbal = True

            candidate_r_values = []
            candidate_all_correct = True
            for r_value in marking.correct_r_value:
                is_existent = False
                r_ques_no = '0'
                if r_value.find(" gap_") > -1:
                    r_ques_no = r_value[r_value.rfind('_') + 1:]
                for value in marking.candidate_r_value:
                    if value.find(" gap_") > -1:
                        ques_no = value[value.rfind('_') + 1:]
                        if r_ques_no == ques_no:
                            _is_correct = False
                            if r_value == value:
                                _is_correct = True
                            end = value.index(" gap_")
                            ques_candidate_value = value[0:end]
                            candidate_r_values.append({'no':str(len(candidate_r_values)+1), 'value':ques_candidate_value, 'correct': _is_correct})
                            if _is_correct is False:
                                candidate_all_correct = False
                            is_existent = True
                if not is_existent:
                    candidate_r_values.append({'no': str(len(candidate_r_values)+1), 'value': '', 'correct': False})
                    candidate_all_correct = False

            if len(candidate_r_values) > 0:
                marking.verbal_candidate_r_value = candidate_r_values
                marking.candidate_all_correct = candidate_all_correct


            last_r_values = []
            last_r_value_index = 0
            for r_value in marking.last_r_value:
                last_r_value_index += 1
                is_existent = False
                r_ques_no = '0'
                if r_value.find(" gap_") > -1:
                    r_ques_no = r_value[r_value.rfind('_') + 1:]
                    end = r_value.index(" gap_")
                    ques_last_value = r_value[0:end]
                #else:
                #    if r_value['RESPONSE_' + str(correct_qes_no)] is not None:
                #    elif value['RESPONSE'] is not None:
                #        r_ques_no = str(last_r_value_index)
                #        ques_last_value =  r_value

                correct_qes_no = 0
                for value in marking.correct_r_value:
                    correct_qes_no += 1
                    if value.find(" gap_") > -1:
                        ques_no = value[value.rfind('_') + 1:]
                        if r_ques_no == ques_no:
                            _is_correct = False
                            if r_value == value:
                                _is_correct = True

                            last_r_values.append({'no':str(correct_qes_no), 'value':ques_last_value, 'correct': _is_correct})
                            is_existent = True


                #if not is_existent:
                #    last_r_values.append({'no': str(len(last_r_values)+1), 'value': '', 'correct': False})

            if len(last_r_values) > 0:
                marking.verbal_last_r_value = last_r_values


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

    is_all_correct = True
    for _marking in markings:
        if _marking.is_correct is None or not _marking.is_correct:
            is_all_correct = False
        if not hasattr(_marking, 'verbal_correct_r_value'):
            is_verbal_all = False

    template_file = 'errornote/error_note.html'
    rendered_template = render_template(template_file, assessment_name=assessment_name,
                                        assessment_enroll_id=assessment_enroll_id,
                                        subject=test_subject_string,
                                        score=score, markings=markings, retry_session_key=retry_session_key,
                                        last_error_count=last_error_count, test_datetime=test_datetime,
                                        student_user_id=student_user_id, static_folder=current_app.static_folder,
                                        grade=grade, is_all_correct=is_all_correct, is_verbal=is_verbal,
                                        is_verbal_all=is_verbal_all)
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
