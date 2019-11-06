from collections import namedtuple
from datetime import datetime

from flask import render_template, flash, request
from flask_login import login_required, current_user

from . import report
from .forms import ReportSearchForm, ItemSearchForm
from .. import db
from ..api.reports import draw_report
from ..decorators import permission_required
from ..models import Codebook, Permission, AssessmentEnroll, Assessment, EducationPlanDetail, \
    refresh_mviews, Item, Marking


@report.route('/my_report', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def list_my_report():
    student_id = current_user.id
    column_names = ['id',
                    'assessment_id',
                    'student_id',
                    'year',
                    'test_type',
                    'name',
                    'branch_id',
                    'subject_1',
                    'subject_2',
                    'subject_3',
                    'subject_4',
                    'subject_5'
                    ]
    sql_stmt = 'SELECT {columns} ' \
               'FROM my_report_list_v ' \
               ' WHERE student_id=:student_id'.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt, {'student_id': student_id})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]
    return render_template("report/my_report_list.html", assessment_enrolls=rows)


@report.route('/student/set/<int:assessment_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def my_student_set_report(assessment_id):
    student_id = current_user.id

    assessment_enrolls = AssessmentEnroll.query.filter_by(assessment_id=assessment_id).filter_by(
        student_id=student_id).all()
    if assessment_enrolls:
        grade = EducationPlanDetail.get_grade(assessment_id)
        assessment_GUID = assessment_enrolls[0].assessment_guid
        test_type_string = Codebook.get_code_name(assessment_enrolls[0].assessment.test_type)
        if test_type_string == 'Naplan':
            column_names = ['assessment_id',
                            'testset_id',
                            'student_id',
                            'percentile_score',
                            'median',
                            'percentile_20',
                            'percentile_80'
                            ]
            sql_stmt = 'SELECT {columns} ' \
                       'FROM test_summary_mview ' \
                       'WHERE student_id = :student_id ' \
                       'AND assessment_id = :assessment_id ' \
                       'AND testset_id = :testset_id '.format(columns=','.join(column_names))
            assessment_json = {}
            for assessment in assessment_enrolls:
                student_score, average_score = 0, 0
                testset_id = assessment.testset_id
                cursor = db.session.execute(sql_stmt, {'assessment_id': assessment_id, 'testset_id': testset_id,
                                                       'student_id': student_id})
                Record = namedtuple('Record', cursor.keys())
                rows = [Record(*r) for r in cursor.fetchall()]
                for row in rows:
                    student_score = row.percentile_score
                    average_score = row.median
                    percentile_20 = row.percentile_20
                    percentile_80 = row.percentile_80
                    subject_name = Codebook.get_subject_name(testset_id)
                    # Todo: need update if clause
                    subject = ''
                    if subject_name == 'LC':
                        column_names_sub = ['code_name',
                                            'percentile_score',
                                            'median',
                                            'percentile_20',
                                            'percentile_80'
                                            ]
                        sql_stmt_sub = 'SELECT {columns} ' \
                                       'FROM test_summary_by_category_v ' \
                                       'WHERE student_id = :student_id ' \
                                       'AND assessment_id = :assessment_id ' \
                                       'AND testset_id = :testset_id '.format(columns=','.join(column_names_sub))
                        cursor_sub = db.session.execute(sql_stmt_sub,
                                                        {'assessment_id': assessment_id, 'testset_id': testset_id,
                                                         'student_id': student_id})
                        Record = namedtuple('Record', cursor_sub.keys())
                        sub_rows = [Record(*r) for r in cursor_sub.fetchall()]
                        lc_spelling_score, lc_spelling_average_score, lc_spelling_percentile_20, lc_spelling_percentile_80 = 0, 0, 0, 0
                        lc_other_score, lc_other_average_score, lc_other_percentile_20, lc_other_percentile_80 = 0, 0, 0, 0
                        for sub_row in sub_rows:
                            if sub_row.code_name == 'spelling':
                                lc_spelling_score = sub_row.percentile_score
                                lc_spelling_average_score = sub_row.median
                                lc_spelling_percentile_20 = sub_row.percentile_20
                                lc_spelling_percentile_80 = sub_row.percentile_80
                            else:
                                lc_other_score = lc_other_score + sub_row.percentile_score
                                lc_other_average_score = lc_other_average_score + sub_row.median
                                lc_other_percentile_20 = lc_other_percentile_20 + sub_row.percentile_20
                                lc_other_percentile_80 = lc_other_percentile_80 + sub_row.percentile_80
                        assessment_json['spelling'] = {
                            "student": lc_spelling_score,
                            "average": lc_spelling_average_score,
                            "sixty": (lc_spelling_percentile_20, lc_spelling_percentile_80)}
                        assessment_json['grammar'] = {
                            "student": lc_other_score,
                            "average": lc_other_average_score,
                            "sixty": (lc_other_percentile_20, lc_other_percentile_80)}
                    else:
                        if subject_name == 'RC':
                            assessment_json["reading"] = {
                                "student": student_score,
                                "average": average_score,
                                "sixty": (percentile_20, percentile_80)}
                        elif subject_name == 'Math':
                            assessment_json["numeracy"] = {
                                "student": student_score,
                                "average": average_score,
                                "sixty": (percentile_20, percentile_80)}

            scores = {
                "grade": grade,
                "assessment_GUID": assessment_GUID,
                "student_id": student_id,
                "assessments": assessment_json
            }
            file_name = draw_report(scores)
        else:
            # For selective test or other test type
            test_type_string = 'other'
    template_html_name = 'report/my_report_' + test_type_string + '.html'
    return render_template(template_html_name, file_name=file_name)


@report.route('/ts/<int:assessment_id>/<int:ts_id>/<int:student_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def my_report(assessment_id, ts_id, student_id):
    refresh_mviews()
    assessment_enroll_id = (AssessmentEnroll.query.with_entities(AssessmentEnroll.id). \
                            filter_by(assessment_id=assessment_id). \
                            filter_by(testset_id=ts_id). \
                            filter_by(student_id=student_id).order_by(AssessmentEnroll.id.desc()).first()).id
    assessment_name = (Assessment.query.with_entities(Assessment.name).filter_by(id=assessment_id).first()).name

    # ##
    # My Report : Header - Number_of_enrolls, Student Name/ID/Grade, Ranking, Score/TotalScore, TestDate
    # ##
    column_names = ['rank_v as student_rank',
                    'total_students',
                    "to_char(score,'999.99') as score",
                    "to_char(total_score,'999.99') as total_score",
                    "to_char(percentile_score,'999.99') as percentile_score"
                    ]
    sql_stmt = 'SELECT {columns} ' \
               'FROM test_summary_mview ' \
               'WHERE assessment_id=:assessment_id and testset_id=:testset_id ' \
               'and student_id=:student_id'.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt,
                                {'assessment_id': assessment_id, 'testset_id': ts_id, 'student_id': student_id})
    ts_header = cursor.fetchone()
    score = '{} out of {} ({}%)'.format(ts_header.score, ts_header.total_score, ts_header.percentile_score)
    rank = '{} out of {}'.format(ts_header.student_rank, ts_header.total_students)

    # ##
    # My Report : Body - Item ID/Candidate Value/IsCorrect/Correct_Value, Correct_percentile, Item Category
    # ##
    column_names_1 = ['assessment_enroll_id',
                      'testset_id',
                      'candidate_r_value',
                      'student_id',
                      'grade',
                      "to_char(created_time,'YYYY-MM-DD Dy') as created_time",
                      'is_correct',
                      'correct_r_value',
                      'item_percentile',
                      'item_id',
                      'category'
                      ]
    sql_stmt_1 = 'SELECT {columns} ' \
                 'FROM my_report_body_v ' \
                 'WHERE assessment_enroll_id=:assessment_enroll_id and testset_id=:testset_id'.format(
        columns=','.join(column_names_1))
    cursor_1 = db.session.execute(sql_stmt_1, {'assessment_enroll_id': assessment_enroll_id, 'testset_id': ts_id})
    Record = namedtuple('Record', cursor_1.keys())
    markings = [Record(*r) for r in cursor_1.fetchall()]

    # ##
    # My Report : Footer - Candidate Avg Score / Total Avg Score by Item Category
    # ##
    column_names_2 = ['code_name as category',
                      "to_char(score,'999.99') as score",
                      "to_char(total_score,'999.99') as total_score",
                      "to_char(avg_score,'999.99') as avg_score",
                      "to_char(percentile_score,'999.99') as percentile_score"
                      ]
    sql_stmt_2 = 'SELECT {columns} ' \
                 'FROM test_summary_by_category_v ' \
                 'WHERE student_id = :student_id ' \
                 'AND assessment_id = :assessment_id ' \
                 'ORDER BY category'.format(columns=','.join(column_names_2))
    cursor_2 = db.session.execute(sql_stmt_2, {'assessment_id': assessment_id, 'student_id': student_id})
    Record = namedtuple('Record', cursor_2.keys())
    ts_by_category = [Record(*r) for r in cursor_2.fetchall()]
    return render_template("report/my_report.html", assessment_name=assessment_name, rank=rank,
                           score=score, markings=markings, ts_by_category=ts_by_category)


@report.route('/summary/<int:plan_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_EXEC)
def test_summary_report(plan_id):
    # Todo: change student_id
    student_id = 8
    # student_id = current_user.id

    # ##
    # Individual Progress Report : Header
    # ##
    column_names_1 = ['year',
                      'grade',
                      'test_type'
                      ]
    sql_stmt_1 = 'SELECT DISTINCT {columns} ' \
                 'FROM csedu_education_plan_v ' \
                 ' WHERE plan_id=:plan_id '.format(columns=','.join(column_names_1))
    cursor_1 = db.session.execute(sql_stmt_1, {'plan_id': plan_id})
    ts_header = cursor_1.fetchone()
    test_type_string = Codebook.get_code_name(ts_header.test_type)
    if test_type_string!='Naplan':
        test_type_string = 'other'
    # ##
    # Individual Progress Report : Body - Summary Report
    # ##

    column_names_all = ['p.plan_id', 'p."order"', 'p.assessment_id',
                        'p.student_id',
                        "to_char(coalesce(p.score,0),'999.99') as my_set_score",
                        "p.rank_v",
                        "to_char(coalesce(p.avg_score,0),'999.99') as avg_set_score"
                        ]
    sql_stmt_all = 'SELECT DISTINCT {columns} ' \
                   'FROM test_summary_by_assessment_v p ' \
                   ' WHERE p.plan_id = :plan_id ' \
                   '  AND student_id = :student_id ' \
                   ' ORDER BY p.plan_id, p."order" '.format(columns=','.join(column_names_all))
    cursor_all = db.session.execute(sql_stmt_all, {'plan_id': plan_id, 'student_id': student_id})
    Record = namedtuple('Record', cursor_all.keys())
    rows_all = [Record(*r) for r in cursor_all.fetchall()]

    column_names = ['p.plan_id', 'p."order"', 'p.assessment_id',
                    'p.testset_id',
                    'ts.student_id',
                    "to_char(coalesce(ts.score,0),'999.99') as score",
                    "to_char(coalesce(ts.total_score,0),'999.99') as total_score",
                    "to_char(coalesce(ts.avg_score,0),'999.99') as avg_score",
                    "to_char(coalesce(ts.percentile_score,0),'999.99') as percentile_score",
                    "coalesce(ts.rank_v,0) as rank_v",
                    'coalesce(ts.total_students,0) as total_students'
                    ]
    sql_stmt = 'SELECT {columns} ' \
               'FROM csedu_education_plan_v p left join test_summary_mview ts ' \
               ' ON p.assessment_id = ts.assessment_id and p.testset_id = ts.testset_id ' \
               ' WHERE p.plan_id = :plan_id ' \
               '  AND student_id = :student_id ' \
               ' ORDER BY p.plan_id, p."order", p.testset_id'.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt, {'plan_id': plan_id, 'student_id': student_id})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]

    my_assessment = []
    my_subject_score = []  # my_score by subject
    avg_subject_score = []  # avg_score by subject

    my_set_score = []
    my_set_rank = []
    avg_set_score = []

    # Fill in my_assessment - my_testset which are displayed as individual subject score on report
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
    # re-construct data to display properly on the template html page
    subject_names = []
    num_of_subjects = 0
    num_of_assessments = len(my_assessment)
    subject_score_by_assessment = []
    subjects = []
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

    #
    # # -- 학생이 친 시험 과목별 평균점수, rank, 최저점, 최고점
    column_names = ['plan_id', 'testset_id', 'student_id',
                    'rank_v',
                    "to_char(coalesce(subject_avg_my_score,0),'999.99') as subject_avg_my_score,"
                    "to_char(coalesce(subject_avg_avg_score,0),'999.99') as subject_avg_avg_score",
                    "to_char(coalesce(subject_avg_min_score,0),'999.99') as subject_avg_min_score",
                    "to_char(coalesce(subject_avg_max_score,0),'999.99') as subject_avg_max_score"
                    ]
    sql_stmt = 'SELECT {columns} ' \
               'from test_summary_by_subject_v ts' \
               ' WHERE plan_id = :plan_id ' \
               ' AND student_id =:student_id ' \
               ' ORDER BY testset_id'.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt, {'plan_id': plan_id, 'student_id': student_id})
    Record = namedtuple('Record', cursor.keys())
    total_subject_scores = [Record(*r) for r in cursor.fetchall()]

    #
    # # -- 학생이 친 시험 전체(plan package단위) 점수, rank, 최저점, 최고점
    column_names = ['plan_id', 'student_id',
                    'rank_v',
                    "to_char(coalesce(sum_my_score,0)/" + str(num_of_assessments) + ",'999.99') as sum_my_score",
                    "to_char(coalesce(sum_avg_score,0)/" + str(num_of_assessments) + ",'999.99') as sum_avg_score",
                    "to_char(coalesce(sum_min_score,0)/" + str(num_of_assessments) + ",'999.99') as sum_min_score",
                    "to_char(coalesce(sum_max_score,0)/" + str(num_of_assessments) + ",'999.99') as sum_max_score"
                    ]
    sql_stmt = 'SELECT {columns} ' \
               'from test_summary_by_plan_v ts' \
               ' WHERE plan_id = :plan_id ' \
               ' AND student_id =:student_id '.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt, {'plan_id': plan_id, 'student_id': student_id})
    total_score = cursor.fetchone()

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

    template_file_name = 'report/individual_progress_' + test_type_string + '.html'
    return render_template(template_file_name, ts_header=ts_header,
                           num_of_assessments=num_of_assessments, num_of_subjects=num_of_subjects,
                           subject_names=subject_names,
                           subjects=subjects, my_set_score=my_set_score,
                           avg_set_score=avg_set_score, my_set_rank=my_set_rank,
                           score_summaries=score_summaries, plan_id=plan_id)


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

    rows = []
    column_names = ['plan_id',
                    'plan_name',
                    '"year" as assessment_year',
                    'grade',
                    'test_type',
                    '"order" as assessment_order',
                    'assessment_id',
                    'testset_id',
                    'id as assessment_enroll_id',
                    'student_id',
                    'attempt_count',
                    'test_center',
                    'start_time_client'
                    ]
    sql_stmt = 'SELECT {columns} ' \
               'FROM csedu_plan_assessment_testsets_enrolled_v '.format(columns=','.join(column_names))
    sql_stmt_sub = ''
    reports = []
    students = []
    testsets = []
    test_summaries = []
    if flag:
        if test_type:
            sql_stmt_sub = sql_stmt_sub + 'AND test_type = :test_type '
        if test_center:
            if Codebook.get_code_name(test_center)!='All':
                sql_stmt_sub = sql_stmt_sub + 'AND test_center = :test_center '
        if year:
            sql_stmt_sub = sql_stmt_sub + 'AND "year" = :year '
        sql_stmt = sql_stmt + sql_stmt_sub.replace('AND', 'WHERE', 1)
        sql_stmt = sql_stmt + ' ORDER BY plan_id, assessment_order, testset_id, test_center,student_id'
        cursor = db.session.execute(sql_stmt, {'test_type': test_type, 'test_center': test_center, 'year': year})
        Record = namedtuple('Record', cursor.keys())
        rows = [Record(*r) for r in cursor.fetchall()]
        index = 0
        _assessment_enroll_id, _testset_id, _test_center, _assessment_year, _assessment_order = 0, 0, 0, 0, 0
        _assessment_id, _grade, _test_type = 0, 0, 0
        for row in rows:
            if index>0 and \
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
        # Test Summary Report for All Students
        # Todo: Change student_id
        student_id = 8
        column_names_1 = ['student_id',
                          'plan_id',
                          'plan_name',
                          'year',
                          'grade',
                          'test_type'
                          ]
        sql_stmt_1 = 'SELECT distinct {columns} ' \
                     'FROM my_report_progress_summary_v ' \
                     ' WHERE student_id=:student_id'.format(columns=','.join(column_names_1))
        cursor_1 = db.session.execute(sql_stmt_1, {'student_id': student_id})
        Record = namedtuple('Record', cursor_1.keys())
        test_summaries = [Record(*r) for r in cursor_1.fetchall()]
    return render_template('report/manage.html', form=search_form, reports=reports,
                           test_summaries=test_summaries, test_center=test_center)


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


