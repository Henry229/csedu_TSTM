import json
import os
import random
import string
import time
import urllib
from datetime import datetime

import datetime
from pytz import timezone, utc

import pytz
from PIL import ImageFile, Image, ImageDraw, ImageFont
from sqlalchemy import func
from werkzeug.utils import secure_filename

ImageFile.LOAD_TRUNCATED_IMAGES = True
from flask import render_template, flash, request, redirect, url_for, current_app, send_file, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm.attributes import flag_modified

from common.logger import log
from . import writing
from .forms import AssessmentSearchForm, WritingMarkingForm, WritingMMForm, \
    MarkerAssignForm, MarkingListSearchForm
from .. import db
from ..api.reports import query_my_report_header
from ..api.response import success, bad_request
from ..api.writings import common_writing_search_assessment
from ..decorators import permission_required, permission_required_or_multiple
from ..models import Permission, Assessment, Codebook, Student, AssessmentEnroll, Marking, MarkingForWriting, \
    AssessmentHasTestset, Testset, MarkerAssigned, Item, MarkerBranch, User



@writing.route('/writing_marking_list', methods=['GET'])
@login_required
@permission_required(Permission.WRITING_READ)
def list_writing_marking():
    assessment_name = ''
    if request.args.get("assessment_name") is not None: assessment_name = request.args.get("assessment_name")
    grade = ''
    if request.args.get("grade") is not None: grade = request.args.get("grade")
    marked = ''
    if request.args.get("marked") is not None: marked = request.args.get("marked")
    #marker = 0
    #if request.args.get("marker") is not None: marker = request.args.get("marker")

    test_type = request.args.get("test_type")
    marker_name = request.args.get("marker_name")
    tabs = '2'
    if request.args.get("tabs") is not None: tabs = request.args.get("tabs")
    search_form = MarkingListSearchForm()

    marker_id = None
    if current_user.is_administrator():
        if tabs == '1':
            #marker_id = current_user.id
            marker_id = int(search_form.marker_name.data) if marker_name is None else int(marker_name)
        else:
            marker_id = int(search_form.marker_name.data) if marker_name is None else int(marker_name)
    else:
        marker_id = current_user.id

    branch_ids = getBranchIds(marker_id)
    writing_code_id = Codebook.get_code_id('Writing')

    #default year
    max_year = db.session.query(func.max(Assessment.year)).scalar()

    #default assessment
    '''
    query = db.session.query(Assessment.id, Assessment.name, Testset.id.label('testset_id'),
                             Testset.version, Testset.name.label('testset_name')). \
        join(AssessmentEnroll, Assessment.id == AssessmentEnroll.assessment_id). \
        join(Testset, Testset.id == AssessmentEnroll.testset_id). \
        join(Marking, AssessmentEnroll.id == Marking.assessment_enroll_id). \
        join(MarkingForWriting, Marking.id == MarkingForWriting.marking_id). \
        filter(Assessment.year == str(max_year)). \
        filter(AssessmentEnroll.test_center.in_(branch_ids)). \
        filter(Testset.subject == writing_code_id)
    row = query.distinct().order_by(Assessment.id.desc()).one()
    assessment_default = str(row.id) + '_' + str(row.testset_id)
    '''
    assessment = request.args.get("assessment")
    year = request.args.get("year", max_year, type=int)


    search_form.assessment_name.data = assessment_name
    search_form.grade.data = grade
    search_form.marked.data = marked

    search_form.year.data = str(year)
    if test_type is not None:
        search_form.test_type.data = int(test_type)
    if current_user.is_administrator():
        if marker_name is None:
            search_form.marker_name.data = search_form.marker_name.choices[0][0]
        else:
            search_form.marker_name.data = marker_name



    test = [(str(row.id) + '_' + str(row.testset_id), row.name + ' : ' + row.testset_name + ' v.' + str(row.version)) for row in common_writing_search_assessment(str(year), branch_ids, writing_code_id, '0')]



    if assessment is not None and assessment != '0':
        search_form.assessment.choices = [(str(row.id) + '_' + str(row.testset_id),
                                           row.name + ' : ' + row.testset_name + ' v.' + str(row.version)) for row in
                                          common_writing_search_assessment(year, branch_ids, writing_code_id,
                                                                           test_type)]
        search_form.assessment.data = assessment

    query = db.session.query(AssessmentEnroll.id).join(Testset). \
        filter(AssessmentEnroll.testset_id == Testset.id). \
        filter(AssessmentEnroll.test_center.in_(branch_ids)).filter(Testset.subject == writing_code_id)

    if tabs == '1':
        if grade != '':
            query = query.filter(Testset.grade == grade)
    else:
        if assessment is not None and assessment != '0':
            assessments = assessment.split('_')
            query = query.filter(AssessmentEnroll.assessment_id == int(assessments[0])). \
                filter(AssessmentEnroll.testset_id == int(assessments[1]))

    assessment_enroll_ids = [row.id for row in query.all()]

    ############# no marking_writing creating
    #if current_user.is_administrator() is False:

    if writing_code_id:
        marking_writings = db.session.query(AssessmentEnroll, Marking, MarkingForWriting). \
            join(Marking, AssessmentEnroll.id == Marking.assessment_enroll_id). \
            join(MarkingForWriting, Marking.id == MarkingForWriting.marking_id, isouter=True). \
            filter(Marking.assessment_enroll_id.in_(assessment_enroll_ids)). \
            filter(MarkingForWriting.id.is_(None)). \
            all()

        for m in marking_writings:
            if m.AssessmentEnroll.is_finished:
                if m.Marking.candidate_r_value is not None and m.Marking.candidate_r_value != '' and m.Marking.candidate_r_value.get(
                        'writing_text') is not None:
                    save_writing_data(m.AssessmentEnroll.student_user_id, m.Marking.id,
                                      writing_text=m.Marking.candidate_r_value.get('writing_text'))
                else:
                    marking_writing = None
                    marking_writing = MarkingForWriting(marking_id=m.Marking.id, marker_id=m.AssessmentEnroll.student_user_id)
                    marking_writing.candidate_file_link = {}
                    marking_writing.created_time = m.Marking.created_time
                    marking_writing.modified_time = m.Marking.modified_time
                    db.session.add(marking_writing)
                    db.session.commit()

    #############

    query = db.session.query(AssessmentEnroll, Marking, MarkingForWriting). \
        join(Marking, AssessmentEnroll.id == Marking.assessment_enroll_id). \
        join(MarkingForWriting, Marking.id == MarkingForWriting.marking_id). \
        filter(Marking.assessment_enroll_id.in_(assessment_enroll_ids))
    if tabs == '1':
        if marked == '1':
            query = query.filter(MarkingForWriting.candidate_mark_detail != None)
        elif marked == '0':
            query = query.filter(MarkingForWriting.candidate_mark_detail == None)
    marking_writings = query.all()
    #marking_writings = query.order_by(AssessmentEnroll.assessment_id.desc(), AssessmentEnroll.student_user_id).all()

    marking_writing_list = []

    for m in marking_writings:
        if m.MarkingForWriting.candidate_file_link:
            is_candidate_file = 'Y'
        else:
            is_candidate_file = 'N'
        if m.MarkingForWriting.candidate_mark_detail:
            is_marked = 'Y'
        else:
            is_marked = 'N'

        au_tz = pytz.timezone('Australia/Sydney')

        is_ppending = True
        if tabs == '1':
            if assessment_name.strip() != '':
                if m.AssessmentEnroll.assessment.name.find(assessment_name) == -1: is_ppending = False

        writing_files = [];
        if is_candidate_file:
            for key, file_name in m.MarkingForWriting.candidate_file_link.items():
                if file_name:
                    file_path = os.path.join(current_app.config['USER_DATA_FOLDER'], str(m.AssessmentEnroll.student_user_id), "writing",
                                             file_name)
                    if os.path.exists(file_path):
                         writing_files.append(url_for('api.get_writing', marking_writing_id=m.MarkingForWriting.id,
                                               student_user_id=m.AssessmentEnroll.student_user_id, file=file_name))

        downloaded = False
        if m.MarkingForWriting.additional_info:
            additional_info = json.loads(m.MarkingForWriting.additional_info)
            for key, value in additional_info.items():
                if key=='downloaded':
                    downloaded = value


        if is_ppending:
            json_str = {"assessment_enroll_id": m.AssessmentEnroll.id,
                        "assessment_name": m.AssessmentEnroll.assessment.name,
                        "student_user_id": m.AssessmentEnroll.student_user_id,
                        "student_user_name": User.getUserName(m.AssessmentEnroll.student_user_id),
                        "testset_name": m.AssessmentEnroll.testset.name,
                        "start_time": utc.localize(m.AssessmentEnroll.start_time).astimezone(au_tz),
                        "marking_id": m.Marking.id,
                        "item_id": m.Marking.item_id,
                        "marking_writing_id": m.MarkingForWriting.id,
                        "is_candidate_file": is_candidate_file,
                        "is_marked": is_marked,
                        "web_img_links_writing": writing_files,
                        "student_id": Student.getCSStudentId(m.AssessmentEnroll.student_user_id),
                        "downloaded": downloaded
                        }
            marking_writing_list.append(json_str)
    return render_template('writing/list.html', form=search_form, marking_writing_list=marking_writing_list, tabs=tabs)

