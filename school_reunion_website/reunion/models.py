from django.db import models


class Meeting(models.Model):
    meeting_code = models.UUIDField(primary_key=True)
    display_name = models.CharField(max_length=100)
    code_max_usage = models.IntegerField()
    code_available_usage = models.IntegerField(default=-1)
    contact_email = models.EmailField()

    def __str__(self):
        return f'meeting {self.meeting_code}'


class MeetingPreference(models.Model):
    registered_attendant_code = models.UUIDField(primary_key=True)
    meeting = models.ForeignKey(Meeting, on_delete=models.PROTECT)

    name = models.CharField(max_length=30)
    email = models.EmailField()
    email_verification_code = models.TextField(db_index=True, unique=True)
    # Time and location:
    preferred_attending_frequency_in_months = models.IntegerField()
    repeated_available_holidays = models.TextField(blank=True)
    repeated_available_dates_each_year = models.TextField(blank=True)
    one_time_available_dates = models.TextField(blank=True)
    acceptable_meeting_time_range_in_day = models.CharField(max_length=50, blank=True)
    # For both online and offline.
    expected_attending_time_zones = models.CharField(max_length=300, blank=True)
    acceptable_offline_meeting_locations = models.TextField(blank=True)
    preferred_meeting_duration_in_hour = models.DurationField(blank=True)

    acceptable_meeting_methods = models.CharField(max_length=30, blank=True)
    preferred_meeting_activities = models.CharField(max_length=300, blank=True)

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