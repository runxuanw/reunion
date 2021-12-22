from django.core.mail import send_mail
from .models import MeetingPreference


SCHOOL_REUNION_ADMIN_EMAIL = 'reunion4school@gmail.com'


def _verification_link(verification_code):
    # todo: formalize the host
    return f'<a href="https://127.0.0.1:8000/email_verification/{verification_code}>Click Me To Verify</a>"'


def verify_registered_email_address(meeting_preference: MeetingPreference, meeting_name):
    message = (f'Please click the following link to confirm your registration for Meeting {meeting_name}:'
               f'\n{_verification_link(meeting_preference.email_verification_code)}')
    send_mail(
        'Verify Email For School Reunion',
        message,
        SCHOOL_REUNION_ADMIN_EMAIL,
        [meeting_preference.email],
        fail_silently=False
    )


def send_scheduled_meeting_notification(email):
    pass