@report.route('/score_summary/<int:item_id>', methods=['GET'])
@login_required
@permission_required(Permission.ITEM_MANAGE)
def score_summary(item_id):
    rows = []
    # grouping : 'by_item_assessment', 'by_item'
    column_names = ['item_id',
                    'grouping',
                    'assessment_id',
                    'assessment_name',
                    'number_of_exec',
                    'percentile_correct'
                    ]
    sql_stmt = 'SELECT {columns} ' \
               'FROM item_score_summary_v ' \
               'WHERE item_id = :item_id ' \
               'ORDER BY assessment_name '.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt, {'item_id': item_id})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]
    by_assessment = []
    by_item = None
    for row in rows:
        if row.grouping == 'by_item':
            by_item = row
        elif row.grouping == 'by_item_assessment':
            by_assessment.append(row)
    item = Item.query.filter_by(id=item_id).first()
    return render_template('report/score_summary.html', by_item=by_item, by_assessment=by_assessment, item=item)


@report.route('/list/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:test_center>',
              methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_READ)
def list(year, test_type, sequence, assessment_id, test_center):
    column_names = ['att.testset_id',
                    '(select cb.code_name ' \
                        + ' from testset ts, codebook cb ' \
                        + ' where att.testset_id=ts.id ' \
                        + ' and ts.subject = cb.id ' \
                        + " and cb.code_type = 'subject') as subject_name"]
    sql_stmt = 'SELECT distinct {columns} ' \
               'FROM assessment_testsets as att, assessment_enroll as ae' \
               ' WHERE att.assessment_id = ae.assessment_id ' \
                ' AND  att.assessment_id = :assessment_id ' \
               ' ORDER BY 1 ASC'.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt, {'assessment_id': assessment_id})
    Record = namedtuple('Record', cursor.keys())
    subjects = [Record(*r) for r in cursor.fetchall()]

    # Original SQL Statement for student_ranking report
    # sql_stmt = WITH test_result_by_subject AS(
    #     SELECT test_summary_v.row_name[1] AS student_id,
    #             test_summary_v.row_name[2] AS assessment_id,
    #             test_summary_v."2",
    #             test_summary_v."3",
    #             test_summary_v."4",
    #             COALESCE(NULLIF(test_summary_v."2", 0::double precision), 0::double precision)
    #             + COALESCE(NULLIF(test_summary_v."3", 0::double precision), 0::double precision)
    #             + COALESCE(NULLIF(test_summary_v."4", 0::double precision), 0::double precision) AS total_mark
    #     FROM crosstab('select ARRAY[student_id::integer,assessment_id::integer] as row_name, testset_id, my_score
    #                     from (SELECT m.student_id,
    #                             m.assessment_id,
    #                             m.testset_id,
    #                             m.score AS my_score
    #                             FROM marking_summary_360_degree_mview m
    #                             where student_id is not null
    #                             and m.assessment_id = 2) test_summary_v
    #                     order by 1, 2 ',
    #                     'select distinct att.testset_id
    #                         from assessment_testsets as att join assessment_enroll as ae
    #                         on att.assessment_id = ae.assessment_id
    #                         where att.assessment_id = 2
    #                         order by 1')
    #     AS test_summary_v(row_name integer[], "2" double precision, "3" double precision, "4" double precision)
    # )
    # SELECT trs.student_id,
    #     (select s.student_id from student s where s.user_id=trs.student_id) AS cs_student_id,
    #       (select u.username from users u where u.id=trs.student_id) AS student_name,
    #     trs.assessment_id,
    #     a.test_center,
    #     trs."2" as subject_1,
    #     trs."3" as subject_2,
    #     trs."4" as subject_3,
    #     trs.total_mark,
    #     rank() OVER(PARTITION BY trs.assessment_id ORDER BY trs.total_mark DESC) AS student_rank
    # FROM
    # test_result_by_subject trs,
    #     (SELECT DISTINCT assessment_enroll.assessment_id,
    #     assessment_enroll.student_id,
    #     assessment_enroll.test_center
    #     FROM assessment_enroll) a
    # WHERE trs.assessment_id = a.assessment_id
    # AND trs.student_id = a.student_id;

    sql_stmt = ' WITH test_result_by_subject AS( ' \
                + ' SELECT test_summary_v.row_name[1] AS student_id, '\
                + ' test_summary_v.row_name[2] AS assessment_id, '
    for subject in subjects:
        sql_stmt = sql_stmt + ' test_summary_v.'+subject.subject_name+', '
    index = 1
    for subject in subjects:
        if index!=1:
            sql_stmt = sql_stmt + '+'
        sql_stmt = sql_stmt \
                + ' COALESCE(NULLIF(test_summary_v.'+subject.subject_name+', 0::double precision), 0::double precision)'
        index += 1
    sql_stmt = sql_stmt + ' AS total_mark '
    sql_stmt = sql_stmt \
        + " FROM crosstab('select ARRAY[student_id::integer,assessment_id::integer] as row_name, testset_id, my_score "  \
        + "                  from (SELECT m.student_id, " \
        + "                            m.assessment_id, " \
        + "                             m.testset_id, " \
        + "                            m.score AS my_score "\
        + "                            FROM marking_summary_360_degree_mview m " \
        + "                            where student_id is not null " \
        + "                            and m.assessment_id = :assessment_id) test_summary_v " \
        + "                        order by 1, 2 ', " \
        + "                        'select distinct att.testset_id " \
        + "                            from assessment_testsets as att join assessment_enroll as ae " \
        + "                            on att.assessment_id = ae.assessment_id " \
        + "                            where att.assessment_id = :assessment_id " \
        + "                            order by 1') "
    sql_stmt = sql_stmt + ' AS test_summary_v(row_name integer[], '
    index = 1
    for subject in subjects:
        sql_stmt = sql_stmt + subject.subject_name + ' double precision'
        if index<len(subjects):
            sql_stmt = sql_stmt +', '
        index += 1
    sql_stmt = sql_stmt + ') )'
    sql_stmt = sql_stmt  \
        + " SELECT trs.student_id, "\
        + "     (select s.student_id from student s where s.user_id=trs.student_id) AS cs_student_id, " \
        + "     (select u.username from users u where u.id=trs.student_id) AS student_name, " \
        + "     trs.assessment_id, " \
        + "      a.test_center, "
    index = 1
    for subject in subjects:
        sql_stmt = sql_stmt + 'trs.'+ subject.subject_name + ' as subject_'+str(index)+', '
        index += 1
    sql_stmt = sql_stmt  \
        + ' trs.total_mark, '\
        + ' rank() OVER(PARTITION BY trs.assessment_id ORDER BY trs.total_mark DESC) AS student_rank '\
        + ' FROM test_result_by_subject trs, '\
        + ' (SELECT DISTINCT assessment_enroll.assessment_id, '\
        + '     assessment_enroll.student_id, '\
        + '     assessment_enroll.test_center '\
        + '     FROM assessment_enroll) a '\
        + ' WHERE trs.assessment_id = a.assessment_id '\
        + ' AND trs.student_id = a.student_id '

    cursor = db.session.execute(sql_stmt, {'assessment_id': assessment_id})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]

    # rank students from all test candidates
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
    if request.args.get('excel-download') == "1":
        rsp = build_test_result_excel_response(subjects, test_summaries, year, test_type, sequence)
        return rsp
    elif request.args.get('excel-download') == "0":
        pass
        # rsp = build_test_result_pdf_response(test_summaries)
        # return rsp

    return render_template(template_file_name,
                           year=year, test_type=test_type, sequence=sequence,
                           subject_names=subjects,
                           test_summaries=test_summaries, now=datetime.utcnow())