def save_writing_data(student_user_id, marking_id, writing_files=None, writing_text=None, has_files=False):
    if writing_files is None:
        writing_files = []
    file_names = []
    # 1.1 Save the file to the path at config['USER_DATA_FOLDER']
    for writing_file in writing_files:
        file_name = writing_file.filename if writing_file is not None else 'writing.txt'
        random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=24))
        new_file_name = 'file_' + str(student_user_id) + '_' + random_name + '_' + secure_filename(file_name)
        writing_upload_dir = os.path.join(current_app.config['USER_DATA_FOLDER'], str(student_user_id), "writing")
        item_file = os.path.join(writing_upload_dir, new_file_name)
        if not os.path.exists(writing_upload_dir):
            os.makedirs(writing_upload_dir)
        writing_file.save(item_file)
        file_names.append(new_file_name)

    marking_writing = MarkingForWriting.query.filter_by(marking_id=marking_id) \
        .order_by(MarkingForWriting.id.desc()).first()
    if len(writing_files) == 0 and has_files and marking_writing is not None:
        candidate_file_link = json.loads(marking_writing.candidate_file_link)
        for f_n in candidate_file_link.values():
            if not f_n.startswith('writing'):
                file_names.append(f_n)

    # 1.2 Save the text to the path at config['USER_DATA_FOLDER']
    if writing_text is not None:
        file_name = 'writing.txt'
        random_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=24))
        new_file_name = 'writing_' + str(student_user_id) + '_' + random_name + '_' + secure_filename(file_name)
        writing_upload_dir = os.path.join(current_app.config['USER_DATA_FOLDER'], str(student_user_id), "writing")
        item_file = os.path.join(writing_upload_dir, new_file_name)
        if not os.path.exists(writing_upload_dir):
            os.makedirs(writing_upload_dir)
        with open(item_file, "w") as f:
            f.write(writing_text)
        file_names += text_to_images(student_user_id, item_file)

    # 2. Create a record in MarkingForWriting
    index = 1
    candidate_file_link_json = {}
    for file_name in file_names:
        candidate_file_link_json["file%s" % index] = file_name
        index += 1
    if marking_writing is None:
        marking_writing = MarkingForWriting(marking_id=marking_id, marker_id=student_user_id)
    marking_writing.candidate_file_link = candidate_file_link_json
    marking_writing.modified_time = datetime.datetime.utcnow()
    db.session.add(marking_writing)
    db.session.commit()

