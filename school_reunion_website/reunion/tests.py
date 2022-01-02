"""Run test under manager.py directory with command:
    set DJANGO_SETTINGS_MODULE=school_reunion_website.settings; python3.9 manage.py test"""
from django.test import TestCase
from django.test import Client
from .models import Meeting, MeetingPreference
import uuid
from django.core import mail
from .emails import SCHOOL_REUNION_ADMIN_EMAIL
from .utils import VERIFIED_EMAIL_STATUS


TESTING_EMAIL_ADDRESS = 'school.reunion.testing@gmail.com'


def _create_preference_form(client, meeting_code, email=TESTING_EMAIL_ADDRESS, registered_attendant_code=None):
    session = client.session
    session['meeting_code'] = meeting_code
    session.save()
    post_data = {
        'name': 'fake_name',
        'email': email,
        'prefer_to_attend_every_n_months': '12',
        'selected_attending_dates':
            '[{"value":"12/16/2021 - 12/25/2021:no_repeat"},{"value":"United_States:Washington\'s Birthday 2021-02-15"}]',
        'earliest_meeting_time': '00:12',
        'latest_meeting_time': '00:12',
        'online_attending_time_zone': '12',
        'acceptable_offline_meeting_cities': '12',
        'preferred_meeting_duration': '00:12',
        'acceptable_meeting_methods': ['online', 'offline'],
        'weighted_attendants': '12',
        'minimal_meeting_value': '1',
        'minimal_meeting_size': '2'}
    if registered_attendant_code:
        post_data['registered_attendant_code'] = registered_attendant_code

    return client.post(
        path='/meeting_preference/',
        data=post_data)


class MeetingPreferenceViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.meeting_code = str(uuid.uuid4())
        Meeting.objects.create(meeting_code=self.meeting_code, display_name='test meeting',
                               code_max_usage=2, code_available_usage=2, contact_email='test@test.com')

    def test_add_new_record_and_verify_email_after_new_meeting_preference_form_submitted(self):
        """
        meeting_preference() with proper post request will have preference recorded.
        """
        self.assertEqual(Meeting.objects.get(meeting_code=self.meeting_code).display_name, 'test meeting')
        response = _create_preference_form(self.client, self.meeting_code)

        preference = MeetingPreference.objects.get(meeting_id=self.meeting_code)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Meeting.objects.get(meeting_code=self.meeting_code).code_available_usage, 1)
        self.assertEqual(preference.name, 'fake_name')
        self.assertEqual(preference.selected_attending_dates,
                         "12/16/2021 - 12/25/2021:no_repeat,United_States:Washington's Birthday 2021-02-15")
        self.assertEqual(len(preference.email_verification_code), 128)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, SCHOOL_REUNION_ADMIN_EMAIL)
        self.assertEqual(mail.outbox[0].to, [TESTING_EMAIL_ADDRESS])
        self.assertTrue((preference.email_verification_code in mail.outbox[0].body))

    def test_email_verification_status_change_to_pass_after_click_the_generated_link(self):
        _create_preference_form(self.client, self.meeting_code)
        preference = MeetingPreference.objects.get(meeting_id=self.meeting_code)
        response = self.client.get(path=f'/email_verification/{preference.email_verification_code}')

        preference = MeetingPreference.objects.get(meeting_id=self.meeting_code)
        self.assertEqual(preference.email_verification_code, VERIFIED_EMAIL_STATUS)
        self.assertEqual(response.status_code, 200)

    def test_resend_verification_email_only_after_email_is_changed(self):
        _create_preference_form(self.client, self.meeting_code)
        preference = MeetingPreference.objects.get(meeting_id=self.meeting_code)
        # Unchanged email address.
        _create_preference_form(self.client, self.meeting_code,
                                registered_attendant_code=preference.registered_attendant_code)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, SCHOOL_REUNION_ADMIN_EMAIL)
        self.assertEqual(mail.outbox[0].to, [TESTING_EMAIL_ADDRESS])

        _create_preference_form(self.client, self.meeting_code,
                                email=SCHOOL_REUNION_ADMIN_EMAIL,
                                registered_attendant_code=preference.registered_attendant_code)
        updated_preference = MeetingPreference.objects.get(meeting_id=self.meeting_code)

        self.assertNotEqual(preference.email_verification_code, updated_preference.email_verification_code)
        self.assertNotEqual(updated_preference.email_verification_code, VERIFIED_EMAIL_STATUS)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].from_email, SCHOOL_REUNION_ADMIN_EMAIL)
        self.assertEqual(mail.outbox[1].to, [SCHOOL_REUNION_ADMIN_EMAIL])

    def test_scheduling_meeting_after_conditions_are_met(self):
        pass
