import os
from collections import namedtuple
from datetime import datetime

from PIL import Image, ImageDraw
from flask import current_app, render_template, request
from flask_login import current_user
from sqlalchemy import text

from app.api import api
from app.decorators import permission_required
from app.models import Permission, refresh_mviews, Codebook, AssessmentEnroll, Student, Marking, Assessment, Testset, \
    MarkingForWriting
from common.logger import log
from .response import success
from .. import db

'''Student Naplan Report - graph mapping for drawing picture '''
graph_mapping = {
    "column_coords": {
        "ceiling": 558,
        "floor": 2433,
        "reading": {
            "centre": 818,  # Centre of the reading column
            "offset": 74,  # Offset between center and side
            "offset_direction": 1  # -1 for left, 1 for right
        },
        "writing": {
            "centre": 1635,  # Centre of the reading column
            "offset": 74,  # Offset between center and side
            "offset_direction": 1  # -1 for left, 1 for right
        },
        "grammar": {
            "centre": 1996,  # Centre of the reading column
            "offset": 74,  # Offset between center and side
            "offset_direction": -1  # -1 for left, 1 for right
        },
        "spelling": {
            "centre": 2602,  # Centre of the reading column
            "offset": 74,  # Offset between center and side
            "offset_direction": 1  # -1 for left, 1 for right
        },
        "numeracy": {
            "centre": 3440,  # Centre of the reading column
            "offset": 74,  # Offset between center and side
            "offset_direction": 1  # -1 for left, 1 for right
        }
    },
    "score_ranges": {
        "Y3": {
            "ceiling_score": 80,
            "floor_score": 50,
            "upper_limit": 100,
            "lower_limit": 50
        },
        "Y4": {
            "ceiling_score": 80,
            "floor_score": 50,
            "upper_limit": 100,
            "lower_limit": 0
        },
        "Y5": {
            "ceiling_score": 80,
            "floor_score": 50,
            "upper_limit": 100,
            "lower_limit": 0
        },
        "Y6": {
            "ceiling_score": 80,
            "floor_score": 50,
            "upper_limit": 100,
            "lower_limit": 0
        },
        "Y7": {
            "ceiling_score": 80,
            "floor_score": 50,
            "upper_limit": 100,
            "lower_limit": 0
        },
        "Y8": {
            "ceiling_score": 80,
            "floor_score": 50,
            "upper_limit": 80,
            "lower_limit": 0
        },
        "Y9": {
            "ceiling_score": 80,
            "floor_score": 50,
            "upper_limit": 80,
            "lower_limit": 0
        }
    }
}

'''Student Naplan Report - draw picture '''


def draw_report(result, student_user_id):
    # Read base image
    naplan_folder = os.path.join(current_app.config['USER_DATA_FOLDER'], str(student_user_id), "naplan")
    if not os.path.exists(naplan_folder):
        os.makedirs(naplan_folder)
    base = Image.open('%s/naplan-%s.png' % (current_app.config['NAPLAN_BASE_IMG_DIR'], result["grade"]))
    base.load()
    img = Image.new("RGB", base.size, (255, 255, 255))
    img.paste(base, mask=base.split()[3])

    # Graph-Score ratio
    ceiling_score = graph_mapping["score_ranges"][result["grade"]]["ceiling_score"]
    floor_score = graph_mapping["score_ranges"][result["grade"]]["floor_score"]
    upper_limit = graph_mapping["score_ranges"][result["grade"]]["upper_limit"]
    lower_limit = graph_mapping["score_ranges"][result["grade"]]["lower_limit"]
    ratio = (graph_mapping["column_coords"]["floor"] - graph_mapping["column_coords"]["ceiling"]) / (
            ceiling_score - floor_score)

    # Draw overlays
    dctx = ImageDraw.Draw(img, 'RGBA')
    size = int(50 / 2)
    margin = 10

    def get_y(score):
        # Limit the score to keep it within the range
        if score >= upper_limit:
            score = upper_limit
        if score <= lower_limit:
            score = lower_limit
        # Calculate y
        if score > ceiling_score:
            y = graph_mapping["column_coords"]["ceiling"] - size - margin
        elif score < floor_score:
            y = graph_mapping["column_coords"]["floor"] + size + margin
        else:
            y = graph_mapping["column_coords"]["ceiling"] + (ceiling_score - score) * ratio
        return y

    for assessment, scores in result["assessments"].items():
        # 60% box
        x = graph_mapping["column_coords"][assessment]["centre"]
        o = graph_mapping["column_coords"][assessment]["offset"] * graph_mapping["column_coords"][assessment][
            "offset_direction"]
        y1 = get_y(scores["sixty"][0])
        y2 = get_y(scores["sixty"][1])
        dctx.rectangle((x - o, y1, x + o, y2), fill=(222, 238, 245, 125), outline="black")

        # Average score
        x = graph_mapping["column_coords"][assessment]["centre"] + o
        y = get_y(scores["average"])
        if o >= 0:  # on right side
            dctx.polygon([(x, y), (x + size + margin, y + size), (x + size + margin, y - size)], fill="black",
                         outline="black")
        else:  # on left side
            dctx.polygon([(x, y), (x - (size + margin), y - size), (x - (size + margin), y + size)], fill="black",
                         outline="black")

        # Student score
        x = graph_mapping["column_coords"][assessment]["centre"]
        y = get_y(scores["student"])
        dctx.ellipse((x - size, y - size, x + size, y + size), fill="black", outline="black")

    del dctx
    img.format = "PNG"
    # img.show()
    file_name = 'naplan-grade-%s_%s_%s.png' % (result["grade"], result["student_user_id"], result["assessment_GUID"])
    naplan_folder = os.path.join(current_app.config['USER_DATA_FOLDER'], str(student_user_id), "naplan")
    img.save(os.path.join(naplan_folder, file_name))
    return file_name


