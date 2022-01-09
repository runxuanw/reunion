"""Run test under manager.py directory with command:
    set DJANGO_SETTINGS_MODULE=school_reunion_website.settings; python3.9 manage.py test"""
import datetime

from django.test import TestCase
from django.test import Client
from .models import Meeting, MeetingPreference
import uuid
from django.core import mail
from .emails import SCHOOL_REUNION_ADMIN_EMAIL
from .utils import VERIFIED_EMAIL_STATUS
from .schedule_meeting import get_available_dates
from typing import Optional, Dict


TESTING_EMAIL_ADDRESS = 'school.reunion.testing@gmail.com'


def _create_preference_form(client, meeting_code, email=TESTING_EMAIL_ADDRESS,
                            override_post_data: Optional[Dict[str, str]] = None):
    session = client.session
    session['meeting_code'] = meeting_code
    session.save()
    post_data = {
        'name': 'fake_name',
        'email': email,
        'prefer_to_attend_every_n_months': '12',
        'selected_attending_dates':
            '[{"value":"12/16/2021 - 12/25/2021:no_repeat"},{"value":"United_States:Washington\'s Birthday"},'
            '{"value":"09/29/2021 - 10/02/2021:repeat_each_year"},'
            '{"value":"10/01/2021 - 10/02/2021:repeat_each_month"}]',
        'earliest_meeting_time': '00:12',
        'latest_meeting_time': '00:12',
        'online_attending_time_zone': '12',
        'acceptable_offline_meeting_cities': '12',
        'preferred_meeting_duration': '00:12',
        'acceptable_meeting_methods': ['online', 'offline'],
        'weighted_attendants': '12',
        'minimal_meeting_value': '1',
        'minimal_meeting_size': '2'}
    if override_post_data:
        post_data.update(override_post_data)

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
                         "12/16/2021 - 12/25/2021:no_repeat,United_States:Washington's Birthday,"
                         "09/29/2021 - 10/02/2021:repeat_each_year,"
                         "10/01/2021 - 10/02/2021:repeat_each_month")
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
                                override_post_data={'registered_attendant_code': preference.registered_attendant_code})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, SCHOOL_REUNION_ADMIN_EMAIL)
        self.assertEqual(mail.outbox[0].to, [TESTING_EMAIL_ADDRESS])

        _create_preference_form(self.client, self.meeting_code,
                                email=SCHOOL_REUNION_ADMIN_EMAIL,
                                override_post_data={'registered_attendant_code': preference.registered_attendant_code})
        updated_preference = MeetingPreference.objects.get(meeting_id=self.meeting_code)

        self.assertNotEqual(preference.email_verification_code, updated_preference.email_verification_code)
        self.assertNotEqual(updated_preference.email_verification_code, VERIFIED_EMAIL_STATUS)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].from_email, SCHOOL_REUNION_ADMIN_EMAIL)
        self.assertEqual(mail.outbox[1].to, [SCHOOL_REUNION_ADMIN_EMAIL])

    def test_get_available_dates_from_meeting_preference(self):
        _create_preference_form(self.client, self.meeting_code)
        preference = MeetingPreference.objects.get(meeting_id=self.meeting_code)
        available_dates = get_available_dates(
            preference,
            datetime.datetime(year=2000, month=1, day=1).date(),
            datetime.datetime(year=2001, month=1, day=1).date())

        self.assertCountEqual(
            available_dates, [datetime.date(2000, 11, 2), datetime.date(2000, 1, 2), datetime.date(2000, 10, 2),
                              datetime.date(2000, 10, 1), datetime.date(2000, 3, 2), datetime.date(2000, 2, 19),
                              datetime.date(2000, 4, 1), datetime.date(2000, 1, 1), datetime.date(2000, 6, 1),
                              datetime.date(2000, 8, 1), datetime.date(2000, 12, 2), datetime.date(2000, 4, 2),
                              datetime.date(2001, 1, 1), datetime.date(2000, 8, 2), datetime.date(2000, 2, 1),
                              datetime.date(2000, 6, 2), datetime.date(2000, 12, 1), datetime.date(2000, 9, 30),
                              datetime.date(2000, 9, 1), datetime.date(2000, 9, 2), datetime.date(2000, 3, 1),
                              datetime.date(2000, 5, 1), datetime.date(2000, 9, 29), datetime.date(2000, 5, 2),
                              datetime.date(2000, 2, 2), datetime.date(2000, 2, 20), datetime.date(2000, 7, 1),
                              datetime.date(2000, 2, 21), datetime.date(2000, 7, 2), datetime.date(2000, 11, 1)])

    def test_get_all_dates_from_meeting_preference(self):
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_week"}]'})
        preference = MeetingPreference.objects.get(meeting_id=self.meeting_code)
        available_dates = get_available_dates(
            preference,
            datetime.datetime(year=2000, month=5, day=1).date(),
            datetime.datetime(year=2000, month=5, day=15).date())

        self.assertCountEqual(available_dates,
                              [datetime.date(2000, 5, 1), datetime.date(2000, 5, 2), datetime.date(2000, 5, 3),
                               datetime.date(2000, 5, 4), datetime.date(2000, 5, 5), datetime.date(2000, 5, 6),
                               datetime.date(2000, 5, 7), datetime.date(2000, 5, 8), datetime.date(2000, 5, 9),
                               datetime.date(2000, 5, 10), datetime.date(2000, 5, 11), datetime.date(2000, 5, 12),
                               datetime.date(2000, 5, 13), datetime.date(2000, 5, 14), datetime.date(2000, 5, 15)])

    def test_scheduling_meeting_after_conditions_are_met(self):
        pass
