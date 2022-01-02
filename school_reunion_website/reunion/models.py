import datetime

from django.db import models


class Meeting(models.Model):
    meeting_code = models.UUIDField(primary_key=True)
    display_name = models.CharField(max_length=100)
    code_max_usage = models.IntegerField()
    code_available_usage = models.IntegerField(default=-1)
    contact_email = models.EmailField()
    last_check_time = models.DateTimeField(default=datetime.datetime(year=1970, month=1, day=1))

    def __str__(self):
        return f'meeting {self.meeting_code}'


class MeetingRecord(models.Model):
    meeting_record = models.UUIDField(primary_key=True)
    meeting = models.ForeignKey(Meeting, on_delete=models.PROTECT)

    meeting_method = models.TextField()
    offline_meeting_locations = models.TextField()
    online_meeting_link = models.TextField()
    meeting_start_time = models.DateTimeField()
    meeting_end_time = models.DateTimeField()
    confirmed_attendant_codes = models.TextField()
    pending_attendant_codes = models.TextField()
    denied_attendant_codes = models.TextField()


class MeetingPreference(models.Model):
    registered_attendant_code = models.UUIDField(primary_key=True)
    meeting = models.ForeignKey(Meeting, on_delete=models.PROTECT)

    name = models.CharField(max_length=30)
    email = models.EmailField()
    email_verification_code = models.TextField(db_index=True, unique=False)
    # Time and location:
    prefer_to_attend_every_n_months = models.IntegerField()
    selected_attending_dates = models.TextField(blank=True)
    earliest_meeting_time = models.TimeField(max_length=50, blank=True)
    latest_meeting_time = models.TimeField(max_length=50, blank=True)
    # For both online and offline.
    online_attending_time_zone = models.CharField(max_length=300, blank=True)
    acceptable_offline_meeting_cities = models.TextField(blank=True)
    preferred_meeting_duration = models.TimeField(blank=True)

    acceptable_meeting_methods = models.CharField(max_length=30, blank=True)

    # Other attendants:
    # If one joins the meeting, the finalized meeting value will be positive for that person.
    # The conflict between people will be handled in meeting scheduler.
    # Default value is 1 for everyone.
    weighted_attendants = models.TextField(blank=True)
    # Minimal meeting value for one to be considered joining.
    minimal_meeting_value = models.IntegerField(default=1)
    # In case minimal_meeting_value doesn't cover edge cases.
    minimal_meeting_size = models.IntegerField(default=2)

    def __str__(self):
        return f'meeting preference for {self.meeting}'

    class Meta:
        unique_together = (("meeting", "name"), ("meeting", "email"),)