@writing.route('/writing_marking_list/download/<int:marking_writing_id>/<int:student_user_id>', methods=['GET'])
@login_required
@permission_required(Permission.WRITING_READ)
def list_writing_marking_download(marking_writing_id, student_user_id):
    from zipfile import ZipFile
    from flask import send_file

    marking_writing = MarkingForWriting.query.filter_by(id=marking_writing_id).first()
    if marking_writing is not None:
        curr_dir = os.getcwd()
        os.chdir(current_app.config['USER_DATA_FOLDER'])
        os.chdir(str(student_user_id))
        os.chdir("writing")
        zip_name = "writing_" + str(marking_writing_id) + "_" + Student.getCSStudentId(student_user_id)

        zfile = '%s/%s/%s/%s.zip' % (current_app.config['USER_DATA_FOLDER'],str(student_user_id),"writing",zip_name)

        with ZipFile('%s.zip' % zip_name, 'w') as zip:
            idx = 0
            for key, file_name in marking_writing.candidate_file_link.items():
                if file_name:
                    idx += 1
                    zip.write(file_name, "writing_" + str(marking_writing_id) + "_" + Student.getCSStudentId(student_user_id) + "_" + str(idx) + file_name[file_name.rfind('.'):])

        rsp = send_file(
            zfile,
            mimetype='application/zip',
            as_attachment=True,
            attachment_filename='%s.zip' % zip_name)

        os.chdir(curr_dir)
        return rsp
    return None


@writing.route('/assign/<string:assessment_guid>', methods=['GET'])
@login_required
@permission_required(Permission.WRITING_MANAGE)
def assign(assessment_guid):

    """
    Menu Writing > Assign main page
    :return:
    """
    assessment = Assessment.query.filter_by(GUID=assessment_guid).first()
    if not assessment:
        return redirect(
            url_for('writing.manage', error="Invalid Request - assessment information not found"))
    form = MarkerAssignForm(branch_id=assessment.branch_id)
    form.assessment_id.data = assessment.id
    form.year.data = assessment.year
    form.test_center.data = assessment.branch_id
    form.test_type.data = assessment.test_type
    marker_ids = [sub.marker_id for sub in db.session.query(MarkerAssigned.marker_id).filter(
        MarkerAssigned.assessment_id == assessment.id).filter(MarkerAssigned.delete.isnot(True)).all()]
    form.markers.data = marker_ids
    return render_template('writing/assign.html', form=form, assessment=assessment)


@writing.route('/assign', methods=['POST'])
@login_required
@permission_required(Permission.WRITING_MANAGE)
def assign_marker():
    """
    Requested from Menu Writing > Assign
    :return: assign marker and return manage
    """
    test_center = request.form.get('test_center')
    form = MarkerAssignForm(branch_id=test_center)
    if form.validate_on_submit():
        marker_ids = form.markers.data
        assessment_id = form.assessment_id.data
        for id in marker_ids:
            row = MarkerAssigned.query.filter_by(assessment_id=assessment_id). \
                filter_by(marker_id=id).first()
            if row:
                if row.delete == True:
                    row.delete = False
                    row.modified_time = datetime.now(pytz.utc)
                    db.session.add(row)
            else:
                ma = MarkerAssigned(marker_id=id, assessment_id=assessment_id)
                db.session.add(ma)

        d_ids = MarkerAssigned.query.filter_by(assessment_id=assessment_id). \
            filter(MarkerAssigned.marker_id.notin_(marker_ids)). \
            filter(MarkerAssigned.delete.isnot(True)).all()
        for row in d_ids:
            row.delete = True
            row.modified_time = datetime.now(pytz.utc)
            db.session.add(row)
        db.session.commit()
        flash('Marker assigned successfully.')
        return redirect(url_for('writing.manage', year=form.year.data, test_type=form.test_type.data,
                                test_center=form.test_center.data))
    return redirect(url_for('writing.manage', error="Marker Assign - Form validation Error"))


