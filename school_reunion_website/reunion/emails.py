from django.core.mail import send_mail
from .models import MeetingPreference, MeetingRecord
from typing import List, Dict


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


def invitation_link(record_id, invitation_id):
    return f'<a href="https://127.0.0.1:8000/confirm_invitation/{record_id}/{invitation_id}>Click Me To Confirm</a>"'


def send_scheduled_meeting_notification(meeting_record: MeetingRecord,
                                        invitation_id: str,
                                        preference: MeetingPreference,
                                        all_preference: List[MeetingPreference]):
    if not invitation_id:
        return
    message = (f'Please click the following link to confirm your attendance:'
               f'\n{invitation_link(meeting_record.record_id, invitation_id)}'
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


def send_scheduled_meeting_details(preference: MeetingPreference, meeting_record: MeetingRecord):
    message = (f'Thanks for confirming your attendance! Here is the online meeting link:'
               f'\n{meeting_record.online_meeting_link}'
               f'\nMeeting details'
               f'\n    Name: {meeting_record.meeting.display_name}_{meeting_record.record_id}'
               f'\n    Start time: {meeting_record.meeting_start_time.isoformat()}'
               f'\nThe final participants list will be sent three weeks before the meeting.')
    send_mail(
        f'Online meeting link for {meeting_record.meeting.display_name}',
        message,
        SCHOOL_REUNION_ADMIN_EMAIL,
        [preference.email],
        fail_silently=True
    )


def send_final_meeting_reminder_emails(target_email, all_meeting_participants: List[MeetingPreference],
                                       meeting_record: MeetingRecord):
    message = (f'The meeting {meeting_record.meeting.display_name} is finalized.'
               f'\nOnline meeting link:'
               f'\n{meeting_record.online_meeting_link}'
               f'\nMeeting details:'
               f'\n    Name: {meeting_record.meeting.display_name}_{meeting_record.record_id}'
               f'\n    Start time: {meeting_record.meeting_start_time.isoformat(timespec="microseconds")}'
               f'\nPlease have a discussion with other participants if needed:'
               f'\n{", ".join([preference.name + ": " + preference.email for preference in all_meeting_participants])}')
    send_mail(
        f'Finalized information about meeting {meeting_record.meeting.display_name}_{meeting_record.record_id}',
        message,
        SCHOOL_REUNION_ADMIN_EMAIL,
        [target_email],
        fail_silently=True
    )
