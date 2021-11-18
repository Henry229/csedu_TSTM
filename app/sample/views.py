import base64
import json
import re
import subprocess
import uuid
from collections import namedtuple
from datetime import datetime

import pytz
from PIL import ImageFont
from flask import render_template, flash, request, redirect, url_for, session, jsonify, render_template_string, \
    current_app
from flask_login import login_required, current_user
from sqlalchemy import func, text

from qti.itemservice.itemservice import ItemService
from . import sample
from .. import db
from ..api.errors import bad_request
from ..api.omr import marking_to_value
from ..decorators import check_sample_login, permission_required
from ..models import SampleUsers, Codebook, SampleAssessment, Permission, Testset, Item, TestletHasItem, \
    SampleAssessmentItems, SampleAssessmentEnroll, SampleMarking

'''New Sample Page - rendering template'''

@sample.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if session.get('sample') is None:
            email = request.form.get('email', '', type=str)
            name = request.form.get('name', '', type=str)

            if email and name:
                email = email.lower()
                name = name.lower()
                row = SampleUsers.query.filter(SampleUsers.email == email, SampleUsers.username == name).first()
                if row:
                    session["sample"] = row.id
                else:
                    user = SampleUsers(email=email,
                                       username=name,
                                       created_time=datetime.utcnow())
                    db.session.add(user)
                    db.session.commit()

                    session["sample"] = user.id

    list1 = []
    list2 = []
    sample_list = SampleAssessment.query.order_by(SampleAssessment.order_number).all()

    for s in sample_list:
        if s.sample_type == 'OC Trial Test':
            list1.append({'id': s.id, 'name': s.name})
        else:
            list2.append({'id': s.id, 'name': s.name})

    return render_template("sample/index.html", list1=list1, list2=list2)


@sample.route('/agreement', methods=['GET'])
@check_sample_login()
def agreement():
    assessment_id = request.args.get('id')

    user = SampleUsers.query.filter_by(id=session["sample"]).first()
    if user is None:
        return redirect(url_for('sample.index'))

    assessment = SampleAssessment.query.filter_by(id=assessment_id).first()
    if assessment is None:
        return redirect(url_for('sample.index'))

    return render_template('sample/agreement.html', name='Sample Tester - ' + user.username, assessment=assessment)


@sample.route('/testing', methods=['GET', 'POST'])
@check_sample_login()
def testing():
    session_key = request.args.get('session')
    if session_key is None:
        return redirect(url_for('sample.index'))

    user = SampleUsers.query.filter_by(id=session["sample"]).first()
    if user is None:
        return redirect(url_for('sample.index'))

    sample_assessment_enroll = SampleAssessmentEnroll.query.filter_by(session_key=session_key).first()
    if sample_assessment_enroll is None:
        return redirect(request.referrer)

    if sample_assessment_enroll.finish_time is not None:
        return redirect("/sample/report?session={}".format(session_key))

    return render_template('sample/sample_runner.html', session_key=session_key,
                           sample_assessment_id=sample_assessment_enroll.sample_assessment_id,
                           sample_assessment_enroll_id=sample_assessment_enroll.id,
                           name='Sample Tester - ' + user.username)