'''Student UI - Student Naplan Report : Query data and return image file_name generated '''


def make_naplan_student_report(assessment_enrolls, assessment_id, student_user_id, assessment_GUID, grade):
    column_names = ['assessment_id',
                    'testset_id',
                    'student_user_id',
                    'percentile_score',
                    'median',
                    'percentile_20',
                    'percentile_80'
                    ]
    sql_stmt = 'SELECT {columns} ' \
               'FROM test_summary_mview ' \
               'WHERE student_user_id = :student_user_id ' \
               'AND assessment_id = :assessment_id ' \
               'AND testset_id = :testset_id '.format(columns=','.join(column_names))
    assessment_json = {}
    for assessment in assessment_enrolls:
        student_score, average_score = 0, 0
        testset_id = assessment.testset_id
        cursor = db.session.execute(sql_stmt, {'assessment_id': assessment_id, 'testset_id': testset_id,
                                               'student_user_id': student_user_id})
        Record = namedtuple('Record', cursor.keys())
        rows = [Record(*r) for r in cursor.fetchall()]
        if len(rows) == 0:
            return None
        for row in rows:
            student_score = row.percentile_score
            average_score = row.median
            percentile_20 = row.percentile_20
            percentile_80 = row.percentile_80
            subject_name = Codebook.get_subject_name(testset_id).strip()
            # Todo: need update if clause
            subject = ''
            if subject_name == 'Language Convention':
                column_names_sub = ['code_name',
                                    'percentile_score',
                                    'median',
                                    'percentile_20',
                                    'percentile_80'
                                    ]
                sql_stmt_sub = 'SELECT {columns} ' \
                               'FROM test_summary_by_category_v ' \
                               'WHERE student_user_id = :student_user_id ' \
                               'AND assessment_id = :assessment_id ' \
                               'AND testset_id = :testset_id '.format(columns=','.join(column_names_sub))
                cursor_sub = db.session.execute(sql_stmt_sub,
                                                {'assessment_id': assessment_id, 'testset_id': testset_id,
                                                 'student_user_id': student_user_id})
                Record = namedtuple('Record', cursor_sub.keys())
                sub_rows = [Record(*r) for r in cursor_sub.fetchall()]
                lc_spelling_score, lc_spelling_average_score, lc_spelling_percentile_20, lc_spelling_percentile_80 = 0, 0, 0, 0
                lc_other_score, lc_other_average_score, lc_other_percentile_20, lc_other_percentile_80 = 0, 0, 0, 0
                for sub_row in sub_rows:
                    if sub_row.code_name == 'Spelling':
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
                if subject_name == 'Reading Comprehension':
                    assessment_json["reading"] = {
                        "student": student_score,
                        "average": average_score,
                        "sixty": (percentile_20, percentile_80)}
                elif subject_name == 'Numeracy':
                    assessment_json["numeracy"] = {
                        "student": student_score,
                        "average": average_score,
                        "sixty": (percentile_20, percentile_80)}
    scores = {
        "grade": grade,
        "assessment_GUID": assessment_GUID,
        "student_user_id": student_user_id,
        "assessments": assessment_json
    }
    file_name = draw_report(scores, student_user_id)
    return file_name


'''Student UI: Query My Report List for each Student'''


def query_my_report_list_v(student_user_id):
    column_names = ['id',
                    'assessment_id',
                    'assessment_enroll_id',
                    'student_user_id',
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
               ' WHERE student_user_id=:student_user_id'.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt, {'student_user_id': student_user_id})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]
    return rows


'''Student UI: Query My Report (subject) Header for each Student'''


def query_my_report_header(assessment_enroll_id, assessment_id, ts_id, student_user_id):
    column_names = ['rank_v as student_rank',
                    'total_students',
                    "to_char(score,'999.99') as score",
                    "to_char(total_score,'999.99') as total_score",
                    "to_char(percentile_score,'999.99') as percentile_score"
                    ]

    # Combining the two tests
    '''
    sql_stmt = "SELECT " \
               "rank_v as student_rank, " \
               "total_students, " \
               "to_char(score,'999.99') as score, " \
               "to_char(total_score,'999.99') as total_score, " \
               "to_char(percentile_score,'999.99') as percentile_score, " \
               "(select count(distinct bbb.student_user_id) " \
               "from (select student_user_id, assessment_id, max(id) as id " \
               "from assessment_enroll " \
               "where assessment_id in (" \
               "  select id from assessment where id in(select assessment_id from education_plan_details aaaa where plan_id = test_summary_mview.plan_id) " \
               "                 and test_detail = (select test_detail from assessment where id =:assessment_id) " \
               ") " \
               "group by student_user_id, assessment_id " \
               ") bbb " \
               "where exists(select 1 from marking where assessment_enroll_id = bbb.id and student_user_id = bbb.student_user_id) " \
               ") AS total_students1, " \
    "( " \
    "    select student_rank " \
    "    from ( " \
    "        select student_user_id, rank() OVER(ORDER by score desc) as student_rank " \
    "        from ( " \
    "            select aaa.student_user_id, " \
    "                case when sum(bbb.outcome_score * bbb.weight) = 0 then 0 else " \
    "                    sum(bbb.candidate_mark * bbb.weight) * 100::double precision / sum(bbb.outcome_score * bbb.weight) end as score " \
    "            from (select student_user_id, assessment_id, max(id) as id from assessment_enroll " \
    "                    where assessment_id in ( " \
    "                        select id from assessment where id in (select assessment_id from education_plan_details aaaa where plan_id = test_summary_mview.plan_id) " \
    "                            and test_detail = (select test_detail from assessment where id =:assessment_id) " \
    "                           ) " \
    "                   group by student_user_id, assessment_id " \
    "                ) aaa " \
    "            join marking bbb " \
    "                on aaa.id = bbb.assessment_enroll_id " \
    "            group by aaa.student_user_id " \
    "        ) rnk " \
    "    ) tt " \
    "    where student_user_id = test_summary_mview.student_user_id " \
    ") as student_rank1 " \
"FROM test_summary_mview " \
               "WHERE assessment_enroll_id=:assessment_enroll_id " \
               "and assessment_id=:assessment_id and testset_id=:testset_id " \
               "and student_user_id=:student_user_id"
   '''

    sql_stmt = "SELECT " \
               "(select rnk from (select id, RANK () OVER (order by score desc) as rnk from assessment_enroll " \
               "where assessment_id = ae.assessment_id and testset_id = ae.testset_id) tt " \
               "where id = ae.id) as student_rank, " \
               "(select count(1) from assessment_enroll where assessment_id = ae.assessment_id " \
               "and testset_id = ae.testset_id) as total_students, " \
               "to_char(ae.score,'999.99') as score, " \
               "to_char(ae.total_score,'999.99') as total_score, " \
               "to_char(CASE WHEN ae.total_score is null or ae.total_score=0 then 0 else " \
               "round(((ae.score/ae.total_score) * 100)::numeric, 2) end,'999.99') as percentile_score " \
               "FROM assessment_enroll ae " \
               "WHERE id=:assessment_enroll_id"
    cursor = db.session.execute(sql_stmt,
                                {'assessment_enroll_id': assessment_enroll_id, 'assessment_id': assessment_id,
                                 'testset_id': ts_id, 'student_user_id': student_user_id})
    ts_header = cursor.fetchone()
    return ts_header


