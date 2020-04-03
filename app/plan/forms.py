from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, HiddenField, StringField

from ..models import Choices


class EducationPlanSearchForm(FlaskForm):
    class Meta:
        csrf = False

    plan_name = StringField('Plan Name', id='search_name')
    year = SelectField('Year')
    grade = SelectField('Grade', id='search_grade', coerce=int)
    test_type = SelectField('Test Type', id='search_type', coerce=int)
    submit = SubmitField('Search')

    def __init__(self, *args, **kwargs):
        super(EducationPlanSearchForm, self).__init__(*args, **kwargs)
        self.test_type.choices = Choices.get_codes('test_type')
        self.grade.choices = Choices.get_codes('grade')
        self.year.choices = Choices.get_ty_choices()


class EducationPlanCreateForm(FlaskForm):
    plan_id = HiddenField('Id', default='')
    plan_name = StringField('Education Plan Name', default='')
    year = SelectField('Year', default=str(datetime.now().year))
    grade = SelectField('Grade', coerce=int)
    test_type = SelectField('Test Type', coerce=int)
    submit = SubmitField('Search')

    def __init__(self, *args, **kwargs):
        super(EducationPlanCreateForm, self).__init__(*args, **kwargs)
        self.test_type.choices = Choices.get_codes('test_type')
        self.grade.choices = Choices.get_codes('grade')
        self.year.choices = Choices.get_ty_choices()


class EducationPlanDetailCreateForm(FlaskForm):
    ordered_ids = HiddenField('ordered_ids', id='ordered_ids', default='')
    ordered_plan_id = HiddenField('ordered_plan_id', id='ordered_plan_id', default='')
    submit = SubmitField('Save Assessments')


class AssessmentSearchForm(FlaskForm):
    class Meta:
        csrf = False

    assessment_name = StringField('Assessment Name', id='i_name')
    test_type = SelectField('Test Type', id='i_test_type', coerce=int)
    test_center = SelectField('CSEdu Branch', id='i_test_center', coerce=int)
    submit = SubmitField('Search')
    assessment_ids = HiddenField('assessment_ids', id='i_plan_assessment_ids', default='')
    plan_id = HiddenField('plan_id', id='i_plan_id', default='')

    def __init__(self, *args, **kwargs):
        super(AssessmentSearchForm, self).__init__(*args, **kwargs)
        self.test_type.choices = Choices.get_codes('test_type')
        self.test_center.choices = Choices.get_codes('test_center')


class CodebookForm(FlaskForm):
    class Meta:
        csrf = False

    test_type = SelectField('Test Type', id="select_test_type", coerce=int)
    level = SelectField('Level', id="select_level", coerce=int)
    test_center = SelectField('Test Centre', id='select_test_center', coerce=int)
    grade = SelectField('Grade', id='select_grade', coerce=int)
    subject = SelectField('Subject', id='select_subject', coerce=int)
    category = SelectField('Category', id='select_category', coerce=int)
    subcategory = SelectField('Sub Category',
                              id='select_subcategory',
                              coerce=int)
    criteria = SelectField('Criteria', id="select_criteria", coerce=int)
    branch_state = SelectField('Branch State', id="select_branch_state")
    submit = SubmitField('Search')

    def __init__(self, *args, **kwargs):
        super(CodebookForm, self).__init__(*args, **kwargs)
        self.test_type.choices = Choices.get_codes('test_type')
        self.level.choices = [(0, '')]
        self.test_center.choices = Choices.get_codes('test_center')
        self.grade.choices = Choices.get_codes('grade')
        self.subject.choices = Choices.get_codes('subject')
        self.category.choices = [(0, '')]
        self.subcategory.choices = [(0, '')]
        # self.criteria.choices = Choices.get_codes('criteria')
        self.criteria.choices = [(0, '')]
        self.branch_state.choices = Choices.get_branch_state_choices()
