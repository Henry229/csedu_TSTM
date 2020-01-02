from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SelectField, SubmitField, BooleanField, StringField, \
    FieldList, FormField, TextAreaField, HiddenField
from wtforms.fields.html5 import URLField
from wtforms.validators import length


class ItemSearchForm(FlaskForm):
    class Meta:
        csrf = False

    grade = SelectField('Grade', coerce=int)
    subject = SelectField('Subject', id='select_subject', coerce=int)
    level = SelectField('Level', coerce=int)
    category = SelectField('Category', id='select_category', coerce=int)
    subcategory = SelectField('Sub Category',
                              id='select_subcategory',
                              coerce=int)
    byme = BooleanField('Imported by me')
    active = BooleanField('active', default=True)
    submit = SubmitField('Search')


class FileLoadForm(FlaskForm):
    # Item Import: Step 1 SelectBox and File for Load
    supported_exts = ['zip', 'xls', 'xlsx', 'xml']
    grade = SelectField('Grade',
                        coerce=int)
    subject = SelectField('Subject',
                          id='select_subject',
                          coerce=int)
    items_file = FileField('File',
                           validators=[FileAllowed(supported_exts, 'Only %s files are supported!' % ', '.join(supported_exts))])
    submit = SubmitField('Load')


class ItemListForm(FlaskForm):
    class Meta:
        csrf = False

    # Item Import: Step 2 List for Edit
    check = BooleanField('Label', default=True)
    item_id = StringField('Id', default='')
    item_name = StringField('Names', default='')
    correct_answer = StringField('Answers')  # answers which are imported items
    grade = StringField('Grade')  # grade which are imported items
    subject = StringField('Subjects')  # subjects which are imported items

    level = SelectField('Levels', coerce=int, default=0)  # levels which are imported items
    category = SelectField('Categories', coerce=int, default=0)
    subcategory = SelectField('Sub Category', coerce=int, default=0)  # subcategories which are imported items

    def __init__(self, *args, **kwargs):
        super(ItemListForm, self).__init__(*args, **kwargs)
        for key, value in kwargs.items():
            if key == 'level_choices':
                self.level.choices = value
            elif key == 'category_choices':
                self.category.choices = value
            elif key == 'subcategory_choices':
                self.subcategory.choices = value


class ItemLoadForm(FlaskForm):
    # Item Import: Step 1 & 2 SelectBox for Edit
    level = SelectField('Level',
                        coerce=int)
    category = SelectField('Category',
                           id='select_category',
                           coerce=int)
    subcategory = SelectField('Sub Category',
                              id='select_subcategory',
                              coerce=int)

    items = FieldList(FormField(ItemListForm))
    submit = SubmitField('Import')


class ItemEditSubForm(FlaskForm):
    class Meta:
        csrf = False

    # Item Import: Step 2 List for Edit
    check = BooleanField('Label', default=True)
    item_id = StringField('Id', default='')
    item_name = StringField('Names', default='')
    correct_answer = StringField('Answers')

    grade = SelectField('Grade', coerce=int, default=0)
    subject = SelectField('Subjects', coerce=int, default=0)
    level = SelectField('Levels', coerce=int, default=0)
    category = SelectField('Categories', coerce=int, default=0)
    subcategory = SelectField('Sub Category', coerce=int, default=0)
    active = BooleanField('active', default=True)

    def __init__(self, *args, **kwargs):
        super(ItemEditSubForm, self).__init__(*args, **kwargs)
        for key, value in kwargs.items():
            if key == 'grade_choices':
                self.grade.choices = value
            elif key == 'subject_choices':
                self.subject.choices = value
            elif key == 'level_choices':
                self.level.choices = value
            elif key == 'category_choices':
                self.category.choices = value
            elif key == 'subcategory_choices':
                self.subcategory.choices = value


class ItemEditForm(FlaskForm):
    grade = SelectField('Grade',
                        id='select_grade2',
                        coerce=int)
    subject = SelectField('Subject',
                          id='select_subject2',
                          coerce=int)
    level = SelectField('Level',
                        id='select_level2',
                        coerce=int)
    category = SelectField('Category',
                           id='select_category2',
                           coerce=int)
    subcategory = SelectField('Sub Category',
                              id='select_subcategory2',
                              coerce=int)
    byme = BooleanField('Imported by me')
    active = BooleanField('active', id='select_active2', default=True)

    items = FieldList(FormField(ItemEditSubForm))
    submit = SubmitField('Property Setup')


class ItemEditExplanationForm(FlaskForm):
    explanation = TextAreaField('Explanation', validators=[length(max=200)])
    image = FileField('Image',
                      validators=[FileAllowed(['png', 'gif', 'jpg'], 'Only Image Files are supported!')])
    link1 = URLField('link1')
    link2 = URLField('link2')
    link3 = URLField('link3')
    link4 = URLField('link4')
    link5 = URLField('link5')
    chx_remove = HiddenField("chx_remove")
    submit = SubmitField('Submit')