@writing.route('/manage', methods=['GET'])
@login_required
@permission_required_or_multiple(Permission.WRITING_READ, Permission.WRITING_MANAGE)
def manage():
    """
    Menu Writing > Marking main page
    :return: search form and search result - assessment related information
    """
    if current_user.is_writing_marker():
        return redirect(url_for('writing.list_writing_marking'))

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
    query = db.session.query(Assessment.id, Assessment.GUID,
                             Assessment.year, Assessment.test_type,
                             Assessment.name, Assessment.branch_id,
                             Testset.id.label('testset_id'),
                             Testset.name.label('testset_name')).filter_by(active=True)
    if current_user.role.name == 'Writing_marker':
        ids = [sub.assessment_id for sub in
               db.session.query(MarkerAssigned.assessment_id).filter_by(marker_id=current_user.id).all()]
        query = query.filter(Assessment.id.in_(ids))
    if flag:
        if assessment_name:
            query = query.filter(Assessment.name.ilike('%{}%'.format(assessment_name)))
        if year:
            query = query.filter_by(year=year)
        if test_type != 0:
            query = query.filter_by(test_type=test_type)
        if test_center:
            if test_center == Codebook.get_code_id(current_user.username):
                query = query.filter_by(branch_id=test_center)
            elif Codebook.get_code_name(test_center) == 'All':
                query = query
            else:
                query = query.filter(1 == 2)  # always false return

        # Filtering for only writing testset
        subject_id = Codebook.get_code_id('Writing')
        query = query.join(AssessmentHasTestset, Assessment.id == AssessmentHasTestset.assessment_id).\
                        join(Testset, AssessmentHasTestset.testset_id == Testset.id).\
                        filter(Testset.subject == subject_id)

        rows = query.order_by(Assessment.id.desc()).all()
        for r in rows:
            marker_ids = [sub.marker_id for sub in db.session.query(MarkerAssigned.marker_id).filter(
                MarkerAssigned.assessment_id == r.id).filter(MarkerAssigned.delete.isnot(True)).all()]

            query = AssessmentEnroll.query.filter(
                                    AssessmentEnroll.assessment_id == r.id,
                                    AssessmentEnroll.testset_id == r.testset_id)
            # Query current_user's test center
            # If test_center 'All', query all
            # If test_center 'Administrator', query all
            if not current_user.is_administrator() and \
                    current_user.get_branch_id() != test_center:
                query = query.filter(1 == 0)
                flash("Forbidden branch data!")
            else:
                if Codebook.get_code_name(test_center) != 'All':
                    query = query.filter(AssessmentEnroll.test_center == test_center)
            enrolls = query.distinct().order_by(AssessmentEnroll.student_user_id.asc()).all()
            student_user_ids = []
            marked = []
            marked_none_exists = False
            # Check if marking_writing record existing
            for enroll in enrolls:
                for marking in enroll.marking:
                    mw = db.session.query(MarkingForWriting.id, MarkingForWriting.candidate_mark_detail).filter_by(marking_id=marking.id).first()
                    if mw:
                        student_user_ids.append(enroll.student_user_id)
                        if mw.candidate_mark_detail:
                            marked.append(True)
                        else:
                            marked.append(False)
                            marked_none_exists = True
                        break

            assessment_json_str = {"assessment_guid": r.GUID,
                                   "year": r.year,
                                   "test_type": r.test_type,
                                   "name": r.name,
                                   "testset_name": r.testset_name,
                                   "testset_id": r.testset_id,
                                   "test_center": r.branch_id,
                                   "markers": marker_ids,
                                   "students": student_user_ids,
                                   "marked": marked,
                                   "marked_none_exists": marked_none_exists
                                   }
            assessments.append(assessment_json_str)
    return render_template('writing/manage.html', is_rows=flag, form=search_form, assessments=assessments)


@login_required
@permission_required(Permission.WRITING_READ)
@writing.route('/rewrite/load/<int:student_user_id>', methods=['POST'])
def load_rewrite(student_user_id):
    if student_user_id == current_user.id:
        rewritings = {}
        for marking_writing_id in request.json:
            marking_writing = MarkingForWriting.query.filter_by(id=marking_writing_id).first()
            if marking_writing:
                if marking_writing.additional_info:
                    additional_info = json.loads(marking_writing.additional_info)
                    rewritings[marking_writing_id] = additional_info['rewriting']
        return jsonify(rewritings)
    return bad_request()


@login_required
@permission_required(Permission.WRITING_READ)
@writing.route('/rewrite/save/<int:student_user_id>', methods=['POST'])
def save_rewrite(student_user_id):
    if student_user_id == current_user.id:
        for rewrite in request.json:
            marking_writing = MarkingForWriting.query.filter_by(id=rewrite['marking_id']).first()
            if marking_writing:
                additional_info = {}
                if marking_writing.additional_info:
                    additional_info = json.loads(marking_writing.additional_info)
                additional_info['rewriting'] = rewrite['rewriting']
                marking_writing.additional_info = json.dumps(additional_info)
                db.session.commit()
        return success()
    return bad_request()


# https://github.com/nkmk/python-snippets/blob/4e232ef06628025ef6d3c4ed7775f5f4e25ebe19/notebook/pillow_concat.py
def get_concat_h_multi_resize(im_list, resample=Image.BICUBIC):
    min_height = min(im.height for im in im_list)
    im_list_resize = [im.resize((int(im.width * min_height / im.height), min_height), resample=resample)
                      for im in im_list]
    total_width = sum(im.width for im in im_list_resize)
    dst = Image.new('RGB', (total_width, min_height))
    pos_x = 0
    for im in im_list_resize:
        dst.paste(im, (pos_x, 0))
        pos_x += im.width
    return dst


def get_concat_v_multi_resize(im_list, resample=Image.BICUBIC):
    min_width = min(im.width for im in im_list)
    im_list_resize = [im.resize((min_width, int(im.height * min_width / im.width)), resample=resample)
                      for im in im_list]
    total_height = sum(im.height for im in im_list_resize)
    dst = Image.new('RGB', (min_width, total_height))
    pos_y = 0
    for im in im_list_resize:
        dst.paste(im, (0, pos_y))
        pos_y += im.height
    return dst


