from datetime import datetime

import pytz
import requests
from flask import render_template, redirect, request, url_for, flash
from flask_login import login_required, login_user, logout_user, current_user
from requests.auth import HTTPBasicAuth

from common.logger import log
from config import Config
from . import auth
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, EditProfileAdminForm, SearchUserForm, \
    ResetPasswordRequestForm, ResetPasswordForm
from .. import db
from ..decorators import permission_required, admin_required
from ..email import send_email, send_password_reset_email
from ..models import User, Permission, Role, Codebook, MarkerBranch


@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint \
                and request.blueprint != 'auth' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    # if current_user.is_anonymous or current_user.confirmed:
    if current_user.confirmed:
        return redirect(url_for('web.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    log.info("Logging in")
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(url_for('web.index'))
        flash('Invalid username or password.')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('web.index'))


@auth.route('/logout_student')
@login_required
def logout_student():
    logout_user()
    return redirect(url_for('web.loggedout'))


@auth.route('/user/<int:id>', methods=['GET'])
@login_required
def user_profile(id=None):
    if not id:
        id = current_user.id
    user = User.query.filter_by(id=id).first()
    return render_template('auth/user.html', user=user)


@auth.route('/manage/delete', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def user_delete():
    form = request.form
    row = User.query.filter(User.id == form.get("user_id")).filter(User.active.isnot(False)).first()
    if row:
        row.active = False
        flash("{} has been deleted".format(row.username))
        row.modified_time = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('auth.user_manage'))
    return redirect(url_for('auth.user_manage', error="User Delete validation error!"))


@auth.route('/manage/recover/<int:id>', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def user_recover(id):
    row = User.query.filter(User.id == id).filter(User.active.is_(False)).first()
    if row:
        row.active = True
        flash("{} has been recovered".format(row.username))
        row.modified_date = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('auth.user_manage'))
    return redirect(url_for('auth.user_manage', error="User Recovery validation error!"))


@auth.route('/manage/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def user_edit_profile(id):
    user = User.query.get(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        role_name = (Role.query.filter_by(id=form.role.data).first()).name
        if user.username != form.username.data and role_name == 'Test_center':
            test_center = Codebook.query.filter_by(code_type='test_center').filter_by(code_name=user.username).first()
            if test_center:
                test_center.code_name = form.username.data
            else:
                Codebook.create_default_codeset(None, "test_center", form.username.data)
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)  # Role.relationship.backref=role
        db.session.commit()

        if form.branch.data:
            link_marker(user.id, form.branch.data)
        flash('The profile has been updated.')
        return redirect(url_for('auth.user_manage'))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id

    branch_ids = [sub.branch_id for sub in db.session.query(MarkerBranch.branch_id).filter(
        MarkerBranch.marker_id == user.id).filter(MarkerBranch.delete.isnot(True)).all()]
    form.branch.data = branch_ids
    return render_template('auth/edit_profile.html', form=form, user=user)


@auth.route('/manage', methods=['GET'])
@login_required
@permission_required(Permission.ADMIN)
def user_manage():
    email = request.args.get("email")
    username = request.args.get("username")
    error = request.args.get("error")
    if error:
        flash(error)

    searchUserform = SearchUserForm()
    searchUserform.email.data = email
    searchUserform.username.data = username
    query = User.query
    if searchUserform.email.data:
        query = query.filter(User.email.ilike('%{}%'.format(searchUserform.email.data)))
    if searchUserform.username.data:
        query = query.filter(User.username.ilike('%{}%'.format(searchUserform.username.data)))
    rows = query.order_by(User.id.desc()).all()
    return render_template('auth/manage.html', form=searchUserform, users=rows)


@auth.route('/new', methods=['GET'])
@login_required
@permission_required(Permission.ADMIN)
def new():
    error = request.args.get('error')
    if error:
        flash(error)

    form = RegistrationForm()
    return render_template('auth/new.html', form=form)


@auth.route('/register', methods=['POST'])
@login_required
@permission_required(Permission.ADMIN)
def register():
    form = RegistrationForm()
    role = Role.query.get(form.u_role.data[0])
    if form.validate_on_submit():
        user = User(email=form.u_email.data,
                    username=form.u_name.data,
                    password=form.u_pwd.data,
                    role=role,
                    confirmed=True,
                    active=True)
        db.session.add(user)
        db.session.commit()

        if form.branch.data:
            link_marker(user.id, form.branch.data)

        if form.u_role.data[1] == 'Test_center':
            test_center = Codebook.query.filter_by(code_type='test_center').filter_by(
                code_name=form.u_name.data).first()
            if not test_center:
                Codebook.create_default_codeset(None, "test_center", form.u_name.data)
        flash("User {} has been registered.".format(user.username))
        return redirect(url_for('auth.user_manage'))
    for key in form.errors.keys():
        flash(form.errors.get(key))
    return redirect(url_for('auth.user_manage', error="Registration - Form validation error"))


"""
ToDo: not yet fixed TypeError when trying confirmation
"""


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('web.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired')
    return redirect(url_for('web.index'))


"""
ToDo: not yet fixed TypeError when trying confirmation
"""


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('web.index'))


@auth.route('/change-password', methods=['GET'])
@login_required
def change_password():
    form = ChangePasswordForm()
    return render_template('auth/change_password.html', form=form)


@auth.route('/change-password', methods=['POST'])
@login_required
def set_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.commit()
            flash('Your password has been updated.')
            return redirect(url_for('web.index'))
        else:
            flash('Invalid password.')
    for key in form.errors.keys():
        flash(form.errors.get(key))
    return redirect(url_for('auth.user_profile', id=current_user.id))


@auth.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('web.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Password reset e-mail will be sent if the e-mail has been registered')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', title='Reset Password', form=form)


@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('web.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('web.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password = form.password.data
        db.session.commit()
        flash('Your password has been reset')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


def get_student_info(stud_id):
    """
    Get member info from CS_API
    :param stud_id: csonlineschool student id
    :return: a member info
    """
    print(Config.CS_API_URL + "/member/%s" % stud_id)
    info = requests.get(Config.CS_API_URL + "/member/%s" % stud_id,
                        auth=HTTPBasicAuth(Config.CS_API_USER, Config.CS_API_PASSWORD), verify=False).json()
    return info


def get_campuses():
    """
    Get compus info from CS_API. CSOnlineSchool has the info
    :return: List of campuses
    """
    info = requests.get(Config.CS_API_URL + "/campus",
                        auth=HTTPBasicAuth(Config.CS_API_USER, Config.CS_API_PASSWORD), verify=False).json()
    return info


def link_marker(marker_id, branch_ids):
    for branch_id in branch_ids:
        row = MarkerBranch.query.filter_by(marker_id=marker_id).filter_by(branch_id=branch_id).first()
        if row:
            if row.delete == True:
                row.delete = False
                row.modified_time = datetime.now(pytz.utc)
                db.session.add(row)
        else:
            ma = MarkerBranch(marker_id=marker_id, branch_id=branch_id)
            db.session.add(ma)

    d_ids = MarkerBranch.query.filter_by(marker_id=marker_id). \
        filter(MarkerBranch.branch_id.notin_(branch_ids)). \
        filter(MarkerBranch.delete.isnot(True)).all()
    for row in d_ids:
        row.delete = True
        row.modified_time = datetime.now(pytz.utc)
        db.session.add(row)
    flash('Marker has been successfully assigned to the branch(es).')
    db.session.commit()
    return True
