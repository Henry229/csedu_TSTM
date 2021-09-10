import json
import re
import uuid
from datetime import datetime

import pytz
from flask import render_template, flash, request, redirect, url_for, session, jsonify, render_template_string
from flask_login import login_required, current_user

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

    return render_template('sample/agreement.html', name=user.username, assessment=assessment)

@sample.route('/testing', methods=['GET'])
@check_sample_login()
def testing():
    session_key = request.args.get('session')
    question_no = request.args.get('q')

    if session_key is None:
        return redirect(url_for('sample.sample_index'))
    if question_no is None:
        return redirect(url_for('sample.sample_index'))

    sample_assessment_enroll = SampleAssessmentEnroll.query.filter_by(session_key=session_key).first()
    if sample_assessment_enroll is None:
        return redirect(request.referrer)

    return render_template('sample/sample_runner.html', session_key=session_key, question_no=question_no, sample_assessment_id=sample_assessment_enroll.sample_assessment_id)


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
        if result.get('correct_r_value') is None:
            correct_r_value = "''"
        elif len(result.get('correct_r_value'))==1:
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
                                                correct_r_value=correct_r_value,
                                                outcome_score=result.get('outcome_score'))
        db.session.add(assessment_item)
        index += 1
    db.session.commit()

    return render_template_string('success')