def get_merged_images(student_user_id, marking_writing, local_file=False, vertical=True):
    """
    Create writing + marking combined files with it's resource URLs AND all-in-one single file
    :param student_user_id: Student user ID
    :param marking_writing: MarkingWriting object
    :param local_file: Get path to local files
    :param vertical: Merge image to vertical otherwise horizontal
    :return: URLs/Paths for combined image, URL/Path for the single image
    """
    # Create merged writing markings
    marked_images = []
    combined_images = []
    for idx, (k, v) in enumerate(marking_writing.candidate_file_link.items()):
        try:
            if os.path.isfile(os.path.join(current_app.config['USER_DATA_FOLDER'], str(student_user_id), "writing", v.replace('.jpg', '_merging.jpg'))):
                v = v.replace('.jpg', '_merging.jpg')
                c_image = Image.open(
                    os.path.join(current_app.config['USER_DATA_FOLDER'],
                                 str(student_user_id), "writing", v))
            else:
                c_image = Image.open(
                    os.path.join(current_app.config['USER_DATA_FOLDER'],
                                 str(student_user_id), "writing", v))

            #testing : tif file change to jpg.. after this code..needs to change file name in db
            #if v[-4:] == '.tif':
            #    c_image.save(
            #        os.path.join(current_app.config['USER_DATA_FOLDER'],
            #                     str(student_user_id),
            #                     "writing", v.replace('.tif', '.jpg')), "PNG")
        except FileNotFoundError:
            log.error('File not found. Check the student writing file existing')

        # Merge only when marking is available
        if marking_writing.marked_file_link:
            if k in marking_writing.marked_file_link.keys():
                m_image = Image.open(
                    os.path.join(current_app.config['USER_DATA_FOLDER'],
                                 str(student_user_id),
                                 "writing", marking_writing.marked_file_link[k]))
                c_image.paste(m_image, (0, 0), m_image)

        saved_file_name = v.replace('.jpg', '_merged.png')
        #if v[-4:] == '.jpg':
        #    saved_file_name = v.replace('.jpg', '_merged.png')
        #elif v[-4:] == 'jpeg':
        #    saved_file_name = v.replace('.jpeg', '_merged.jpg')
        #elif v[-4:] == '.tif':
        #    saved_file_name = v.replace('.tif', '_merged.tif')

        c_image.save(
            os.path.join(current_app.config['USER_DATA_FOLDER'],
                         str(student_user_id),
                         "writing", saved_file_name), "PNG")
        combined_images.append(c_image)
        marked_writing_path = url_for('api.get_writing', marking_writing_id=marking_writing.id,
                                      student_user_id=student_user_id, file=saved_file_name)
        if local_file:
            # PDF generation needs to access the file from local file system
            marked_writing_path = 'file:///%s/%s/writing/%s' % (current_app.config['USER_DATA_FOLDER'],
                                                                str(student_user_id), saved_file_name)

        marked_images.append(marked_writing_path)

    # Generate single image of all combined images
    single_image_name = "%s_single.png" % marking_writing.id
    single_pdf_name = "%s_single.pdf" % marking_writing.id
    single_image_path = os.path.join(current_app.config['USER_DATA_FOLDER'],
                                     str(student_user_id), "writing", single_image_name)
    single_pdf_path = os.path.join(current_app.config['USER_DATA_FOLDER'],
                                   str(student_user_id), "writing", single_pdf_name)

    if vertical:
        get_concat_v_multi_resize(combined_images).save(single_image_path, "PNG")
        get_concat_v_multi_resize(combined_images).save(single_pdf_path, "PDF")
    else:
        get_concat_h_multi_resize(combined_images).save(single_image_path, "PNG")
        get_concat_h_multi_resize(combined_images).save(single_pdf_path, "PDF")

    single_image_url = url_for('api.get_writing', marking_writing_id=marking_writing.id,
                               student_user_id=student_user_id, file=single_image_name)
    single_pdf_url = url_for('api.get_writing', marking_writing_id=marking_writing.id,
                             student_user_id=student_user_id, file=single_pdf_name)

    if local_file:
        # PDF generation needs to access the file from local file system
        single_image_url = 'file:///%s/%s/writing/%s' % (current_app.config['USER_DATA_FOLDER'],
                                                         str(student_user_id), single_image_name)
        single_pdf_url = 'file:///%s/%s/writing/%s' % (current_app.config['USER_DATA_FOLDER'],
                                                       str(student_user_id), single_pdf_name)

    return marked_images, single_image_url, single_pdf_url