def build_test_result_excel_response(subjects, test_summaries, year, test_type, sequence):
    """
    test_result_summary 를 받아서 엑셀로 export 하는 response object 를 만듭니다.
    :param test_summaries: test_summary query object list
    :return: flask response object
    """
    import io
    import time
    import unidecode
    from urllib import parse
    from flask import send_file
    import xlsxwriter

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('Test Ranking')

    row, col = 0, 0
    # Excel header list
    headers = ["No.", "Student No.", "Name" ]
    for subject in subjects:
        headers.append(subject.subject_name)
    headers.append("Total")
    headers.append("Ranking")
    headers.append("Branch Name")
    for header in headers:
        worksheet.write(row, col, header)
        col += 1

    # test_summaries object 에서 Excel 로 export 할 attribute
    attributes = ["cs_student_id", "student_name"]
    for i in range(1,len(subjects)+1):
        attributes.append("subject_"+str(i))
    attributes.append("total_mark")
    attributes.append("student_rank")
    attributes.append("test_center")

    for ts in test_summaries:
        row += 1
        worksheet.write(row, 0, str(col+1))
        col = 1
        for attr in attributes:
            if attr == "test_center":
                tc = getattr(ts, attr)
                worksheet.write(row, col, Codebook.get_code_name(tc))
            else:
                worksheet.write(row, col, getattr(ts, attr))
            col += 1

    workbook.close()
    output.seek(0)
    file_name = 'test_ranking_%s_%s_%s_%s.xlsx' % (year, test_type, sequence, int(time.time()))

    # response object 생성
    rsp = send_file(
        io.BytesIO(output.read()), as_attachment=True,
        attachment_filename=file_name,
        mimetype='application/vnd.ms-excel'
    )
    rsp.headers["Content-Disposition"] = \
        "attachment;" \
        "filename={ascii_filename};" \
        "filename*=UTF-8''{utf_filename}".format(
            ascii_filename=unidecode.unidecode(file_name).replace(' ', '_'),
            utf_filename=parse.quote(file_name)
        )

    return rsp