'''Student UI: Query My Report (subject) Body for each Student'''


def query_my_report_body(assessment_enroll_id, ts_id):
    column_names_1 = ['question_no',
                      'assessment_enroll_id',
                      'testset_id',
                      'testlet_id',
                      'candidate_r_value',
                      'student_user_id',
                      'grade',
                      "to_char(created_time,'YYYY-MM-DD Dy') as created_time",
                      "to_char(read_time,'YYYY-MM-DD Dy') as read_time",
                      'is_correct',
                      'correct_r_value',
                      'item_percentile',
                      'item_id',
                      'category',
                      'subcategory'
                      ]
    sql_stmt_1 = 'SELECT {columns} ' \
                 'FROM my_report_body_v ' \
                 'WHERE assessment_enroll_id=:assessment_enroll_id and testset_id=:testset_id ' \
                 'ORDER BY question_no asc'.format(
        columns=','.join(column_names_1))
    cursor_1 = db.session.execute(sql_stmt_1, {'assessment_enroll_id': assessment_enroll_id, 'testset_id': ts_id})
    Record = namedtuple('Record', cursor_1.keys())
    rows = [Record(*r) for r in cursor_1.fetchall()]
    return rows


'''Student UI: Query My Report (subject) Footer for each Student'''


def query_my_report_footer(assessment_id, student_user_id, assessment_enroll_id):
    column_names_2 = ['code_name as category',
                      "to_char(score,'999.99') as score",
                      "to_char(total_score,'999.99') as total_score",
                      "to_char(avg_score,'999.99') as avg_score",
                      "to_char(percentile_score,'999.99') as percentile_score"
                      ]

    sql_stmt_2 = "SELECT 1 as part," \
                 "code_name as category, " \
                 "to_char(score,'999.99') as score, " \
                 "to_char(total_score,'999.99') as total_score, " \
                 "to_char(avg_score,'999.99') as avg_score, " \
                 "to_char(percentile_score,'999.99') as percentile_score, " \
                 "(" \
                 "    select to_char(avg(score),'999.99')" \
                 "    from (" \
                 "       select code_name," \
                 "               case when sum(outcome_score * weight) = 0 then 0 else " \
                 "                   sum(candidate_mark * weight) * 100::double precision / sum(outcome_score * weight) end as score" \
                 "       from (" \
                 "               select aaa.student_user_id, bbb.outcome_score, bbb.weight, bbb.candidate_mark," \
                 "               (" \
                 "                   SELECT c.code_name" \
                 "                   FROM codebook c," \
                 "                       item i" \
                 "                   WHERE c.id = i.category" \
                 "                     and i.id = bbb.item_id" \
                 "               ) as code_name" \
                 "               from (select student_user_id, assessment_id, testset_id, max(id) as id from assessment_enroll" \
                 "              where assessment_id in (" \
                 "                       select id from assessment where id in (select assessment_id from education_plan_details aaaa where plan_id =" \
                 "                       (SELECT plan_id FROM education_plan_details WHERE assessment_id = test_summary_by_category_v.assessment_id)" \
                 "                       and test_detail = (select test_detail from assessment where id =test_summary_by_category_v.assessment_id)" \
                 "               ))" \
                 "        and testset_id = test_summary_by_category_v.testset_id" \
                 "        and student_user_id =:student_user_id" \
                 "        group by student_user_id, assessment_id, testset_id" \
                 "    ) aaa" \
                 "   join marking bbb" \
                 "     on aaa.id = bbb.assessment_enroll_id" \
                 "   ) aa" \
                 "   group by code_name" \
                 "   ) t" \
                 "   where code_name = test_summary_by_category_v.code_name" \
                 ") as avg_score1 " \
                 ", '' as total_avg " \
                 "FROM test_summary_by_category_v " \
                 "WHERE student_user_id = :student_user_id " \
                 "AND assessment_enroll_id = :assessment_enroll_id " \
                 "AND assessment_id = :assessment_id " \
                 "UNION ALL " \
                 "SELECT 0 as part," \
                 "       'Total' as category, " \
                 "       '' as score, " \
                 "       '' as total_score, " \
                 "       '' as avg_score, " \
                 "       '' as percentile_score, " \
                 "       student_avg as avg_score1, " \
                 "       total_avg " \
                 "from (" \
                 "    select to_char(avg(student_score),'999.99') as student_avg, to_char(avg(score),'999.99') as total_avg" \
                 "    from (" \
                 "       select case when sum(case when student_user_id = :student_user_id then outcome_score * weight else 0 end) = 0 then 0 else " \
                 "                   sum(case when student_user_id = :student_user_id then candidate_mark * weight else 0 end) * 100::double precision / sum(case when student_user_id = :student_user_id then outcome_score * weight else 0 end) end as student_score, " \
                 "case when sum(outcome_score * weight) = 0 then 0 else " \
                 "                   sum(candidate_mark * weight) * 100::double precision / sum(outcome_score * weight) end as score" \
                 "       from (" \
                 "               select aaa.student_user_id, bbb.outcome_score, bbb.weight, bbb.candidate_mark" \
                 "               from (select student_user_id, assessment_id, testset_id, max(id) as id from assessment_enroll" \
                 "              where assessment_id in (" \
                 "                       select :assessment_id as id " \
                 "                       union all " \
                 "                       select id from assessment where id in (select assessment_id from education_plan_details aaaa where plan_id =" \
                 "                       (SELECT plan_id FROM education_plan_details WHERE assessment_id = :assessment_id)" \
                 "                       and test_detail = (select test_detail from assessment where id = :assessment_id)" \
                 "               ))" \
                 "        and testset_id = (select testset_id from assessment_enroll where id = :assessment_enroll_id) " \
                 "        group by student_user_id, assessment_id, testset_id" \
                 "    ) aaa" \
                 "   join marking bbb" \
                 "     on aaa.id = bbb.assessment_enroll_id" \
                 "   ) aa" \
                 "   ) a" \
                 ") t " \
                 "ORDER BY part desc, category"
    cursor_2 = db.session.execute(sql_stmt_2, {'assessment_id': assessment_id, 'student_user_id': student_user_id,
                                               'assessment_enroll_id': assessment_enroll_id})
    Record = namedtuple('Record', cursor_2.keys())
    rows = [Record(*r) for r in cursor_2.fetchall()]
    return rows