def get_w_report_template(assessment_enroll_id, student_user_id, marking_writing_id, pdf, pdf_url=None):
    if marking_writing_id == 0:
        marking_writings = MarkingForWriting.query \
            .join(Marking, Marking.id == MarkingForWriting.marking_id) \
            .filter(Marking.assessment_enroll_id == assessment_enroll_id) \
            .all()
    else:
        marking_writings = MarkingForWriting.query.filter_by(id=marking_writing_id).all()

    if marking_writings:
        for marking_writing in marking_writings:
            marking = Marking.query.filter_by(id=marking_writing.marking_id). \
                filter_by(assessment_enroll_id=assessment_enroll_id).first()

            # Create merged writing markings
            marking_writing.marked_images, single_image, single_pdf = get_merged_images(student_user_id, marking_writing,
                                                                            local_file=pdf)
            if marking.item_id:
                item = Item.query.filter_by(id=marking.item_id).first()
                marking_writing.item_name = item.name

        # Query Assessment information
        ts_id = marking.testset_id
        row = AssessmentEnroll.query.with_entities(AssessmentEnroll.assessment_id, AssessmentEnroll.grade,
                                                   AssessmentEnroll.start_time_client). \
            filter_by(id=assessment_enroll_id). \
            filter_by(testset_id=ts_id). \
            filter_by(student_user_id=student_user_id).first()
        if row:
            # My Report : Header - 'total_students', 'student_rank', 'score', 'total_score', 'percentile_score'
            assessment_name = (
                Assessment.query.with_entities(Assessment.name).filter_by(id=row.assessment_id).first()).name
            item_name = (Item.query.with_entities(Item.name).filter_by(id=marking.item_id).first()).name
            grade = row.grade
            test_date = row.start_time_client

            ts_header = query_my_report_header(assessment_enroll_id, row.assessment_id, ts_id, student_user_id)
            # get writing score from marking_writing table
            my_score = query_writing_report_score(marking.id)

            if ts_header is None:
                url = request.referrer
                flash('Marking data not available')
                return redirect(url)
            # score = '{} out of {} ({}%)'.format(ts_header.score, ts_header.total_score, ts_header.percentile_score)
            score = '{} out of {} ({}%)'.format(my_score['score'], my_score['total_score'], my_score['percentile_score'])
            rank = '{} out of {}'.format(ts_header.student_rank1, ts_header.total_students1)

            template_file = 'writing/my_report_writing.html'
            if pdf:
                template_file = 'writing/my_report_writing_pdf.html',
            student = User.query.filter_by(id=student_user_id).first()
            rendered_template_pdf = render_template(template_file,
                                                    assessment_name=assessment_name, item_name=item_name,
                                                    grade=grade, test_date=test_date,
                                                    rank=rank, score=score,
                                                    marking_writings=marking_writings,
                                                    static_folder=current_app.static_folder,
                                                    student=student,
                                                    pdf_url=pdf_url)
            return rendered_template_pdf
        else:
            return 'fail-enrollment'
    else:
        return 'fail-marking'


@login_required
@permission_required(Permission.WRITING_READ)
@writing.route('/report/<int:assessment_enroll_id>/<int:student_user_id>/<int:marking_writing_id>', methods=['GET'])
@login_required
def w_report(assessment_enroll_id, student_user_id, marking_writing_id=None):
    """
    Menu Writing > Marking > Click 'search writing' > Click 'link to Marking' page
    :param marking_writing_id:
    :param student_user_id:
    :return: the specific student's writing information for marking by marker
    """

    if current_user.id == student_user_id:
        redirect_url_for_name = 'report.list_my_report'
    else:
        redirect_url_for_name = 'writing.manage'
    pdf = False
    pdf_url = "%s?type=pdf" % request.url
    if 'type' in request.args.keys():
        pdf = request.args['type'] == 'pdf'

    rendered_template_pdf = get_w_report_template(assessment_enroll_id, student_user_id, marking_writing_id, pdf, pdf_url)

    if rendered_template_pdf == 'fail-enrollment':
        return redirect(url_for(redirect_url_for_name, error='Not found assessment enroll - writing data'))
    elif rendered_template_pdf == 'fail-enrollment':
        return redirect(url_for(redirect_url_for_name, error='Not found Marking for writing data'))
    else:
        if not pdf:
            return rendered_template_pdf
        # PDF download
        from weasyprint import HTML
        html = HTML(string=rendered_template_pdf)

        pdf_file_path = os.path.join(current_app.config['USER_DATA_FOLDER'],
                                     str(student_user_id),
                                     "writing",
                                     "%s_%s_%s.pdf" % (assessment_enroll_id, student_user_id, marking_writing_id))
        html.write_pdf(target=pdf_file_path, presentational_hints=True)
        rsp = send_file(
            pdf_file_path,
            mimetype='application/pdf',
            as_attachment=True,
            attachment_filename=pdf_file_path)
        return rsp


@login_required
@permission_required(Permission.WRITING_READ)
@writing.route('/marking/<int:marking_writing_id>/<int:student_user_id>', methods=['GET'])
@login_required
def marking(marking_writing_id, student_user_id):
    """
    Menu Writing > Marking > Click 'search writing' > Click 'link to Marking' page
    :param marking_writing_id:
    :param student_user_id:
    :return: the specific student's writing information for marking by marker
    """
    form = WritingMarkingForm()
    form.marking_writing_id.data = marking_writing_id
    form.student_user_id.data = student_user_id
    marking_writing = MarkingForWriting.query.filter_by(id=marking_writing_id).first()
    item = None
    if marking_writing:
        item = Marking.query.filter_by(id=marking_writing.marking_id).first()

    if marking_writing and canMarking(current_user, marking_writing.marking_id) and item:
        item_id = item.item_id
        web_img_links = marking_onscreen_load(marking_writing_id, student_user_id)
        if len(web_img_links.keys()):
            if marking_writing.candidate_mark_detail:
                populate_criteria_form(form, marking_writing_id,
                                       marking_writing.candidate_mark_detail)  # SubForm data populate from the db
            else:
                populate_criteria_form(form, marking_writing_id)
            form.markers_comment.data = marking_writing.markers_comment
            return render_template('writing/marking_onscreen_gradient.html', form=form, item_id=item_id,
                                   web_img_links=web_img_links,
                                   timestamp=str(round(time.time() * 1000)))
        #capture file is required. if there is no a capture, go on under error page. stop under function
        #else:
        #    log.debug('Marking For Writing: id(%s),student_user_id(%s) - marking_onscreen_load return null' % (
        #        marking_writing_id, student_user_id))
    else:
        if marking_writing:
            log.debug('Marking For Writing: id(%s),student_user_id(%s) - student writing data not found' % (
                marking_writing_id, student_user_id))
            flash('student writing data not found')
        elif not item:
            log.debug('Marking For Writing: id(%s),student_user_id(%s) - student answer data not found' % (
                marking_writing_id, student_user_id))
            flash('student answer data not found')
        else:
            log.debug('Marking For Writing: id(%s),student_user_id(%s) - canMarking return false' % (
                marking_writing_id, student_user_id))
            flash('Not authorised to get the resource requested')
    return render_template('writing/marking_empty.html')