@sample.route('/creation/items/<int:sample_assessment_id>', methods=['GET'])
@login_required
@permission_required(Permission.ADMIN)
def creation(sample_assessment_id):
    if sample_assessment_id is None:
        return render_template_string('fail')

    assessment = SampleAssessment.query.filter_by(id=sample_assessment_id).first()
    if assessment is None:
        return render_template_string('fail')
    testset_id = assessment.testset_id

    testset = Testset.query.filter_by(id=testset_id).first()
    if testset is None:
        return render_template_string('fail')

    sample_assessment_items_count = SampleAssessmentItems.query.filter_by(
        sample_assessment_id=sample_assessment_id).count()

    if sample_assessment_items_count > 0:
        return render_template_string('fail')

    results = []
    branching = json.dumps(testset.branching)
    ends = [m.end() for m in re.finditer('"id":', branching)]
    for end in ends:
        comma = branching.find(',', end)
        testlet_id = int(branching[end:comma])

        items = db.session.query(*Item.__table__.columns, TestletHasItem.weight). \
            select_from(Item). \
            join(TestletHasItem, Item.id == TestletHasItem.item_id). \
            filter(TestletHasItem.testlet_id == testlet_id).order_by(TestletHasItem.order).all()

        for item in items:
            i = {'item_id': item.id,
                 'testlet_id': testlet_id,
                 'correct_r_value': item.correct_r_value,
                 'weight': item.weight,
                 'outcome_score': item.outcome_score
                 }
            results.append(i)

    index = 1
    for result in results:
        correct_r_value = None
        if type(result.get('correct_r_value')) is str:
            correct_r_value = result.get('correct_r_value').replace("'", "\"")
        else:
            correct_r_value = []
            for r_value in result.get('correct_r_value'):
                correct_r_value.append(r_value.replace("'", "\""))

        assessment_item = SampleAssessmentItems(sample_assessment_id=sample_assessment_id,
                                                question_no=index,
                                                testlet_id=result.get('testlet_id'),
                                                item_id=result.get('item_id'),
                                                weight=result.get('weight'),
                                                correct_r_value=correct_r_value)
        db.session.add(assessment_item)
        index += 1
    db.session.commit()

    return render_template_string('success')


