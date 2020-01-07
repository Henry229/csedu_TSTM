from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, \
    SubmitField
from wtforms.validators import DataRequired


class StartOnlineTestForm(FlaskForm):
    assessment_guid = StringField('Assessment GUID', validators=[DataRequired()])
    student_user_id = StringField('Student ID', validators=[DataRequired()])
    submit = SubmitField('Start')


class ItemModifyForm(FlaskForm):
    grade = SelectField('Grade', choices=[('', ''), ('K', 'K'), ('Y1', 'Y1'), ('Y2', 'Y2'), ('Y3', 'Y3'), ('Y4', 'Y4'),
                                          ('Y5', 'Y5'), ('Y6', 'Y6'), ('Y7', 'Y7')], default='')
    subject = SelectField('Subject', choices=[('', ''), ('Maths', 'Maths'), ('English', 'English')], default='')
    level = SelectField('Level',
                        choices=[('', ''), ('L1', 'L1'), ('L2', 'L2'), ('L3', 'L3'), ('L4', 'L4'), ('L5', 'L5'),
                                 ('L6', 'L6'), ('L7', 'L7'), ('L8', 'L8'), ('L9', 'L9'), ('L10', 'L10')], default='')
    category = SelectField('Category', choices=[('', ''), ('Category1', 'Category1'), ('Category2', 'Category2')],
                           default='')
    subcategory = SelectField('Sub Category',
                              choices=[('', ''), ('SubCategory1', 'SubCategory1'), ('SubCategory2', 'SubCategory2')],
                              default='')
    submit = SubmitField('Modify')