def populate_criteria_form(form, marking_writing_id, criteria_detail=None):
    """
    Call from writing.marking(marking_writing_id, student_user_id) to populate form - fieldList Criteria information
    :param form:
    :param marking_writing_id: marking_writing.id
    :param criteria_detail:
    :return:
    """
    test_type_code_id = (db.session.query(Testset.test_type). \
                         join(Marking, Marking.testset_id == Testset.id). \
                         join(MarkingForWriting, MarkingForWriting.marking_id == Marking.id). \
                         filter(MarkingForWriting.id == marking_writing_id).first()
                         ).test_type
    criteria = Codebook.query.filter_by(code_type='criteria').filter_by(parent_code=test_type_code_id).order_by(
        Codebook.id).all()
    if criteria_detail is None:
        while len(form.markings) > 0:
            form.markings.pop_entry()

        for c in criteria:
            wm_form = WritingMMForm()  # weight mapping
            wm_form.criteria = c.code_name
            wm_form.marking = 0
            if c.additional_info:
                try:
                    wm_form.max_score = c.additional_info['max_score']
                except TypeError:
                    flash('Check if max_score of "%s" correctly entered. ' % c.code_name)
                    wm_form.max_score = 0.0
            else:
                wm_form.max_score = 0.0
            form.markings.append_entry(wm_form)
    else:
        while len(form.markings) > 0:
            form.markings.pop_entry()
        for c in criteria:
            wm_form = WritingMMForm()  # weight mapping
            wm_form.criteria = c.code_name

            try:
                wm_form.marking = float(criteria_detail[c.code_name])
            except TypeError:
                flash("Invalid Criteria: %s " % c.code_name)
                pass
            if c.additional_info:
                wm_form.max_score = float(c.additional_info['max_score'])
            else:
                wm_form.max_score = 0.0
            form.markings.append_entry(wm_form)
    return form


@writing.route('/marking_complete', methods=['GET'])
@login_required
@permission_required(Permission.WRITING_READ)
def marking_complete():
    data = json.loads(request.args.get("data"))
    return render_template('writing/marking_complete.html', data=data)


@login_required
@permission_required(Permission.WRITING_READ)
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
        # Update MarkingForWriting table
        row.markers_comment = form.markers_comment.data
        row.marker_id = current_user.id
        # json_str = { 'entry' : form.markings.data }
        json_str = {}
        candidate_mark = 0
        for entry in form.markings.data:
            json_str[entry['criteria']] = str(entry['marking'])
            candidate_mark = candidate_mark + int(entry['marking'])
        row.candidate_mark_detail = json_str
        db.session.add(row)
        # Update Marking table > candidate_mark
        marking = Marking.query.filter_by(id=row.marking_id).first()
        marking.candidate_mark = candidate_mark / len(form.markings.data)
        db.session.add(marking)
        db.session.commit()

        data = {"student": Student.getCSStudentName(form.student_user_id.data),
                "marking": json_str,
                "comments": form.markers_comment.data}
        return redirect(url_for('writing.marking_complete', data=json.dumps(data)))
    return redirect(url_for('writing.manage', error="Marking Edit - Form validation Error"))


@login_required
@permission_required(Permission.WRITING_READ)
@writing.route('/marking_onscreen/<int:marking_writing_id>/<int:student_user_id>', methods=['GET'])
@login_required
def marking_onscreen_load(marking_writing_id, student_user_id):
    marking_writing = MarkingForWriting.query.filter_by(id=marking_writing_id).first()
    web_img_links = {}
    if marking_writing.candidate_file_link:
        for key, file_name in marking_writing.candidate_file_link.items():
            if file_name:
                file_path = os.path.join(current_app.config['USER_DATA_FOLDER'], str(student_user_id), "writing",
                                         file_name)
                if os.path.exists(file_path):
                    web_img_links[key] = {
                        'writing': url_for('api.get_writing', marking_writing_id=marking_writing_id,
                                           student_user_id=student_user_id, file=file_name)}
                else:
                    log.debug("writing file not found: marking_writing_id(%s) student_user_id(%s) - filename(%s)"
                              % (marking_writing_id, student_user_id, file_path))
                if marking_writing.marked_file_link:
                    if key in marking_writing.marked_file_link.keys():
                        if os.path.exists(
                                os.path.join(current_app.config['USER_DATA_FOLDER'], str(student_user_id),
                                             "writing", marking_writing.marked_file_link[key])):
                            web_img_links[key]['marking'] = url_for('api.get_writing',
                                                                    marking_writing_id=marking_writing_id,
                                                                    student_user_id=student_user_id,
                                                                    file=marking_writing.marked_file_link[key])
    return web_img_links


