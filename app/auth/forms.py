from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, \
    SelectField, SelectMultipleField, HiddenField
from wtforms import ValidationError
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo

from app import db
from ..models import User, Role, Codebook


def get_roles():
    role = db.session.query(Role.id, Role.name).order_by(Role.name).all()
    return role


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Length(1, 64), Email(message='Type a correct email address.')])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    u_name = StringField('Name', validators=[DataRequired(), Length(1, 64)])
    u_email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    u_pwd = PasswordField('Password', validators=[DataRequired(),
                                                  EqualTo('u_pwd2', message='Passwords must match.')])
    u_pwd2 = PasswordField('Confirm password', validators=[DataRequired()])
    u_role = QuerySelectField('Role', query_factory=get_roles,
                              get_pk=lambda a: a.id,
                              get_label=lambda a: a.name)
    branch = SelectMultipleField('Assign Branch', id='branch_ids', coerce=int)
    submit = SubmitField('Register')

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.branch.choices = [(u.id, u.code_name)
                               for u in
                               db.session.query(Codebook.id, Codebook.code_name). \
                                   filter(Codebook.code_type == 'test_center').distinct().order_by(
                                   Codebook.code_name).all()]

    def validate_u_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_u_name(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password', validators=[DataRequired()])
    password = PasswordField('New password',
                             validators=[DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm new password', validators=[DataRequired()])
    submit = SubmitField('Update Password')


class SearchUserForm(FlaskForm):
    email = StringField('Email')
    username = StringField('Username')
    role = SelectField('Role', id='role', coerce=int)
    submit = SubmitField('Search')

    def __init__(self, *args, **kwargs):
        super(SearchUserForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]


class EditProfileForm(FlaskForm):
    name = StringField('Real Name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('Name', validators=[DataRequired(), Length(1, 64)])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', id='u_role', coerce=int)
    branch = SelectMultipleField('Assign Branch', id='branch_ids', coerce=int)

    # name = StringField('Real name', validators=[Length(1,64)])
    # location = StringField('Location', validators=[Length(0,64)])
    # about_me = TextAreaField('About me')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.branch.choices = [(u.id, u.code_name)
                               for u in
                               db.session.query(Codebook.id, Codebook.code_name).filter(
                                   Codebook.code_type == 'test_center'). \
                                   distinct().order_by(Codebook.code_name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Registered Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired()])
    password_confirm = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class MarkerLinkForm(FlaskForm):
    branch_id = HiddenField('branch_id', default='')
    markers = SelectMultipleField('To', id='marker_ids', coerce=int)

    submit = SubmitField('Link')

    def __init__(self, *args, **kwargs):
        super(MarkerLinkForm, self).__init__(*args, **kwargs)
        role = Role.query.filter_by(name='Writing_marker').first()
        self.markers.choices = [(u.id, u.username)
                                for u in
                                db.session.query(User.id, User.username).filter(User.role == role).distinct().order_by(
                                    User.username).all()]
