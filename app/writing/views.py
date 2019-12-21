import json
import os
import time
import urllib

from flask import render_template, flash, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import load_only
from sqlalchemy.orm.attributes import flag_modified
from werkzeug.utils import secure_filename

from app.web.errors import page_not_found
from . import writing
from .forms import StartOnlineTestForm, WritingTestForm, AssessmentSearchForm, WritingMarkingForm, WritingMMForm, \
    MarkerAssignForm
from .. import db
from ..decorators import permission_required, permission_required_or_multiple
from ..models import Permission, Assessment, Codebook, Student, AssessmentEnroll, Marking, TestletHasItem, \
    MarkingForWriting, AssessmentHasTestset, Testset, EducationPlanDetail


@writing.route('/assign/<string:assessment_guid>', methods=['GET'])
@login_required
@permission_required(Permission.ADMIN)
def assign(assessment_guid):
    """
    Menu Writing > Assign main page
    :return:
    """
    assessment = Assessment.query.filter_by(GUID=assessment_guid).first()
    if not assessment:
        return redirect(
            url_for('writing.manage', error="Invalid Request - assessment information not found"))
    form = MarkerAssignForm()
    form.assessment_id.data = assessment.id
    ep = EducationPlanDetail.query.filter_by(assessment_id=assessment.id).first()
    form.markers.data = ep.marker_ids["ids"]
    return render_template('writing/assign.html', form=form, assessment=assessment)