def text_to_images(student_user_id, file_path):
    file_name = os.path.basename(file_path)
    image_x = 1200
    image_y = 1596
    left_margin = 40
    right_margin = 20
    font_size = 30
    line_space = 10
    width = image_x - left_margin - right_margin
    characters_per_line = int(width / (font_size / 2.0))
    lines_per_page = int(image_y / (font_size + line_space * 1.5))
    file_names = []
    with open(file_path, "r") as f:
        paragraphs = f.readlines()
        pages = []
        contents_wrapped = []
        for paragraph in paragraphs:
            from textwrap import wrap
            paragraph_wrapped = wrap(paragraph, characters_per_line)
            # Filter out whitespace line
            if paragraph_wrapped:
                contents_wrapped += paragraph_wrapped
                contents_wrapped += '\n'
        while len(contents_wrapped):
            joined_line = '\n'.join(contents_wrapped[:lines_per_page])
            pages.append(joined_line.replace('\n\n', '\n'))
            del contents_wrapped[:lines_per_page]

        fnt = ImageFont.truetype('app/static/writing/font/Kalam-Regular.ttf', font_size)
        count = 1
        for p in pages:
            # Create and save image files
            img = Image.new('RGB', (width, image_y), (255, 255, 255))
            d = ImageDraw.Draw(img)
            d.multiline_text((left_margin, 10), p, font=fnt, spacing=line_space, fill=(0, 0, 0))
            saved_file_name = os.path.splitext(file_name)[0] + str(count) + ".jpg"
            img.save(os.path.join(current_app.config['USER_DATA_FOLDER'], str(student_user_id),
                                  "writing", saved_file_name))
            count += 1
            file_names.append(saved_file_name)
    return file_names


@login_required
@permission_required(Permission.WRITING_READ)
@writing.route('/marking_onscreen', methods=['POST'])
@login_required
def marking_onscreen_save():
    """
    Save onscreen marking an an image
    :return:
    """
    if request:
        writing_id = request.json["writing_id"]
        student_user_id = request.json["student_user_id"]
        key = request.json["key"];
        writing_path = request.json["writing_path"]
        marking_path = request.json["marking_path"]
        marking_image = request.json["marking_image"]

        if writing_path:
            marking_file_name = None
            marking_file_name_merging = None

            if marking_path:
                marking_file_name = os.path.basename(marking_path)
            if not marking_file_name:
                writing_file_name = os.path.splitext(os.path.basename(writing_path))[0]
                marking_file_name = writing_file_name + "_marking.png"
            marking_file_save_path = os.path.join(current_app.config['USER_DATA_FOLDER'], student_user_id, "writing",
                                                  marking_file_name).replace('\\', '/')


            # Save image
            r = urllib.request.urlopen(marking_image)
            with open(marking_file_save_path, 'wb') as f:
                f.write(r.file.read())




            writing_file_save_path = os.path.join(current_app.config['USER_DATA_FOLDER'], student_user_id, "writing",
                                                  os.path.basename(writing_path)).replace('\\', '/')

            im = Image.open(writing_file_save_path)

            img = Image.open(r)
            width, height = img.size
            img.close()

            im1 = im.crop()
            newsize = (width, height)
            im1 = im1.resize(newsize)
            #im1.save(writing_file_name + "_merging" + os.path.splitext(os.path.basename(writing_path))[1])
            #im1.save(os.path.join(current_app.config['USER_DATA_FOLDER'], student_user_id, "writing").replace('\\', '/'), 'JPG')
            im1.save(os.path.join(current_app.config['USER_DATA_FOLDER'], student_user_id, "writing", writing_file_name + "_merging" + os.path.splitext(os.path.basename(writing_path))[1]).replace('\\', '/'))

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


def canMarking(marker, marking_id):
    # Admin user : pass
    if marker.is_administrator():
        return True

    # Marker user assigned to Assessment : pass
    marking = Marking.query.filter_by(id=marking_id).first()
    marker_assigned = MarkerAssigned.query.filter_by(marker_id=marker.id). \
        filter_by(assessment_id=marking.enroll.assessment_id). \
        filter_by(delete=False).first()
    if marker_assigned:
        return True

    # Marker user branch Check - enrollment testing branch in marker-branch-ids: Pass
    branch_ids = getBranchIds(marker.id)
    is_markable = True if marking.enroll.test_center in branch_ids else False
    if is_markable:
        return True
    return False


def getBranchIds(marker_id):
    branch_ids = [row.branch_id for row in
                  db.session.query(MarkerBranch.branch_id).filter_by(marker_id=marker_id).all()]
    all_branches = []
    for branch_id in branch_ids:
        if Codebook.get_code_name(branch_id) == 'All':
            all_branches = [row.id for row in
                            db.session.query(Codebook.id).filter(Codebook.code_type == 'test_center').all()]
            break
    branch_ids += all_branches
    return branch_ids


def query_writing_report_score(marking_id):
    total_score = 0
    criteria = Codebook.query.filter_by(code_type='criteria').filter_by(parent_code=76).all()
    for _o in criteria:
        total_score += int(_o.additional_info.get('max_score'))

    score = 0
    percentile_score = 0
    marking_writing = MarkingForWriting.query.filter_by(marking_id=marking_id) \
        .order_by(MarkingForWriting.id.desc()).first()
    if marking_writing is not None:
        if marking_writing.candidate_mark_detail:
            for f_n in marking_writing.candidate_mark_detail.values():
                score += int(f_n)
    percentile_score = round(score / total_score * 100, 1)
    return_value = {"score": score, "total_score": total_score, "percentile_score": percentile_score}
    return return_value
