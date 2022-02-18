from django.core.mail import send_mail
from .models import MeetingPreference, MeetingRecord
from typing import List


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


def _invitation_link(record_id, invitation_id):
    return f'<a href="https://127.0.0.1:8000/confirm_invitation/{record_id}/{invitation_id}>Click Me To Confirm</a>"'


def send_scheduled_meeting_notification(meeting_record: MeetingRecord,
                                        invitation_id,
                                        preference: MeetingPreference,
                                        all_preference: List[MeetingPreference]):
    message = (f'Please click the following link to confirm your attendance:'
               f'\n{_invitation_link(meeting_record.record_id, invitation_id)}'
               f'\n'
               f'\nMeeting details'
               f'\n    Name: {meeting_record.meeting.display_name}'
               f'\n    Start time: {meeting_record.meeting_start_time}'
               f'\n'
               f'\nAll potential participants'
               f'\n{", ".join([p.name for p in all_preference])}')
    send_mail(
        f'You are invited to meeting {meeting_record.meeting.display_name}',
        message,
        SCHOOL_REUNION_ADMIN_EMAIL,
        [preference.email],
        fail_silently=True
    )


# TODO: add online meeting link and content
def send_scheduled_meeting_details():
    pass
