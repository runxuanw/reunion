"""Run test under manager.py directory with command:
    set DJANGO_SETTINGS_MODULE=school_reunion_website.settings; python3.9 manage.py test"""
from django.test import TestCase
from django.test import Client
from .models import Meeting, MeetingPreference
import uuid


class MeetingPreferenceViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.meeting_code = str(uuid.uuid4())
        Meeting.objects.create(meeting_code=self.meeting_code, display_name='test meeting',
                               code_max_usage=2, code_available_usage=2, contact_email='test@test.com')

    def test_add_new_record_after_new_meeting_preference_form_submitted(self):
        """
        meeting_preference() with proper post request will have preference recorded.
        """
        self.assertEqual(Meeting.objects.get(meeting_code=self.meeting_code).display_name, 'test meeting')
        session = self.client.session
        session['meeting_code'] = self.meeting_code
        session.save()
        response = self.client.post(
            path='/meeting_preference/',
            data={
                'name': 'fake_name',
                'email': '123@gmail.com',
                'preferred_attending_frequency_in_months': '12',
                'repeated_available_holidays': '12',
                'repeated_available_dates_each_year': '12',
                'one_time_available_dates': '12',
                'acceptable_meeting_time_range_in_day': '12',
                'expected_attending_time_zones': '12',
                'acceptable_offline_meeting_locations': '12',
                'preferred_meeting_duration_in_hour': '12',
                'acceptable_meeting_methods': '12',
                'preferred_meeting_activities': '12',
                'weighted_attendants': '12',
                'minimal_meeting_value': '1',
                'minimal_meeting_size': '2'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Meeting.objects.get(meeting_code=self.meeting_code).code_available_usage, 1)
        self.assertEqual(MeetingPreference.objects.get(meeting_id=self.meeting_code).name, 'fake_name')
