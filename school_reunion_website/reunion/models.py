import datetime
from pytz import UTC
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
import uuid


DEFAULT_INITIAL_DATE = datetime.datetime(year=1970, month=1, day=1, tzinfo=UTC)


# TODO: rename, e.g. meeting group.
class Meeting(models.Model):
    meeting_code = models.UUIDField(primary_key=True)
    display_name = models.CharField(max_length=100)
    code_max_usage = models.IntegerField(validators=[MaxValueValidator(50),
                                                     MinValueValidator(2)])
    code_available_usage = models.IntegerField(default=-1)
    contact_email = models.EmailField()
    last_check_time = models.DateTimeField(default=DEFAULT_INITIAL_DATE)

    def __str__(self):
        return f'meeting {self.meeting_code}'


class MeetingRecord(models.Model):
    record_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    meeting = models.ForeignKey(Meeting, on_delete=models.PROTECT)
    meeting_status = models.TextField()

    meeting_method = models.TextField()
    offline_meeting_locations = models.TextField()
    online_meeting_link = models.TextField()
    meeting_start_time = models.DateTimeField()
    meeting_end_time = models.DateTimeField()
    # {UUID: PENDING|CONFIRM|DENY}
    attendant_code_to_status = models.TextField()
    # {invitation code: UUID}
    invitation_code_to_attendant_code = models.TextField()


class MeetingPreference(models.Model):
    registered_attendant_code = models.UUIDField(primary_key=True)
    meeting = models.ForeignKey(Meeting, on_delete=models.PROTECT)

    name = models.CharField(max_length=100)
    email = models.EmailField()
    email_verification_code = models.TextField(db_index=True, unique=False)
    # Time and location:
    prefer_to_attend_every_n_months = models.IntegerField()
    selected_attending_dates = models.TextField(blank=True)
    # TODO/p0, add largest_meeting_regardless_dates option.
    #  The logic change would be adding a set of participants, people in the set would always be counted once
    #  in one date, after that date is picked remove selected participants from the set,
    #  if absolute # of people in dates are the same, then pick the date
    #  with originally most selected (further tier would be random selected).
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
    minimal_meeting_value = models.IntegerField(default=2)
    # In case minimal_meeting_value doesn't cover edge cases.
    minimal_meeting_size = models.IntegerField(default=2)

    def __str__(self):
        return f'attendant code {self.registered_attendant_code}, meeting preference for {self.meeting}'

    class Meta:
        unique_together = (("meeting", "name"), ("meeting", "email"),)

    def save(self, **kwargs):
        if not self.earliest_meeting_time:
            self.earliest_meeting_time = '10:00'
        if not self.latest_meeting_time:
            self.latest_meeting_time = '21:00'
        if not self.preferred_meeting_duration:
            self.preferred_meeting_duration = '4:00'
        super().save(kwargs)


class MeetingAttendance(models.Model):
    attendant_preference = models.ForeignKey(MeetingPreference, on_delete=models.PROTECT)
    latest_invitation_time = models.DateTimeField(default=DEFAULT_INITIAL_DATE)
    latest_confirmation_time = models.DateTimeField(default=DEFAULT_INITIAL_DATE)
