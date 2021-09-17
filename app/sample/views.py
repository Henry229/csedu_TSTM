import json
import re
import uuid
from datetime import datetime

import pytz
from flask import render_template, flash, request, redirect, url_for, session, jsonify, render_template_string
from flask_login import login_required, current_user
from sqlalchemy import func

from . import sample
from .. import db
from ..decorators import check_sample_login, permission_required
from ..models import SampleUsers, Codebook, SampleAssessment, Permission, Testset, Item, TestletHasItem, \
    SampleAssessmentItems, SampleAssessmentEnroll

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
        return redirect(url_for('sample.sample_index'))

    assessment = SampleAssessment.query.filter_by(id=assessment_id).first()
    if assessment is None:
        return redirect(url_for('sample.sample_index'))

    return render_template('sample/agreement.html', name='Sample Tester - ' + user.username, assessment=assessment)

@sample.route('/testing', methods=['GET', 'POST'])
@check_sample_login()
def testing():
    session_key = request.args.get('session')
    if session_key is None:
        return redirect(url_for('sample.sample_index'))

    user = SampleUsers.query.filter_by(id=session["sample"]).first()
    if user is None:
        return redirect(url_for('sample.sample_index'))

    sample_assessment_enroll = SampleAssessmentEnroll.query.filter_by(session_key=session_key).first()
    if sample_assessment_enroll is None:
        return redirect(request.referrer)

    question_no = 1
    last = False
    first = True
    if request.cookies.get('question_no'):
        question_no = request.cookies.get('question_no')

    max_question_no = db.session.query(func.max(SampleAssessmentItems.question_no)).filter(SampleAssessmentItems.sample_assessment_id==sample_assessment_enroll.sample_assessment_id).scalar()
    if question_no == max_question_no:
        last = True
    if question_no > 1:
        first = False

    return render_template('sample/sample_runner.html', session_key=session_key, sample_assessment_id=sample_assessment_enroll.sample_assessment_id, first=first, last=last, name='Sample Tester - ' + user.username)


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

    sample_assessment_items_count = SampleAssessmentItems.query.filter_by(sample_assessment_id=sample_assessment_id).count()

    if sample_assessment_items_count > 0:
        return render_template_string('fail')

    results = []
    branching = json.dumps(testset.branching)
    ends = [m.end() for m in re.finditer('"id":', branching)]
    for end in ends:
        comma = branching.find(',', end)
        testlet_id = int(branching[end:comma])

        items = db.session.query(*Item.__table__.columns,TestletHasItem.weight). \
            select_from(Item). \
            join(TestletHasItem, Item.id == TestletHasItem.item_id). \
            filter(TestletHasItem.testlet_id == testlet_id).order_by(TestletHasItem.order).all()


        for item in items:
            i = {'item_id':item.id,
                 'testlet_id':testlet_id,
                 'correct_r_value':item.correct_r_value,
                 'weight':item.weight,
                 'outcome_score':item.outcome_score
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

