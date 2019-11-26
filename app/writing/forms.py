from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, HiddenField, StringField, FileField, TextAreaField, FieldList, FormField
from wtforms.validators import DataRequired
from .. import db
from ..models import Choices, EducationPlan, Codebook
import re

class StartOnlineTestForm(FlaskForm):
    assessment_guid = StringField('Assessment GUID', validators=[DataRequired()])
    student_id = StringField('Student ID', validators=[DataRequired()])
    submit = SubmitField('Start')


class WritingTestForm(FlaskForm):
    w_image = FileField('Writing File')
    w_text = TextAreaField('Writing Text')
    assessment_guid = HiddenField('Assessment GUID', validators=[DataRequired()])
    student_id = HiddenField('Student ID', validators=[DataRequired()])
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
    marking = StringField('Mark', default='0.0')


class WritingMarkingForm(FlaskForm):
    marking_writing_id = HiddenField('Id', default='')
    student_id = HiddenField('Student Id', default='')
    markers_comment = TextAreaField("Marker's comment")
    markings = FieldList(FormField(WritingMMForm))  # marking mapping
    submit = SubmitField('Save')

