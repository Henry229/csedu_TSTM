import re

from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import case
from wtforms import SelectField, SubmitField, HiddenField, StringField, MultipleFileField, \
    TextAreaField, FieldList, FormField, SelectMultipleField, DecimalField
from wtforms.validators import DataRequired

from .. import db
from ..models import Choices, EducationPlan, Codebook, User, MarkerBranch, Role, Assessment


class StartOnlineTestForm(FlaskForm):
    assessment_guid = StringField('Assessment GUID', validators=[DataRequired()])
    student_user_id = StringField('Student ID', validators=[DataRequired()])
    submit = SubmitField('Start')


class WritingTestForm(FlaskForm):
    w_image = MultipleFileField('Writing File')
    w_text = TextAreaField('Writing Text')
    assessment_guid = HiddenField('Assessment GUID', validators=[DataRequired()])
    student_user_id = HiddenField('Student ID', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def validate_image(form, field):
        if field.data:
            field.data = re.sub(r'[^a-z0-9_.-]', '_', field.data)


def get_test_center():
    my_codesets = []
    sql = Codebook.query.filter_by(code_type='test_center')
    if (current_user.role.name == 'Moderator') or (current_user.role.name == 'Administrator'):
        sql = sql
    elif current_user.role.name == 'Test_center':
        sql = sql.filter(Codebook.code_name == current_user.username)

    codesets = sql.all()

    if codesets:
        for codeset in codesets:
            code = (codeset.id, codeset.code_name)
            my_codesets.append(code)
    if len(my_codesets) > 1:
        my_codesets = sorted(my_codesets, key=lambda x: x[1])
    return my_codesets


class AssessmentSearchForm(FlaskForm):
    class Meta:
        csrf = False

    assessment_name = StringField('Assessment Name', id='i_name')
    year = SelectField('Year')
    test_type = SelectField('Test Type', id='i_test_type', coerce=int)
    test_center = SelectField('CSEdu Branch', id='i_test_center', coerce=int)
    submit = SubmitField('Search')
    assessment_guid = HiddenField('assessment_guid', id='i_assessment_guid', default='')

    def __init__(self, *args, **kwargs):
        super(AssessmentSearchForm, self).__init__(*args, **kwargs)
        self.year.choices = [(ts.year, ts.year)
                             for ts in
                             db.session.query(EducationPlan.year).distinct().order_by(EducationPlan.year).all()]
        self.test_type.choices = Choices.get_codes('test_type')
        self.test_center.choices = get_test_center()


class WritingMMForm(FlaskForm):
    class Meta:
        csrf = False

    criteria = StringField('Criteria', default='')
    marking = DecimalField('Mark', default=0.0, places=0)
    max_score = HiddenField('Max Score', default=0.0)


class WritingMarkingForm(FlaskForm):
    marking_writing_id = HiddenField('Id', default='')
    student_user_id = HiddenField('Student Id', default='')
    markers_comment = TextAreaField("Marker's comment")
    markings = FieldList(FormField(WritingMMForm))  # marking mapping
    submit = SubmitField('Save')


class MarkerAssignForm(FlaskForm):
    assessment_id = HiddenField('Id', default='')
    markers = SelectMultipleField('To', id='marker_ids', coerce=int)
    year = HiddenField('year')
    test_type = HiddenField('test_type')
    test_center = HiddenField('test_center')

    submit = SubmitField('Assign')

    def __init__(self, branch_id, *args, **kwargs):
        super(MarkerAssignForm, self).__init__(*args, **kwargs)
        branch_name = Codebook.get_code_name(branch_id)
        if (branch_name=='All'):
            role = Role.query.filter_by(name='Writing_marker').first()
            self.markers.choices = [(u.id, u.username)
                                    for u in
                                    db.session.query(User.id, User.username).filter(User.role == role).filter(User.delete.isnot(True)).distinct().order_by(
                                        User.username).all()]
        else:
            marker_ids = [sub.marker_id for sub in db.session.query(MarkerBranch.marker_id).filter(
                MarkerBranch.branch_id == branch_id).filter(MarkerBranch.delete.isnot(True)).all()]
            self.markers.choices = [(id, User.getUserName(id)) for id in marker_ids]


class MarkingListSearchForm(FlaskForm):
    assessment_name = StringField('Assessment Name', id='i_name')
    grade = SelectField('Grade')
    marked = SelectField('Marked', choices=[('', ''), ('1', ' Y '), ('0', ' N ')], default='')
    submit = SubmitField('Search')
    year = SelectField('Year')
    test_type = SelectField('Test Type')
    marker_name = SelectField('Marker')
    assessment = SelectField('Assessment')

    def __init__(self, *args, **kwargs):
        super(MarkingListSearchForm, self).__init__(*args, **kwargs)
        grades = [('', 'All')]
        _grades = Codebook.query.filter_by(code_type='grade').all()
        if _grades:
            for _grade in _grades:
                code = (_grade.id, _grade.code_name)
                grades.append(code)
        self.grade.choices = grades
        self.year.choices = [(ts.year, ts.year)
                             for ts in
                             db.session.query(Assessment.year).filter(Assessment.year.isnot(None)).distinct().order_by(Assessment.year).all()]
        self.test_type.choices = Choices.get_codes('test_type')
        self.assessment.choices = [(0, '')]

        if current_user.is_administrator():
            xpr_marker_name = case([(User.username != None, User.username), ],
                                   else_=User.email).label("marker_name")

            self.marker_name.choices = [(mk.marker_id, mk.marker_name)
                    for mk in
                    db.session.query(MarkerBranch.marker_id, xpr_marker_name).
                    join(User, MarkerBranch.marker_id == User.id).
                    filter(MarkerBranch.delete.isnot(True)).
                    filter(User.active.isnot(False)).
                    filter(User.delete.isnot(True)).
                    distinct().
                    order_by(User.username).all()]