'''Admin UI: Query all subject report data including assessment, plan(package)'''


def query_all_report_data(test_type, test_center, year):
    column_names = ['plan_id',
                    'plan_name',
                    '"year" as assessment_year',
                    'grade',
                    'test_type',
                    '"order" as assessment_order',
                    'assessment_id',
                    'testset_id',
                    'id as assessment_enroll_id',
                    'student_user_id',
                    'attempt_count',
                    'test_center',
                    'start_time_client'
                    ]
    sql_stmt = 'SELECT {columns} ' \
               'FROM csedu_plan_assessment_testsets_enrolled_v '.format(columns=','.join(column_names))
    sql_stmt_sub = ''
    if test_type:
        sql_stmt_sub = sql_stmt_sub + 'AND test_type = :test_type '
    if test_center:
        if Codebook.get_code_name(test_center) != 'All':
            sql_stmt_sub = sql_stmt_sub + 'AND test_center = :test_center '
    if year:
        sql_stmt_sub = sql_stmt_sub + 'AND "year" = :year '
    sql_stmt = sql_stmt + sql_stmt_sub.replace('AND', 'WHERE', 1)
    sql_stmt = sql_stmt + ' ORDER BY plan_id, assessment_order, testset_id, test_center,student_user_id'
    cursor = db.session.execute(sql_stmt, {'test_type': test_type, 'test_center': test_center, 'year': year})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]
    return rows


'''Admin UI: Query individual progress summary report list'''


def query_individual_progress_summary_report_list():
    column_names_1 = ['plan_id',
                      'plan_name',
                      'year',
                      'grade',
                      'test_type'
                      ]
    sql_stmt_1 = 'SELECT distinct {columns} ' \
                 'FROM my_report_progress_summary_v '.format(columns=','.join(column_names_1))
    cursor_1 = db.session.execute(sql_stmt_1)
    Record = namedtuple('Record', cursor_1.keys())
    rows = [Record(*r) for r in cursor_1.fetchall()]
    return rows


'''Admin UI: Query individual progress summary report header'''


def query_individual_progress_summary_report_header(plan_id):
    column_names_1 = ['year',
                      'grade',
                      'test_type'
                      ]
    sql_stmt_1 = 'SELECT DISTINCT {columns} ' \
                 'FROM csedu_education_plan_v ' \
                 ' WHERE plan_id=:plan_id '.format(columns=','.join(column_names_1))
    cursor_1 = db.session.execute(sql_stmt_1, {'plan_id': plan_id})
    row = cursor_1.fetchone()
    return row


'''Admin UI: Query individual progress summary report by assessment'''


def query_individual_progress_summary_report_by_assessment(plan_id, student_user_id):
    column_names_all = ['p.plan_id', 'p."order"', 'p.assessment_id',
                        'p.student_user_id',
                        "to_char(coalesce(p.score,0),'999.99') as my_set_score",
                        "p.rank_v",
                        "to_char(coalesce(p.avg_score,0),'999.99') as avg_set_score"
                        ]
    sql_stmt_all = 'SELECT DISTINCT {columns} ' \
                   'FROM test_summary_by_assessment_v p ' \
                   ' WHERE p.plan_id = :plan_id ' \
                   '  AND student_user_id = :student_user_id ' \
                   ' ORDER BY p.plan_id, p."order" '.format(columns=','.join(column_names_all))
    cursor_all = db.session.execute(sql_stmt_all, {'plan_id': plan_id, 'student_user_id': student_user_id})
    Record = namedtuple('Record', cursor_all.keys())
    rows = [Record(*r) for r in cursor_all.fetchall()]
    return rows