@sample.route('/report', methods=['GET'])
def report():
    session_key = request.args.get('session')
    if session_key is None:
        return redirect(url_for('sample.index'))

    user = SampleUsers.query.filter_by(id=session["sample"]).first()
    if user is None:
        return redirect(url_for('sample.index'))

    sample_assessment_enroll = SampleAssessmentEnroll.query.filter_by(session_key=session_key).first()
    if sample_assessment_enroll is None:
        return redirect(request.referrer)

    sample_assessment_enroll.test_date = sample_assessment_enroll.start_time.strftime("%Y-%m-%d %a")

    assessment = SampleAssessment.query.filter_by(id=sample_assessment_enroll.sample_assessment_id).first()
    if assessment is None:
        return redirect(url_for('sample.index'))

    sql = 'select round(case when correct_count = 0 then 0 else (correct_count:: decimal / ques_count:: decimal * 100) end) score ' \
          'from (select ' \
          '		 count(b.question_no) as ques_count, ' \
          '		 sum(case when c.is_correct = true then 1 else 0 end) as correct_count ' \
          '	from sample_assessment_enroll a ' \
          'join sample_assessment_items b on a.sample_assessment_id  = b.sample_assessment_id ' \
          'left join sample_marking c on a.id = c.sample_assessment_enroll_id and b.question_no = c.question_no ' \
          'where a.sample_assessment_id = :sample_assessment_id ' \
          ') t'
    total_score = db.session.execute(text(sql), {'sample_assessment_id': assessment.id}).scalar()

    sql = 'select a.question_no ' \
          ',a.correct_r_value as correct_r_value ' \
          ',a.candidate_r_value as candidate_r_value ' \
          ',a.is_correct ' \
          ',( ' \
          '  select 100*COALESCE(sum(CASE WHEN bb.is_correct THEN 1 ELSE 0 END),0)/count(DISTINCT aa.id) ' \
          'from (select * from sample_assessment_enroll where sample_assessment_id = c.id) aa ' \
          'join (select aaa.item_id, bbb.* ' \
          '		from sample_assessment_items aaa, sample_marking bbb where aaa.sample_assessment_id = c.id and aaa.question_no = bbb.question_no ' \
          '	 ) bb ' \
          'on aa.id = bb.sample_assessment_enroll_id ' \
          'where bb.item_id = a.item_id ' \
          ') percentile ' \
          ',(select code_name from codebook where id = (case when d.subcategory = 0 then d.category else d.subcategory end)) as subcategory_name ' \
          ',d.interaction_type ' \
          'from ( ' \
          '	select aa.item_id, aa.question_no, bb.candidate_mark ' \
          '	, bb.candidate_r_value, bb.is_correct, bb.is_flagged, bb.outcome_score ' \
          '	, aa.correct_r_value, case when bb.sample_assessment_enroll_id is null then :sample_assessment_enroll else bb.sample_assessment_enroll_id end as sample_assessment_enroll_id ' \
          '	from sample_assessment_items aa left join sample_marking bb on aa.question_no = bb.question_no ' \
          '	and aa.sample_assessment_id = :sample_assessment_id and bb.sample_assessment_enroll_id = :sample_assessment_enroll ' \
          '	) a ' \
          'join sample_assessment_enroll b on a.sample_assessment_enroll_id = b.id ' \
          'join sample_assessment c on b.sample_assessment_id = c.id ' \
          'join item d on a.item_id = d.id ' \
          'order by a.question_no'
    cursor_1 = db.engine.execute(text(sql), {'sample_assessment_enroll': sample_assessment_enroll.id, 'sample_assessment_id': assessment.id})
    Record = namedtuple('Record', cursor_1.keys())
    rows = [Record(*r) for r in cursor_1.fetchall()]

    crroect_count = 0
    list = []
    for row in rows:
        correct_r_value = ''
        if row.is_correct is None or row.is_correct is False:
            correct_r_value = json.dumps(row.correct_r_value)
            if correct_r_value is not None:
                if correct_r_value[:1] == '"':
                    correct_r_value = correct_r_value[1:]
                if correct_r_value[-1:] == '"':
                    correct_r_value = correct_r_value[:-1]

        if row.candidate_r_value is None:
            candidate_r_value = ''
        else:
            if type(row.candidate_r_value).__name__ == 'list':
                if len(row.candidate_r_value) == 1 and row.candidate_r_value[0] == '':
                    candidate_r_value = ''
                else:
                    candidate_r_value = json.dumps(row.candidate_r_value)
            else:
                candidate_r_value = json.dumps(row.candidate_r_value)
                if candidate_r_value[:1] == '"':
                    candidate_r_value = candidate_r_value[1:]
                if candidate_r_value[-1:] == '"':
                    candidate_r_value = candidate_r_value[:-1]

        if row.is_correct is None:
            is_correct = False
        else:
            is_correct = row.is_correct
            if is_correct is True:
                crroect_count = crroect_count + 1

        list.append({'correct_r_value': correct_r_value,
                     'candidate_r_value': candidate_r_value,
                     'question_no': row.question_no,
                     'percentile': row.percentile,
                     'subcategory_name': row.subcategory_name,
                     'interaction_type': row.interaction_type,
                     'is_correct': is_correct})

    my_score = round(crroect_count % len(list))

    sql = 'select (select code_name from codebook c where id = t.category) as category_name, ' \
          'my_ques_count, my_correct_count, ' \
          'round(case when correct_count = 0 then 0 else (correct_count:: decimal / ques_count:: decimal * 100) end, 2) score, ' \
          'round(case when my_correct_count = 0 then 0 else (my_correct_count:: decimal / my_ques_count:: decimal * 100) end, 2) my_score ' \
          'from ( ' \
          'select d.category, ' \
          'count(b.question_no) as ques_count, ' \
          'sum(case when a.id = :sample_assessment_enroll_id then 1 else 0 end) as my_ques_count, ' \
          'sum(case when c.is_correct = true then 1 else 0 end) as correct_count, ' \
          'sum(case when a.id = :sample_assessment_enroll_id and c.is_correct = true then 1 else 0 end) as my_correct_count ' \
          'from ' \
          'sample_assessment_enroll a ' \
          'join sample_assessment_items b on a.sample_assessment_id  = b.sample_assessment_id ' \
          'left join sample_marking c on a.id = c.sample_assessment_enroll_id and b.question_no = c.question_no ' \
          'join item d on b.item_id = d.id ' \
          'where a.sample_assessment_id = :sample_assessment_id ' \
          'group by d.category ' \
          ') t '

    cursor_1 = db.engine.execute(text(sql), {'sample_assessment_id': assessment.id, 'sample_assessment_enroll_id': sample_assessment_enroll.id})
    Record = namedtuple('Record', cursor_1.keys())
    rows = [Record(*r) for r in cursor_1.fetchall()]

    return render_template('sample/sample_report.html', user=user, assessment=assessment,
                           sample_assessment_enroll=sample_assessment_enroll, markings=list, crroect_count=crroect_count,
                           my_score=my_score, total_score=total_score, categories=rows)