@writing.route('/assign', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def assign_marker():
    """
    Requested from Menu Writing > Assign
    :return: assign marker and return manage
    """
    form = MarkerAssignForm()
    if form.validate_on_submit():
        marker_ids = form.markers.data
        row = EducationPlanDetail.query.filter_by(assessment_id=form.assessment_id.data).first()
        if row is None:
            return redirect(
                url_for('writing.manage', error="Fail to assign - Please register assessment to Education Plan first"))
        row.marker_ids = {"ids": marker_ids}
        db.session.add(row)
        db.session.commit()
        flash('Marker assigned successfully.')
        return redirect(url_for('writing.manage'))
    return redirect(url_for('writing.manage', error="Marker Assign - Form validation Error"))


@writing.route('/manage', methods=['GET'])
@login_required
@permission_required_or_multiple(Permission.ASSESSMENT_READ, Permission.ASSESSMENT_MANAGE)
def manage():
    """
    Menu Writing > Marking main page
    :return: search form and search result - assessment related information
    """
    assessment_name = request.args.get("assessment_name")
    year = request.args.get("year")
    test_type = request.args.get("test_type")
    test_center = request.args.get("test_center")
    if assessment_name or year or test_type or test_center:
        flag = True
    else:
        flag = False
    error = request.args.get("error")
    if error:
        flash(error)

    search_form = AssessmentSearchForm()
    search_form.assessment_name.data = assessment_name
    search_form.year.data = year
    if test_type:
        test_type = int(test_type)
    search_form.test_type.data = test_type
    if test_center:
        test_center = int(test_center)
    search_form.test_center.data = test_center
    rows = None
    assessments = []
    query = Assessment.query.filter_by(active=True)
    if flag:
        if assessment_name:
            query = query.filter(Assessment.name.ilike('%{}%'.format(assessment_name)))
        if year:
            query = query.filter_by(year=year)
        if test_type:
            query = query.filter_by(test_type=test_type)
        if test_center:
            # Todo: Need to check if current_user have access right on queried data
            if test_center == Codebook.get_code_id(current_user.username):
                query = query.filter_by(branch_id=test_center)
            elif Codebook.get_code_name(test_center) == 'All':
                query = query
            else:
                query = query.filter(1 == 2)  # always false return

        # Filtering for only writing testset
        subject_id = Codebook.get_code_id('Writing')
        query = query.join(AssessmentHasTestset, Assessment.id == AssessmentHasTestset.assessment_id).join(Testset,
                                                                                                           AssessmentHasTestset.testset_id == Testset.id).filter(
            Testset.subject == subject_id)

        rows = query.order_by(Assessment.id.desc()).all()
        for r in rows:
            student_ids = [sub.student_id for sub in db.session.query(AssessmentEnroll.student_id).filter(
                AssessmentEnroll.assessment_id == r.id).distinct()]
            assessment_json_str = {"assessment_guid": r.GUID,
                                   "year": r.year,
                                   "test_type": r.test_type,
                                   "name": r.name,
                                   "test_center": r.branch_id,
                                   "students": student_ids
                                   }
            assessments.append(assessment_json_str)
    return render_template('writing/manage.html', is_rows=flag, form=search_form, assessments=assessments)


@login_required
@permission_required(Permission.ADMIN)
@writing.route('/marking/<int:marking_writing_id>/<int:student_id>', methods=['GET'])
@login_required
def marking(marking_writing_id, student_id):
    """
    Menu Writing > Marking > Click 'search writing' > Click 'link to Marking' page
    :param marking_writing_id:
    :param student_id:
    :return: the specific student's writing information for marking by marker
    """
    form = WritingMarkingForm()
    form.marking_writing_id.data = marking_writing_id
    form.student_id.data = student_id
    marking_writing = MarkingForWriting.query.filter_by(id=marking_writing_id).first()
    if marking_writing:
        web_img_links = marking_onscreen_load(marking_writing_id, student_id)
        if len(web_img_links.keys()):
            if marking_writing.candidate_mark_detail:
                populate_criteria_form(form, marking_writing.candidate_mark_detail)  # SubForm data populate from the db
            else:
                populate_criteria_form(form)
            form.markers_comment.data = marking_writing.markers_comment
            return render_template('writing/marking_onscreen_gradient.html', form=form, web_img_links=web_img_links,
                                   timestamp=str(round(time.time() * 1000)))
        else:
            return render_template('writing/marking_empty.html')


def populate_criteria_form(form, criteria_detail=None):
    """
    Call from writing.marking(marking_writing_id, student_id) to populate form - fieldList Criteria information
    :param form:
    :param criteria_detail:
    :return:
    """
    criteria = Codebook.query.filter_by(code_type='criteria').order_by(Codebook.id).all()
    if criteria_detail is None:
        while len(form.markings) > 0:
            form.markings.pop_entry()

        for c in criteria:
            wm_form = WritingMMForm()  # weight mapping
            wm_form.criteria = c.code_name
            wm_form.marking = '0.0'
            form.markings.append_entry(wm_form)
    else:
        while len(form.markings) > 0:
            form.markings.pop_entry()
        for c in criteria:
            wm_form = WritingMMForm()  # weight mapping
            wm_form.criteria = c.code_name
            wm_form.marking = criteria_detail[c.code_name]
            form.markings.append_entry(wm_form)
    return form


@login_required
@permission_required(Permission.ADMIN)
@writing.route('/marking', methods=['POST'])
@login_required
def marking_edit():
    """
    Requested from HTTP to update marker's input into marking_writing table
    :return: Response to Writing > Marking menu
    """
    form = WritingMarkingForm()
    if form.validate_on_submit():
        row = MarkingForWriting.query.filter_by(id=form.marking_writing_id.data).first()
        if row is None:
            return redirect(url_for('writing.manage', error="Invalid Request - marking information not found"))
        row.markers_comment = form.markers_comment.data
        row.marker_id = current_user.id
        # json_str = { 'entry' : form.markings.data }
        json_str = {}
        for entry in form.markings.data:
            json_str[entry['criteria']] = entry['marking']
        row.candidate_mark_detail = json_str
        db.session.add(row)
        db.session.commit()
        flash('Marking for Writing updated.')
        return redirect(url_for('writing.manage'))
    return redirect(url_for('writing.manage', error="Marking Edit - Form validation Error"))


@login_required
@permission_required(Permission.ADMIN)
@writing.route('/writing_ui', methods=['GET'])
@login_required
def writing_ui():
    """
    Temporary Usage / Menu Writing > Testing UI main page
    :return: search form and Writing upload form
    """
    form = StartOnlineTestForm()
    assessment_guid = request.args.get("assessment_guid")
    st_id = request.args.get("student_id")
    form.assessment_guid.data = assessment_guid
    form.student_id.data = st_id
    if assessment_guid:
        test_form = WritingTestForm()
        test_form.assessment_guid.data = assessment_guid
        test_form.student_id.data = st_id
    else:
        test_form = []

    guid_list = [(a.GUID) for a in Assessment.query.distinct(Assessment.GUID). \
        filter(Assessment.name.ilike('%{}%'.format('writing'))).all()]
    student = Student.query.filter_by(user_id=st_id).first()
    if student is None:
        return page_not_found()
    return render_template('writing/writing_ui.html', form=form, guid_list=guid_list, test_form=test_form)


@login_required
@permission_required(Permission.ADMIN)
@writing.route('/marking_onscreen/<int:marking_writing_id>/<int:student_id>', methods=['GET'])
@login_required
def marking_onscreen_load(marking_writing_id, student_id):
    marking_writing = MarkingForWriting.query.filter_by(id=marking_writing_id).first()
    web_img_links = {}
    if marking_writing.candidate_file_link:
        for key, file_name in marking_writing.candidate_file_link.items():
            # import magic
            # mime_type = magic.from_file(item_file, mime=True)
            if file_name:
                if os.path.exists(
                        os.path.join(current_app.config['WRITING_UPLOAD_FOLDER'], str(student_id), file_name)):
                    web_img_links[key] = {
                        'writing': '/static/writing/img/%s/%s' % (student_id, file_name)}
                if marking_writing.marked_file_link:
                    if key in marking_writing.marked_file_link.keys():
                        if os.path.exists(
                                os.path.join(current_app.config['WRITING_UPLOAD_FOLDER'], str(student_id),
                                             marking_writing.marked_file_link[key])):
                            web_img_links[key]['marking'] = '/static/writing/img/%s/%s' % (
                                student_id, marking_writing.marked_file_link[key])
    return web_img_links


@login_required
@permission_required(Permission.ADMIN)
@writing.route('/marking_onscreen', methods=['POST'])
@login_required
def marking_onscreen_save():
    """
    Save onscreen marking an an image
    :return:
    """
    if request:
        writing_id = request.json["writing_id"]
        student_id = request.json["student_id"]
        key = request.json["key"];
        writing_path = request.json["writing_path"]
        marking_path = request.json["marking_path"]
        marking_image = request.json["marking_image"]
        if writing_path:
            marking_file_name = os.path.basename(marking_path)
            if not marking_file_name:
                writing_file_name = os.path.splitext(os.path.basename(writing_path))[0]
                marking_file_name = writing_file_name + "_marking.png"
            marking_file_save_path = os.path.join(current_app.config['WRITING_UPLOAD_FOLDER'], student_id,
                                                  marking_file_name).replace('\\', '/')

            # Save image
            r = urllib.request.urlopen(marking_image)
            with open(marking_file_save_path, 'wb') as f:
                f.write(r.file.read())

            # Update DB if required
            marking_writing = MarkingForWriting.query.filter_by(id=writing_id).first()
            if marking_writing.marked_file_link is None:
                marking_writing.marked_file_link = {key: marking_file_name}
            elif key not in marking_writing.marked_file_link.keys():
                marking_writing.marked_file_link[key] = marking_file_name

            flag_modified(marking_writing, "marked_file_link")
            db.session.commit()
            return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
            # except:
            #     return json.dumps({'success': False}), 500, {'ContentType': 'application/json'}


@login_required
@permission_required(Permission.ADMIN)
@writing.route('/upload_writing', methods=['POST'])
@login_required
def upload_writing():
    """
    Temporary Usage / Menu Writing > Testing UI > upload writing
    :return:
    """
    form = WritingTestForm()
    assessment_guid = form.assessment_guid.data
    st_id = form.student_id.data
    if form.validate_on_submit():
        # Todo: change real data for assessment_id, testset_id and assessment_enroll_id
        # Step for assessment_enroll
        assessment = Assessment.query.options(load_only("id")).filter_by(GUID=assessment_guid).first()
        assessment_id = assessment.id
        testset_id = assessment.testsets[0].id

        assessment_enroll = AssessmentEnroll(assessment_guid=assessment_guid,
                                             assessment_id=assessment_id,
                                             testset_id=testset_id,
                                             student_id=st_id)
        db.session.add(assessment_enroll)
        db.session.commit()
        assessment_enroll_id = assessment_enroll.id
        # Todo: change real data for testlet_id, item_id and marking_id
        # Step for marking
        testlet_id = assessment.testsets[0].getFirstStageTestletID()
        item_id = (TestletHasItem.query.options(load_only("item_id")).filter_by(testlet_id=testlet_id).first()).item_id
        marking = Marking(question_no=1,
                          testset_id=testset_id,
                          testlet_id=testlet_id,
                          item_id=item_id,
                          weight=1.0,
                          assessment_enroll_id=assessment_enroll_id)
        db.session.add(marking)
        db.session.commit()
        marking_id = marking.id

        # Step for marking_writing
        filefield_name = "w_image"
        text = form.w_text.data
        file_name = saveWritingFile(filefield_name, text, assessment_guid, st_id)
        insertMarkingForWriting(marking_id, file_name)
    return redirect(url_for('writing.writing_ui', assessment_guid=assessment_guid, student_id=st_id))


def insertMarkingForWriting(marking_id, file_name):
    """
    Call from writing.upload_writing - update marking_writing table set candidate_file_link
    :param marking_id:
    :param file_name:
    :return: true
    """
    candidate_file_link_json = {"file1": file_name}
    marking_writing = MarkingForWriting(candidate_file_link=candidate_file_link_json,
                                        marking_id=marking_id)
    db.session.add(marking_writing)
    db.session.commit()
    flash("Writing is saved successfully.")


def saveWritingFile(filefield_name, text, assessment_guid, student_id):
    """
    Call from writing.upload_writing - save student's writing to current_app.config['WRITING_UPLOAD_FOLDER']
    :param filefield_name:
    :param text:
    :param assessment_guid:
    :param student_id:
    :return: filename saved to current_app.config['WRITING_UPLOAD_FOLDER']
    """
    if not os.path.exists(os.path.join(current_app.config['WRITING_UPLOAD_FOLDER'], student_id)):
        os.makedirs(os.path.join(current_app.config['WRITING_UPLOAD_FOLDER'], student_id))

    my_files = request.files.getlist(filefield_name)
    file_name = ''
    if len(my_files[0].filename) > 0:
        for f in my_files:
            f_file_name = f.filename
            if f and allowed_file(f.filename):
                file_name = student_id + '_' + assessment_guid + '_' + secure_filename(f.filename)
                item_file = os.path.join(current_app.config['WRITING_UPLOAD_FOLDER'], student_id, file_name)
                f.save(item_file)
                flash("File %s uploaded as %s. " % (f_file_name, file_name))
            else:
                flash("Reject {} file importing".format(f.filename))
    else:
        text = text
        if text:
            file_name = student_id + '_' + assessment_guid + '_writing.txt'
            item_file = os.path.join(current_app.config['WRITING_UPLOAD_FOLDER'], student_id, file_name)
            f = open(item_file, "w")
            f.write(text)
            flash("Writing Texts are uploaded into %s. " % (file_name))
            f.close()
    return file_name


def allowed_file(filename):
    """
    Call from writing.saveWritingFile to check file extension allowed
    :param filename:
    :return:
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['WRITING_ALLOWED_EXTENSIONS']