'''Admin UI: Query individual progress summary report - plan information'''


def query_individual_progress_summary_report_by_plan(plan_id, student_user_id):
    column_names = ['p.plan_id', 'p."order"', 'p.assessment_id',
                    'p.testset_id',
                    'ts.student_user_id',
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
               '  AND student_user_id = :student_user_id ' \
               ' ORDER BY p.plan_id, p."order", p.testset_id'.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt, {'plan_id': plan_id, 'student_user_id': student_user_id})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]
    return rows


def query_report_graph(assessment_id, student_user_id):
    sql_stmt = "select t.testset_id, t.id as assessment_enroll_id, t.score, t.ranking, t.total, " \
               "(select (select code_name from codebook where id = t2.subject) from testset t2 where id = t.testset_id) as subject," \
               "round((ranking / cast( total as DECIMAL(4,1))) * 100) as my_pecent " \
               "from ( " \
               "select e.testset_id, e.id, e.student_user_id, sum(m.candidate_mark) as score " \
               ",RANK() OVER (PARTITION BY e.testset_id ORDER BY sum(m.candidate_mark) desc) as ranking " \
               ",COUNT(*) OVER (PARTITION BY e.testset_id) as total " \
               "FROM marking m, " \
               "  (select * from assessment_enroll  where assessment_id = :assessment_id and finish_time is not null) e " \
               "  WHERE e.id = m.assessment_enroll_id " \
               "group by e.id, e.testset_id, e.student_user_id " \
               ") t " \
               "where student_user_id = :student_user_id " \
               "order by id"
    cursor = db.session.execute(text(sql_stmt), {'assessment_id': assessment_id, 'student_user_id': student_user_id})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]
    return rows


'''Admin UI: Query individual progress summary report by subject'''


def query_individual_progress_summary_by_subject_v(plan_id, student_user_id):
    column_names = ['plan_id', 'testset_id', 'student_user_id',
                    'rank_v',
                    "to_char(coalesce(subject_avg_my_score,0),'999.99') as subject_avg_my_score,"
                    "to_char(coalesce(subject_avg_avg_score,0),'999.99') as subject_avg_avg_score",
                    "to_char(coalesce(subject_avg_min_score,0),'999.99') as subject_avg_min_score",
                    "to_char(coalesce(subject_avg_max_score,0),'999.99') as subject_avg_max_score"
                    ]
    sql_stmt = 'SELECT {columns} ' \
               'from test_summary_by_subject_v ts' \
               ' WHERE plan_id = :plan_id ' \
               ' AND student_user_id =:student_user_id ' \
               ' ORDER BY testset_id'.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt, {'plan_id': plan_id, 'student_user_id': student_user_id})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]
    return rows


'''Admin UI: Query individual progress summary report by plan'''


def query_individual_progress_summary_by_plan_v(plan_id, student_user_id, num_of_assessments):
    column_names = ['plan_id', 'student_user_id',
                    'rank_v',
                    "to_char(coalesce(sum_my_score,0)/" + str(num_of_assessments) + ",'999.99') as sum_my_score",
                    "to_char(coalesce(sum_avg_score,0)/" + str(num_of_assessments) + ",'999.99') as sum_avg_score",
                    "to_char(coalesce(sum_min_score,0)/" + str(num_of_assessments) + ",'999.99') as sum_min_score",
                    "to_char(coalesce(sum_max_score,0)/" + str(num_of_assessments) + ",'999.99') as sum_max_score"
                    ]
    sql_stmt = 'SELECT {columns} ' \
               'from test_summary_by_plan_v ts' \
               ' WHERE plan_id = :plan_id ' \
               ' AND student_user_id =:student_user_id '.format(columns=','.join(column_names))
    cursor = db.session.execute(sql_stmt, {'plan_id': plan_id, 'student_user_id': student_user_id})
    row = cursor.fetchone()
    return row


'''Admin UI: Query Test Ranking report - subject list )'''


