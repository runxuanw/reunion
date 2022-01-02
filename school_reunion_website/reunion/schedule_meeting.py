from .models import MeetingPreference, Meeting, MeetingRecord


def schedule_meeting(meeting: Meeting):
    meeting_records = MeetingRecord.objects.get(meeting=meeting.meeting_code)

