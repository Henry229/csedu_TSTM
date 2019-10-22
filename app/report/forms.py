from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy.sql import func
from wtforms import SelectField, BooleanField, SubmitField

from .. import db
from ..models import AssessmentEnroll, Choices, Codebook


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


class ReportSearchForm(FlaskForm):
    class Meta:
        csrf = False

    year = SelectField('Year')
    test_type = SelectField('Test Type', coerce=int)
    test_center = SelectField('CSEdu Branch', coerce=int)

    def __init__(self, *args, **kwargs):
        super(ReportSearchForm, self).__init__(*args, **kwargs)
        self.year.choices = [(ts.year, ts.year)
                             for ts in
                             db.session.query(func.to_char(AssessmentEnroll.created_time, 'YYYY').label("year")).
                                 distinct().order_by(
                                 func.to_char(AssessmentEnroll.created_time, 'YYYY').label("year")).all()]
        self.test_type.choices = Choices.get_codes('test_type')
        self.test_center.choices = get_test_center()


class ItemSearchForm(FlaskForm):
    class Meta:
        csrf = False

    grade = SelectField('Grade', id='select_grade',  coerce=int)
    subject = SelectField('Subject', id='select_subject', coerce=int)
    level = SelectField('Level', id='select_level', coerce=int)
    category = SelectField('Category', id='select_category', coerce=int)
    subcategory = SelectField('Sub Category',
                              id='select_subcategory',
                              coerce=int)
    active = BooleanField('active', default=True)
    submit = SubmitField('Search')

    def __init__(self, *args, **kwargs):
        super(ItemSearchForm, self).__init__(*args, **kwargs)
        self.grade.choices = Choices.get_codes('grade')
        self.subject.choices = Choices.get_codes('subject')
        self.level.choices = Choices.get_codes('level')
        self.category.choices = [(0, '')]
        self.subcategory.choices = [(0, '')]