def query_test_ranking_subject_list(assessment_id):
    column_names = ['att.testset_id',
                    "'No_'||att.testset_id||'_'||(select cb.code_name " \
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
    rows = [Record(*r) for r in cursor.fetchall()]
    return rows


'''Admin UI: Query Test Ranking report - student rank list )'''


def query_test_ranking_data(subjects, assessment_id):
    # ##
    # Original SQL Statement for student_ranking report
    # ##
    # sql_stmt = WITH test_result_by_subject AS(
    #     SELECT test_summary_v.row_name[1] AS student_user_id,
    #             test_summary_v.row_name[2] AS assessment_id,
    #             test_summary_v."2",
    #             test_summary_v."3",
    #             test_summary_v."4",
    #             COALESCE(NULLIF(test_summary_v."2", 0::double precision), 0::double precision)
    #             + COALESCE(NULLIF(test_summary_v."3", 0::double precision), 0::double precision)
    #             + COALESCE(NULLIF(test_summary_v."4", 0::double precision), 0::double precision) AS total_mark
    #     FROM crosstab('select ARRAY[student_user_id::integer,assessment_id::integer] as row_name, testset_id, my_score
    #                     from (SELECT m.student_user_id,
    #                             m.assessment_id,
    #                             m.testset_id,
    #                             m.score AS my_score
    #                             FROM marking_summary_360_degree_mview m
    #                             where student_user_id is not null
    #                             and m.assessment_id = 2) test_summary_v
    #                     order by 1, 2 ',
    #                     'select distinct att.testset_id
    #                         from assessment_testsets as att join assessment_enroll as ae
    #                         on att.assessment_id = ae.assessment_id
    #                         where att.assessment_id = 2
    #                         order by 1')
    #     AS test_summary_v(row_name integer[], "2" double precision, "3" double precision, "4" double precision)
    # )
    # SELECT trs.student_user_id,
    #     (select s.student_user_id from student s where s.user_id=trs.student_user_id) AS cs_student_id,
    #       (select u.username from users u where u.id=trs.student_user_id) AS student_name,
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
    #     assessment_enroll.student_user_id,
    #     assessment_enroll.test_center
    #     FROM assessment_enroll) a
    # WHERE trs.assessment_id = a.assessment_id
    # AND trs.student_user_id = a.student_user_id;
    #
    sql_stmt = ' WITH test_result_by_subject AS( ' \
               + ' SELECT test_summary_v.row_name[1] AS student_user_id, ' \
               + ' test_summary_v.row_name[2] AS assessment_id, '
    for subject in subjects:
        sql_stmt = sql_stmt + ' test_summary_v.' + subject.subject_name + ', '
    index = 1
    for subject in subjects:
        if index != 1:
            sql_stmt = sql_stmt + '+'
        sql_stmt = sql_stmt \
                   + ' COALESCE(NULLIF(test_summary_v.' + subject.subject_name + ', 0::double precision), 0::double precision)'
        index += 1
    sql_stmt = sql_stmt + ' AS total_mark '
    sql_stmt = sql_stmt \
               + " FROM crosstab('select ARRAY[student_user_id::integer,assessment_id::integer] as row_name, testset_id, my_score " \
               + "                  from (SELECT m.student_user_id, " \
               + "                            m.assessment_id, " \
               + "                             m.testset_id, " \
               + "                            m.score AS my_score " \
               + "                            FROM marking_summary_360_degree_mview m " \
               + "                            where student_user_id is not null " \
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
        if index < len(subjects):
            sql_stmt = sql_stmt + ', '
        index += 1
    sql_stmt = sql_stmt + ') )'
    sql_stmt = sql_stmt \
               + " SELECT trs.student_user_id, " \
               + "     (select s.student_id from student s where s.user_id=trs.student_user_id) AS cs_student_id, " \
               + "     (select u.username from users u where u.id=trs.student_user_id) AS student_name, " \
               + "     trs.assessment_id, " \
               + "      a.test_center, "
    index = 1
    for subject in subjects:
        sql_stmt = sql_stmt + 'trs.' + subject.subject_name + ' as subject_' + str(index) + ', '
        index += 1
    sql_stmt = sql_stmt \
               + ' trs.total_mark, ' \
               + ' rank() OVER(PARTITION BY trs.assessment_id ORDER BY trs.total_mark DESC) AS student_rank ' \
               + ' FROM test_result_by_subject trs, ' \
               + ' (SELECT DISTINCT assessment_enroll.assessment_id, ' \
               + '     assessment_enroll.student_user_id, ' \
               + '     assessment_enroll.test_center ' \
               + '     FROM assessment_enroll) a ' \
               + ' WHERE trs.assessment_id = a.assessment_id ' \
               + ' AND trs.student_user_id = a.student_user_id '

    cursor = db.session.execute(sql_stmt, {'assessment_id': assessment_id})
    Record = namedtuple('Record', cursor.keys())
    rows = [Record(*r) for r in cursor.fetchall()]
    return rows


def build_test_ranking_excel_response(subjects, test_summaries, year, test_type, sequence):
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
    headers = ["No.", "Student No.", "Name"]
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
    for i in range(1, len(subjects) + 1):
        attributes.append("subject_" + str(i))
    attributes.append("total_mark")
    attributes.append("student_rank")
    attributes.append("test_center")

    for ts in test_summaries:
        row += 1
        worksheet.write(row, 0, str(col + 1))
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


def build_test_results_pdf_response(template_file_name, image_file_path, assessment_GUID, student_user_id):
    rendered_template_pdf = render_template(template_file_name, image_file_path=image_file_path)
    from weasyprint import HTML, CSS
    from weasyprint.fonts import FontConfiguration
    font_config = FontConfiguration()
    css = CSS(string='''
        @font-face {
            font-family: Gentium;
            src: url(http://example.com/fonts/Gentium.otf);
        }
        h1 { font-family: Gentium }''', font_config=font_config)
    html = HTML(string=rendered_template_pdf)

    pdf_dir_path = 'test_report_pdf_%s' % (assessment_GUID)
    curr_dir = os.getcwd()
    os.chdir(current_app.config['IMPORT_TEMP_DIR'])
    if not os.path.exists(pdf_dir_path):
        os.makedirs(pdf_dir_path)
    pdf_file_path = '%s/%s_%s.pdf' % (pdf_dir_path, pdf_dir_path, student_user_id)
    html.write_pdf(target=pdf_file_path,
                   presentational_hints=True)
    os.chdir(curr_dir)
    return 'success'


def build_test_results_zipper(assessment_GUID):
    from zipfile import ZipFile
    from flask import send_file

    pdf_dir_path = 'test_report_pdf_%s' % (assessment_GUID)
    os.chdir(current_app.config['IMPORT_TEMP_DIR'])
    file_paths = get_all_files(pdf_dir_path)
    with ZipFile('%s.zip' % pdf_dir_path, 'w') as zip:
        for file in file_paths:
            zip.write(file)
    zfile = '%s/%s.zip' % (current_app.config['IMPORT_TEMP_DIR'], pdf_dir_path)
    rsp = send_file(
        zfile,
        mimetype='application/zip',
        as_attachment=True,
        attachment_filename='%s.zip' % pdf_dir_path)
    return rsp


'''Admin UI individual_progress Report by_subject - draw picture '''


def draw_individual_progress_by_subject(score_summaries, plan_GUID, student_user_id):
    import numpy as np
    import seaborn as sns
    import matplotlib.pyplot as plt
    sns.set(style="whitegrid")
    f, axes = plt.subplots(len(score_summaries), 1, figsize=(3 * len(score_summaries), len(score_summaries)),
                           sharex=True)
    y = np.array(["My Score", "Avg"])

    arr_x = []
    index = 0
    for score in score_summaries:
        _subject = score.get('subject')
        # _my_score_range = score.get('my_score_range')
        _my_score = float(score.get('my_score'))
        _total_score = float(score.get('total_score'))
        # _my_avg_range = float(score.get('my_avg_range'))
        _avg = float(score.get('average'))
        arr_x.append(np.array([_my_score, _avg]))
        axes[index].set_ylabel(_subject)
        axes[index].set(xlim=(0, _total_score))
        index += 1

    index = 0
    for x in arr_x:
        sns.barplot(x=x, y=y, palette="deep", ax=axes[index])
        index += 1

    file_name = "individual_progress_by_subject_%s_%s.png" % (plan_GUID, student_user_id)
    report_folder = os.path.join(current_app.config['USER_DATA_FOLDER'], str(current_user.id),
                                 "individual_progress_report")
    f.savefig(os.path.join(report_folder, file_name))
    return file_name


'''Admin UI individual_progress Report by_set - draw picture '''


def draw_individual_progress_by_set(my_set_score, avg_set_score, plan_GUID, student_user_id):
    import seaborn as sns
    import matplotlib.pyplot as plt
    import pandas as pd
    sns.set(style="darkgrid")
    fig = plt.figure()

    values, tests = [], []
    for i in range(0, len(my_set_score)):
        # score = [my_set_score[i], avg_set_score[i]]
        values.append([my_set_score[i], avg_set_score[i]])
        tests.append('Test%s' % str(i + 1))
    df = pd.DataFrame(values, tests, columns=['My Score', 'Avg Score'])
    sns.lineplot(data=df, palette="tab10", linewidth=2.5)
    # plt.show()
    file_name = "individual_progress_by_set_%s_%s.png" % (plan_GUID, student_user_id)
    report_folder = os.path.join(current_app.config['USER_DATA_FOLDER'], str(current_user.id),
                                 "individual_progress_report")
    fig.savefig(os.path.join(report_folder, file_name))
    return file_name


def build_individual_progress_pdf_response(template_file_name, static_folder,
                                           by_subject_file_name, by_set_file_name,
                                           ts_header, num_of_assessments, num_of_subjects,
                                           subject_names, subjects, my_set_score,
                                           avg_set_score, my_set_rank, score_summaries, plan_id,
                                           plan_GUID, student_user_id):
    rendered_template_pdf = render_template(template_file_name, static_folder=static_folder,
                                            by_subject_file_name=by_subject_file_name,
                                            by_set_file_name=by_set_file_name,
                                            ts_header=ts_header,
                                            num_of_assessments=num_of_assessments, num_of_subjects=num_of_subjects,
                                            subject_names=subject_names,
                                            subjects=subjects, my_set_score=my_set_score,
                                            avg_set_score=avg_set_score, my_set_rank=my_set_rank,
                                            score_summaries=score_summaries, plan_id=plan_id
                                            )

    from weasyprint import HTML
    html = HTML(string=rendered_template_pdf)
    curr_dir = os.getcwd()

    pdf_file_path = os.path.join(current_app.config['USER_DATA_FOLDER'],
                                 str(current_user.id),
                                 "individual_progress_report",
                                 plan_GUID,
                                 "%s_%s.pdf" % (plan_GUID, student_user_id))

    os.chdir(current_app.config['USER_DATA_FOLDER'])
    if not os.path.exists(str(current_user.id)):
        os.makedirs(str(current_user.id))
    os.chdir(str(current_user.id))
    if not os.path.exists("individual_progress_report"):
        os.makedirs("individual_progress_report")
    os.chdir("individual_progress_report")
    if not os.path.exists(plan_GUID):
        os.makedirs(plan_GUID)
    html.write_pdf(target=pdf_file_path, presentational_hints=True)
    os.chdir(curr_dir)
    return 'success'


def build_individual_progress_zipper(plan_GUID):
    from zipfile import ZipFile
    from flask import send_file

    pdf_dir_path = os.path.join(str(current_user.id),
                                "individual_progress_report",
                                plan_GUID)
    os.chdir('%s/%s/%s' % (current_app.config['USER_DATA_FOLDER'], str(current_user.id), "individual_progress_report"))
    file_paths = get_all_files(plan_GUID)

    with ZipFile('%s.zip' % plan_GUID, 'w') as zip:
        for file in file_paths:
            zip.write(file)

    zfile = os.path.join(current_app.config['USER_DATA_FOLDER'],
                         str(current_user.id),
                         "individual_progress_report",
                         "%s.zip" % (plan_GUID))
    rsp = send_file(
        zfile,
        mimetype='application/zip',
        as_attachment=True,
        attachment_filename=zfile)
    return rsp


def get_all_files(directory):
    file_paths = []
    for root, directories, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)
    return file_paths


