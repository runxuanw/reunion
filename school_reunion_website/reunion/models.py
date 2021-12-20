from django.db import models


# class Question(models.Model):
#     question_text = models.CharField(max_length=200)
#     pub_date = models.DateTimeField('date published')
#
#
# class Choice(models.Model):
#     question = models.ForeignKey(Question, on_delete=models.CASCADE)
#     choice_text = models.CharField(max_length=200)
#     votes = models.IntegerField(default=0)


class Meeting(models.Model):
    meeting_code = models.UUIDField(primary_key=True)
    display_name = models.CharField(max_length=100)
    code_max_usage = models.IntegerField()
    contact_email = models.EmailField()

    def __str__(self):
        return f'meeting {self.meeting_code}'


class MeetingPreference(models.Model):
    name = models.CharField(max_length=30)
    email = models.EmailField()
    meeting = models.ForeignKey(Meeting, on_delete=models.PROTECT)
    # Time and location:
    preferred_attending_frequency_in_months = models.IntegerField(null=True)
    repeated_available_holidays = models.TextField(null=True)
    repeated_available_dates_each_year = models.TextField(null=True)
    one_time_available_dates = models.TextField(null=True)
    acceptable_meeting_time_range_in_day = models.CharField(max_length=50, null=True)
    # For both online and offline.
    expected_attending_time_zones = models.CharField(max_length=300, null=True)
    acceptable_offline_meeting_locations = models.TextField(null=True)
    preferred_meeting_duration_in_hour = models.DurationField(null=True)

    acceptable_meeting_methods = models.CharField(max_length=30, null=True)
    preferred_meeting_activities = models.CharField(max_length=300, null=True)

    # Other attendants:
    # If one joins the meeting, the finalized meeting value will be positive for that person.
    # The conflict between people will be handled in meeting scheduler.
    # Default value is 1 for everyone.
    weighted_attendants = models.TextField(null=True)
    # Minimal meeting value for one to be considered joining.
    minimal_meeting_value = models.IntegerField(default=1)
    # In case minimal_meeting_value doesn't cover edge cases.
    minimal_meeting_size = models.IntegerField(default=2)

    def __str__(self):
        return f'meeting preference for {self.meeting}'

    class Meta:
        unique_together = (("meeting", "name"),)
