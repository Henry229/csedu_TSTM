from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, BooleanField, HiddenField, StringField, \
    FieldList, FormField

from ..models import Choices


class TestletSearchForm(FlaskForm):
    class Meta:
        csrf = False

    testlet_name = StringField('Testlet Name', id='search_name')
    grade = SelectField('Grade', id='search_grade', coerce=int)
    subject = SelectField('Subject', id='select_subject', coerce=int)
    completed = BooleanField('Completed?', default=False)
    submit = SubmitField('Search')

    def __init__(self, *args, **kwargs):
        super(TestletSearchForm, self).__init__(*args, **kwargs)
        self.grade.choices = Choices.get_codes('grade')
        self.subject.choices = Choices.get_codes('subject')


class TestletWMForm(FlaskForm):
    class Meta:
        csrf = False

    level = StringField('Level', default='')
    weight = StringField('weight', default='1.0')


class TestletCreateForm(FlaskForm):
    testlet_id = HiddenField('Id', default='')
    testlet_name = StringField('Name', default='')
    grade = SelectField('Grade', coerce=int)
    subject = SelectField('Subject', coerce=int)
    test_type = SelectField('Test Type', coerce=int)
    no_items = StringField('Number of items', default='')

    weights = FieldList(FormField(TestletWMForm))  # weight mapping
    submit = SubmitField('Save')

    def __init__(self, *args, **kwargs):
        super(TestletCreateForm, self).__init__(*args, **kwargs)
        self.grade.choices = Choices.get_codes('grade')
        self.subject.choices = Choices.get_codes('subject')
        self.test_type.choices = Choices.get_codes('test_type')


class TestletItemCreateForm(FlaskForm):
    ordered_ids = HiddenField('ordered_ids', id='ordered_ids', default='')
    ordered_testlet_id = HiddenField('ordered_testlet_id', id='ordered_testlet_id', default='')
    submit = SubmitField('Save Items')


class ItemSearchForm(FlaskForm):
    item_name = StringField('Item Name', id='i_name')
    grade = SelectField('Grade', id='i_grade', coerce=int)
    subject = SelectField('Subject', id='i_subject', coerce=int)
    level = SelectField('Level', id='i_level', coerce=int)
    category = SelectField('Category', id='i_category', coerce=int)
    byme = BooleanField('Imported by me', id='i_byme', default=True)
    item_ids = HiddenField('item_ids', id='i_testlet_item_ids', default='')
    testlet_id = HiddenField('testlet_id', id='i_testlet_id', default='')

    submit = SubmitField('Search')

    def __init__(self, *args, **kwargs):
        super(ItemSearchForm, self).__init__(*args, **kwargs)
        self.grade.choices = Choices.get_codes('grade')
        self.subject.choices = Choices.get_codes('subject')
        self.level.choices = Choices.get_codes('level')
