import datetime

from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import DateField, TimeField, SelectField, SubmitField, HiddenField, StringField, IntegerField
from wtforms.validators import DataRequired, Optional, ValidationError
from wtforms.widgets import html5

from ..models import Choices, Codebook


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

    test_type = SelectField('Test Type', coerce=int)
    test_center = SelectField('CSEdu Branch', coerce=int)
    active = SelectField('Active', choices=[('', ''), ('1', 'True'), ('0', 'False')], default='1')

    def __init__(self, *args, **kwargs):
        super(AssessmentSearchForm, self).__init__(*args, **kwargs)
        self.test_type.choices = Choices.get_codes('test_type')
        self.test_center.choices = get_test_center()


class AssessmentCreateForm(FlaskForm):
    assessment_id = HiddenField('Id', default='')
    assessment_name = StringField('Name', default='', validators=[DataRequired()])
    test_type = SelectField('Test Type', coerce=int, validators=[DataRequired()])
    test_center = SelectField('CSEdu Branch', coerce=int, validators=[DataRequired()])
    year = SelectField('Year', default=datetime.date.today().year)
    term = SelectField('Term', default='')
    unit = SelectField('Unit', default='')
    test_detail = StringField('Test Number', default='')
    review_period = IntegerField('Review Period', default=7, widget=html5.NumberInput(min=0, max=28, step=7))
    session_date = DateField('Test Date', validators=[Optional()])
    session_valid_until = DateField('Valid Until(Homework only)', validators=[Optional()])
    session_start_time = TimeField('Session Time')
    session_end_time = TimeField('Session Time')
    submit = SubmitField('Save')



    def __init__(self, *args, **kwargs):
        super(AssessmentCreateForm, self).__init__(*args, **kwargs)
        self.test_type.choices = Choices.get_codes('test_type')
        self.test_center.choices = get_test_center()
        self.year.choices = Choices.get_ty_choices()
        self.term.choices = [('', ''), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')]
        self.unit.choices = [('', ''), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'), ('15', '15')]

class AssessmentTestsetCreateForm(FlaskForm):
    ordered_ids = HiddenField('ordered_ids', id='ordered_ids', default='')
    ordered_assessment_id = HiddenField('ordered_assessment_id', id='ordered_assessment_id', default='')
    submit = SubmitField('Save Testsets')


class TestsetSearchForm(FlaskForm):
    class Meta:
        csrf = False

    testset_name = StringField('Testset Name', id='t_name')
    grade = SelectField('Grade', id='t_grade', coerce=int)
    subject = SelectField('Subject', id='t_subject', coerce=int)
    test_type = SelectField('Test Type', id='t_test_type', coerce=int)
    submit = SubmitField('Search')
    assessment_id = HiddenField('assessment_id', id='i_assessment_id', default='')
    submit = SubmitField('Search')

    def __init__(self, *args, **kwargs):
        super(TestsetSearchForm, self).__init__(*args, **kwargs)
        self.grade.choices = Choices.get_codes('grade')
        self.subject.choices = Choices.get_codes('subject')
        self.test_type.choices = Choices.get_codes('test_type')
