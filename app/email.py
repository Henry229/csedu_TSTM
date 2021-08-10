from threading import Thread

from flask import current_app, render_template
from flask_mail import Message

from . import mail

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['CSEDU_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['CSEDU_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(to=user.email,
               subject='[Tailored] Reset Your Password',
               template='auth/email/reset_password',
               user=user,
               token=token
               )


def common_send_email(sender, to, prefix, subject, path, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config[prefix] + ' ' + subject,
                  sender=sender, recipients=[to])
    msg.body = render_template(path + '.txt', **kwargs)
    msg.html = render_template(path + '.html', **kwargs)
    #mail.send(msg)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr


"""
Sample for email:
app/auth/templates/auth/email/confirm.html
app/auth/templates/auth/email/confirm.txt

Dear {{user.username}},

Welcome to CS Education Family!

To confirm your account please click on the following link:

{{url_for('auth.confirm', token=token, _external=True)}}

Sincerely,

CS Education

Note: replies to this email address are not monitored.
"""
