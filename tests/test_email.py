import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from string import Template

from config import Config

def main():
    names = [Config.CSEDU_MAIL_SENDER]
    emails = [Config.CSEDU_ADMIN]
    message_template = Template('''
Dear ${PERSON_NAME}, 

This is a test message. 
Have a great weekend! 

Yours Truly
''')

    # set up the SMTP server
    s = smtplib.SMTP(host=Config.MAIL_SERVER, port=Config.MAIL_PORT)
    if Config.MAIL_USE_TLS:
        s.starttls()
    s.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)

    # For each contact, send the email:
    for name, email in zip(names, emails):
        msg = MIMEMultipart()  # create a message

        # add in the actual person name to the message template
        message = message_template.substitute(PERSON_NAME=name.title())

        # Prints out the message body for our sake
        print(message)

        # setup the parameters of the message
        msg['From'] = Config.CSEDU_MAIL_SENDER
        msg['To'] = email
        msg['Subject'] = "This is TEST"

        # add in the message body
        msg.attach(MIMEText(message, 'plain'))

        # send the message via the server set up earlier.
        s.send_message(msg)
        del msg

    # Terminate the SMTP session and close the connection
    s.quit()


if __name__ == '__main__':
    main()
