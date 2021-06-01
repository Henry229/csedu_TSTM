from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, BooleanField, HiddenField, StringField
from wtforms.fields.html5 import URLField
from wtforms.validators import DataRequired

from ..models import Choices


class TestsetSearchForm(FlaskForm):
    class Meta:
        csrf = False

    testset_id = HiddenField('Testset ID', id='search_id')
    testset_name = StringField('Testset Name', id='search_name')
    grade = SelectField('Grade', id='search_grade', coerce=int)
    subject = SelectField('Subject', id='select_subject', coerce=int)
    test_type = SelectField('Test Type', coerce=int)
    active = SelectField('Active', choices=[('', ''), ('1', 'True'), ('0', 'False')], default='1')
    completed = BooleanField('Completed?', default=False)
    submit = SubmitField('Search')

    def __init__(self, *args, **kwargs):
        super(TestsetSearchForm, self).__init__(*args, **kwargs)
        self.grade.choices = Choices.get_codes('grade')
        self.subject.choices = Choices.get_codes('subject')
        self.test_type.choices = Choices.get_codes('test_type')


class TestsetCreateForm(FlaskForm):
    testset_id = HiddenField('Id', default='')
    testset_name = StringField('Name', default='', validators=[DataRequired()])
    test_type = SelectField('Test Type', coerce=int, validators=[DataRequired()])
    grade = SelectField('Grade', coerce=int, validators=[DataRequired()])
    subject = SelectField('Subject', coerce=int, validators=[DataRequired()])
    no_stages = StringField('Number of stages', default='3', validators=[DataRequired()])
    test_duration = StringField('Test Duration', default='50', validators=[DataRequired()])
    total_score = StringField('Total Score', default='100')
    link1 = URLField('Explanation')
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super(TestsetCreateForm, self).__init__(*args, **kwargs)
        self.grade.choices = Choices.get_codes('grade')
        self.subject.choices = Choices.get_codes('subject')
        self.test_type.choices = Choices.get_codes('test_type')