'''Admin UI: Item Score Summary report data '''


def query_item_score_summary_data(item_id):
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
    return rows


'''Refresh Mview for generating Report'''


@api.route('/gen_report/', methods=['POST'])
@permission_required(Permission.ASSESSMENT_MANAGE)
def gen_report():
    # refresh_mviews()
    print('Finish refresh mviews')
    return 'True'


'''Reset test: return EnrollTest Information'''


@api.route('/reset_test/', methods=['GET'])
@permission_required(Permission.ASSESSMENT_MANAGE)
def reset_test_query():
    # Reset Test: Assessment Enroll - testset - testid information
    #       condition : start_time_client
    # query = db.session.query(AssessmentEnroll.assessment_id, AssessmentEnroll.testset_id, \
    #                            AssessmentEnroll.start_time_client.cast(Date).label('start_time')).distinct(). \
    #                     filter(AssessmentEnroll.start_time_client.isnot(None)). \
    #                     filter_by(finish_time_client=None).order_by(AssessmentEnroll.start_time_client.cast(Date).desc())
    query = db.session.query(AssessmentEnroll.assessment_id, AssessmentEnroll.testset_id).distinct(). \
        order_by(AssessmentEnroll.assessment_id, AssessmentEnroll.testset_id)

    enrolls = query.all()
    tests_not_finished = []
    for enroll in enrolls:
        data = {}
        assessment = db.session.query(Assessment.GUID, Assessment.name). \
            filter(Assessment.id == enroll.assessment_id).first()
        testset = db.session.query(Testset). \
            filter(Testset.id == enroll.testset_id).first()
        data['assessment_guid'] = assessment.GUID
        data['assessment_name'] = assessment.name
        data['testset_name'] = testset.name
        data['testset_id'] = testset.id
        data['testset_version'] = testset.version
        # data['start_time'] = str(enroll.start_time)
        tests_not_finished.append(data)
    return success(tests_not_finished)