@report.route('/results/pdf/<string:year>/<int:test_type>/<int:sequence>/<int:assessment_id>/<int:branch_id>',
              methods=['GET'])
@login_required
@permission_required(Permission.ASSESSMENT_READ)
def report_results_pdf(year, test_type, sequence, assessment_id, branch_id):
    query = db.session.query(AssessmentEnroll.id, AssessmentEnroll.student_id).distinct()
    # Todo: Need to check if current_user have access right on queried data
    test_center = Codebook.get_testcenter_of_current_user()
    if not test_center and (current_user.role.name == 'Moderator' or current_user.role.name == 'Administrator'):
        test_center = Codebook.query.filter_by(code_type='test_center').filter_by(code_name='All').first()
    if (test_center.id == branch_id):

        # Get Assessment Enrolled Students
        if not (test_center.code_name == 'All'):
            query = query.filter_by(test_center=branch_id)
        enrolled_students = query.order_by(AssessmentEnroll.testset_id).all()

        if enrolled_students:
            # Assessment General Info
            assessment = db.session.query(Assessment.GUID, Assessment.test_type).filter(
                Assessment.id == assessment_id).first()
            assessment_GUID = assessment.GUID
            test_type_string = Codebook.get_code_name(assessment.test_type)
            grade = EducationPlanDetail.get_grade(assessment_id)

        for enrolled_student in enrolled_students:
            student_id = enrolled_student.student_id
            student_enrolls = AssessmentEnroll.query.filter_by(assessment_id=assessment_id).filter_by(
                student_id=student_id).all()
            # ##
            # Report : Naplan Graph
            # ##
            if test_type_string == 'Naplan':
                column_names = ['assessment_id',
                                'testset_id',
                                'student_id',
                                'percentile_score',
                                'median',
                                'percentile_20',
                                'percentile_80'
                                ]
                sql_stmt = 'SELECT {columns} ' \
                           'FROM test_summary_mview ' \
                           'WHERE student_id = :student_id ' \
                           'AND assessment_id = :assessment_id ' \
                           'AND testset_id = :testset_id '.format(columns=','.join(column_names))

                # ##
                # Report : Marking Detail Body - Item ID/Candidate Value/IsCorrect/Correct_Value, Correct_percentile, Item Category
                # ##
                column_names_1 = ['assessment_enroll_id',
                                  'testset_id',
                                  'candidate_r_value',
                                  'student_id',
                                  'grade',
                                  "to_char(created_time,'YYYY-MM-DD Dy') as created_time",
                                  'is_correct',
                                  'correct_r_value',
                                  'item_percentile',
                                  'item_id',
                                  'category'
                                  ]
                sql_stmt_1 = 'SELECT {columns} ' \
                             'FROM my_report_body_v ' \
                             'WHERE assessment_enroll_id=:assessment_enroll_id and testset_id=:testset_id'.format(
                    columns=','.join(column_names_1))

                assessment_json = {}
                subject_markings = {}
                subjects = []
                for student_enroll in student_enrolls:
                    enroll_id = student_enroll.id
                    testset_id = student_enroll.testset_id
                    # ##
                    # Report : Marking Detail Body - Item ID/Candidate Value/IsCorrect/Correct_Value, Correct_percentile, Item Category
                    # ##
                    cursor_1 = db.session.execute(sql_stmt_1,
                                                  {'assessment_enroll_id': enroll_id, 'testset_id': testset_id})
                    Record = namedtuple('Record', cursor_1.keys())
                    markings = [Record(*r) for r in cursor_1.fetchall()]
                    subject_markings = {"testset_id": testset_id, "markings": markings}
                    subjects.append(subject_markings)
                    # ##
                    # Report : Naplan Graph
                    # ##
                    student_score, average_score = 0, 0
                    cursor = db.session.execute(sql_stmt, {'assessment_id': assessment_id, 'testset_id': testset_id,
                                                           'student_id': student_id})
                    Record = namedtuple('Record', cursor.keys())
                    rows = [Record(*r) for r in cursor.fetchall()]
                    for row in rows:
                        student_score = row.percentile_score
                        average_score = row.median
                        percentile_20 = row.percentile_20
                        percentile_80 = row.percentile_80
                        subject_name = Codebook.get_subject_name(testset_id)
                        # Todo: need update if clause
                        subject = ''
                        if subject_name == 'LC':
                            column_names_sub = ['code_name',
                                                'percentile_score',
                                                'median',
                                                'percentile_20',
                                                'percentile_80'
                                                ]
                            sql_stmt_sub = 'SELECT {columns} ' \
                                           'FROM test_summary_by_category_v ' \
                                           'WHERE student_id = :student_id ' \
                                           'AND assessment_id = :assessment_id ' \
                                           'AND testset_id = :testset_id '.format(columns=','.join(column_names_sub))
                            cursor_sub = db.session.execute(sql_stmt_sub,
                                                            {'assessment_id': assessment_id, 'testset_id': testset_id,
                                                             'student_id': student_id})
                            Record = namedtuple('Record', cursor_sub.keys())
                            sub_rows = [Record(*r) for r in cursor_sub.fetchall()]
                            lc_spelling_score, lc_spelling_average_score, lc_spelling_percentile_20, lc_spelling_percentile_80 = 0, 0, 0, 0
                            lc_other_score, lc_other_average_score, lc_other_percentile_20, lc_other_percentile_80 = 0, 0, 0, 0
                            for sub_row in sub_rows:
                                if sub_row.code_name == 'spelling':
                                    lc_spelling_score = sub_row.percentile_score
                                    lc_spelling_average_score = sub_row.median
                                    lc_spelling_percentile_20 = sub_row.percentile_20
                                    lc_spelling_percentile_80 = sub_row.percentile_80
                                else:
                                    lc_other_score = lc_other_score + sub_row.percentile_score
                                    lc_other_average_score = lc_other_average_score + sub_row.median
                                    lc_other_percentile_20 = lc_other_percentile_20 + sub_row.percentile_20
                                    lc_other_percentile_80 = lc_other_percentile_80 + sub_row.percentile_80
                            assessment_json['spelling'] = {
                                "student": lc_spelling_score,
                                "average": lc_spelling_average_score,
                                "sixty": (lc_spelling_percentile_20, lc_spelling_percentile_80)}
                            assessment_json['grammar'] = {
                                "student": lc_other_score,
                                "average": lc_other_average_score,
                                "sixty": (lc_other_percentile_20, lc_other_percentile_80)}
                        else:
                            if subject_name == 'RC':
                                assessment_json["reading"] = {
                                    "student": student_score,
                                    "average": average_score,
                                    "sixty": (percentile_20, percentile_80)}
                            elif subject_name == 'Math':
                                assessment_json["numeracy"] = {
                                    "student": student_score,
                                    "average": average_score,
                                    "sixty": (percentile_20, percentile_80)}

                scores = {
                    "grade": grade,
                    "assessment_GUID": assessment_GUID,
                    "student_id": student_id,
                    "assessments": assessment_json
                }
                file_name = draw_report(scores)
            else:
                # For selective test or other test type
                test_type_string = 'other'

            template_html_name = 'report/results_pdf_' + test_type_string + '.html'
            # ToDo: Need to remove return statement and continue to loop without break
            rendered_template = render_template(template_html_name, file_name=file_name, subjects=subjects)
            from weasyprint import HTML, CSS
            from weasyprint.fonts import FontConfiguration
            font_config = FontConfiguration()
            css = CSS(string='''
                @font-face {
                    font-family: Gentium;
                    src: url(http://example.com/fonts/Gentium.otf);
                }
                h1 { font-family: Gentium }''', font_config=font_config)
            html = HTML(string=rendered_template)
            html.write_pdf(target='./tmp.pdf',
                           presentational_hints=True)

            return rendered_template
    else:
        return 'Invalid Request'
