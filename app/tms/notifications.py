from flask_mail import Message
from flask import current_app
from app import mail
from twilio.rest import Client

def send_email(subject, recipients, text_body, html_body=None):
    """Send an email using Flask-Mail."""
    msg = Message(subject, recipients=recipients)
    msg.body = text_body
    if html_body:
        msg.html = html_body
    mail.send(msg)

def send_sms(body, to):
    """Send an SMS using Twilio."""
    account_sid = current_app.config['TWILIO_ACCOUNT_SID']
    auth_token = current_app.config['TWILIO_AUTH_TOKEN']
    from_number = current_app.config['TWILIO_FROM_NUMBER']
    client = Client(account_sid, auth_token)
    message = client.messages.create(body=body, from_=from_number, to=to)
    return message.sid