'''Reset test'''


@api.route('/reset_test/', methods=['POST'])
@permission_required(Permission.ASSESSMENT_MANAGE)
def reset_test():
    from datetime import datetime
    enroll_id = request.form.get('enroll_id')
    guid = request.form.get('guid')
    testset_id = request.form.get('testset_id')
    student_user_id = Student.getStudentUserId(request.form.get('cs_student_id'))
    week_no = request.form.get('week_no')

    if week_no != str(datetime.today().isocalendar()[1]):
        return "Invalid Security Code for Reset Test", 404
    if not student_user_id:
        return "Student not found", 404

    if enroll_id:
        enroll = AssessmentEnroll.query.filter_by(id=enroll_id). \
            filter_by(student_user_id=student_user_id).first()
    else:
        enroll = AssessmentEnroll.query.filter_by(assessment_guid=guid). \
            filter_by(testset_id=testset_id). \
            filter_by(student_user_id=student_user_id). \
            order_by(AssessmentEnroll.id.desc()).first()

    if not enroll:
        return "Enrollment for %s is not found" % request.form.get('cs_student_id'), 404
    rows = db.session.query(Marking.testlet_id).distinct().filter(Marking.assessment_enroll_id == enroll.id). \
        filter(Marking.testset_id == enroll.testset_id).order_by(Marking.created_time.asc()). \
        all()
    testlet_ids = [row.testlet_id for row in rows]

    markings = Marking.query.filter_by(assessment_enroll_id=enroll.id).filter_by(testset_id=enroll.testset_id).all()

    errors = []
    if not markings:
        errors.append('No marking')

    for marking in markings:
        marking_writing = MarkingForWriting.query.filter_by(marking_id=marking.id).first()
        if marking_writing:
            db.session.delete(marking_writing)
            db.session.commit()
        db.session.delete(marking)
        db.session.commit()

    if enroll:
        db.session.delete(enroll)
        db.session.commit()
        data = {"assessment_enroll_id": enroll.id,
                "assessment_id": enroll.assessment_id,
                "testset_id": enroll.testset_id,
                "cs_student_id": Student.getCSStudentId(enroll.student_user_id),
                "testlet_ids": testlet_ids}
        log.info(
            "Reset Test: assessment_enroll_id({}), assessment_id({}), testset_id({}), student_user_id({},{})".format(
                enroll.id, enroll.assessment_id, enroll.testset_id, enroll.student_user_id,
                Student.getCSStudentId(enroll.student_user_id)))

    else:
        errors.append('No enroll')
    if len(errors):
        return ",".join(errors), 500
    else:
        return success(data)


# Report Centre > search assessment
@api.route('/search_assessment/')
@permission_required(Permission.ASSESSMENT_READ)
def search_assessment():
    year = request.args.get('year', '2020', type=str)
    test_type = request.args.get('test_type', 0, type=int)
    test_center = request.args.get('test_center', 0, type=int)

    query = db.session.query(Assessment.id, Assessment.name, Testset.id.label('testset_id'),
                             Testset.version, Testset.name.label('testset_name')). \
        join(AssessmentEnroll, Assessment.id == AssessmentEnroll.assessment_id). \
        join(Testset, Testset.id == AssessmentEnroll.testset_id). \
        filter(AssessmentEnroll.start_time_client > datetime(int(year), 1, 1)). \
        filter(Assessment.test_type == test_type)

    # Query current_user's test center
    # If test_center 'All', query all
    # If test_center 'Administrator', query all
    if not current_user.is_administrator() and \
            (current_user.username != 'All' and current_user.get_branch_id() != test_center):
        return "Forbidden branch data!", 403
    else:
        if current_user.username != 'All' and Codebook.get_code_name(test_center) != 'All':
            query = query.filter(AssessmentEnroll.test_center == test_center)

    assessment_list = []
    # assessments = query.distinct().order_by(Assessment.id.asc()).all()
    # assessments = query.distinct().order_by(AssessmentEnroll.start_time_client.desc(), Testset.name.asc(), Testset.version.asc()).all()
    assessments = query.distinct().order_by(Assessment.name.desc()).all()

    for assessment in assessments:
        data = {}
        data['assessment_id'] = assessment.id
        data['assessment_name'] = assessment.name
        data['testset_name'] = assessment.name
        data['testset_id'] = assessment.testset_id
        data['testset_name'] = assessment.testset_name
        data['testset_version'] = assessment.version
        assessment_list.append(data)
    return success(assessment_list)
