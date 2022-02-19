"""Run test under manager.py directory with command:
    set DJANGO_SETTINGS_MODULE=school_reunion_website.settings; python3.9 manage.py test"""
import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from django.test import TestCase
from django.test import Client
from .models import Meeting, MeetingPreference, MeetingAttendance
import uuid
from django.core import mail
from .emails import SCHOOL_REUNION_ADMIN_EMAIL
from .utils import VERIFIED_EMAIL_STATUS
from .schedule_meeting import get_available_dates, get_feasible_meeting_dates_with_participants, MIN_ATTENDING_INTERVAL_TO_PREFERRED_INTERVAL
from typing import Optional, Dict
from django.db import transaction


TESTING_EMAIL_ADDRESS = 'school.reunion.testing@gmail.com'


def _create_preference_form(client, meeting_code, email=TESTING_EMAIL_ADDRESS,
                            override_post_data: Optional[Dict[str, str]] = None):
    session = client.session
    session['meeting_code'] = meeting_code
    session.save()
    post_data = {
        'name': f'name_{str(uuid.uuid4())}',
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
        'weighted_attendants': '[{"value":"assa:-1"},{"value":"lala:-10"},{"value":"haha:20"}]',
        'minimal_meeting_value': '1',
        'minimal_meeting_size': '2'}
    if override_post_data:
        post_data.update(override_post_data)

    return client.post(
        path='/meeting_preference/',
        data=post_data)


@transaction.atomic
def _set_all_preference_email_verified(meeting: Meeting):
    meeting_preferences = MeetingPreference.objects.filter(meeting=meeting.meeting_code)
    for preference in meeting_preferences:
        preference.email_verification_code = VERIFIED_EMAIL_STATUS
        preference.save()


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
        response = _create_preference_form(self.client, self.meeting_code, override_post_data={'name': 'fake_name'})

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

    def test_no_feasible_meeting_dates_because_minimal_meeting_size_set_too_high(self):
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_month"}]',
                                'minimal_meeting_size': '4',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy@gmail.com'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_year"}]',
                                'minimal_meeting_size': '2',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy2@gmail.com'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_year"}]',
                                'minimal_meeting_size': '3',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy3@gmail.com'})

        meeting = Meeting.objects.get(meeting_code=self.meeting_code)
        dates_with_participants = get_feasible_meeting_dates_with_participants(
            meeting, start=datetime.date(2021, 12, 1), until=datetime.date(2022, 1, 1))

        self.assertEqual(dates_with_participants, [])

    def test_has_feasible_meeting_date_because_minimal_meeting_size_set_is_right(self):
        meeting = Meeting.objects.get(meeting_code=self.meeting_code)
        meeting.code_available_usage = 10
        meeting.code_max_usage = 10
        meeting.save()
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_month"}]',
                                'minimal_meeting_size': '3',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy@gmail.com'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_year"}]',
                                'minimal_meeting_size': '2',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy2@gmail.com'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_year"}]',
                                'minimal_meeting_size': '3',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy3@gmail.com'})
        _set_all_preference_email_verified(meeting)
        dates_with_participants = get_feasible_meeting_dates_with_participants(
            meeting, start=datetime.date(2021, 12, 1), until=datetime.date(2022, 1, 1))

        self.assertEqual(len(dates_with_participants), 1)
        self.assertLess(dates_with_participants[0][0], datetime.date(2021, 12, 26))
        self.assertLess(datetime.date(2021, 12, 9), dates_with_participants[0][0])
        self.assertEqual(len(dates_with_participants[0][1]), 3)
        self.assertCountEqual(dates_with_participants[0][1],
                              MeetingPreference.objects.filter(meeting=self.meeting_code))

    def test_get_feasible_meeting_dates_with_meeting_frequency_considered(self):
        meeting = Meeting.objects.get(meeting_code=self.meeting_code)
        meeting.code_available_usage = 10
        meeting.code_max_usage = 10
        meeting.save()
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_month"}]',
                                'minimal_meeting_size': '3',
                                'prefer_to_attend_every_n_months': '6',
                                'email': 'dummy@gmail.com'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_month"}]',
                                'minimal_meeting_size': '2',
                                'prefer_to_attend_every_n_months': '6',
                                'email': 'dummy2@gmail.com'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_month"}]',
                                'minimal_meeting_size': '3',
                                'prefer_to_attend_every_n_months': '6',
                                'email': 'dummy3@gmail.com'})
        _set_all_preference_email_verified(meeting)

        # Non-deterministic behavior, run the test multiple times.
        for i in range(10):
            dates_with_participants = get_feasible_meeting_dates_with_participants(
                meeting, start=datetime.date(2021, 1, 1), until=datetime.date(2022, 1, 1))

            self.assertLess(len(dates_with_participants), 4)
            self.assertLess(1, len(dates_with_participants))
            for idx, (date, participants) in enumerate(dates_with_participants):
                self.assertEqual(len(participants), 3)
                self.assertLess(
                    datetime.timedelta(days=int(6*30*MIN_ATTENDING_INTERVAL_TO_PREFERRED_INTERVAL)-1),
                    abs(date - dates_with_participants[idx-1][0]))

    def test_get_feasible_meeting_dates_with_meeting_value_considered(self):
        # TODO, mock schedule_meeting.get_utc_now before 2025.1.1
        meeting = Meeting.objects.get(meeting_code=self.meeting_code)
        meeting.code_available_usage = 10
        meeting.code_max_usage = 10
        meeting.save()
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_month"}]',
                                'minimal_meeting_size': '2',
                                'minimal_meeting_value': '2',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy@gmail.com',
                                'name': 'A',
                                'weighted_attendants': '[{"value":"C:-10"}]'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_year"}]',
                                'minimal_meeting_size': '2',
                                'minimal_meeting_value': '2',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy2@gmail.com',
                                'name': 'B'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_year"}]',
                                'minimal_meeting_size': '2',
                                'minimal_meeting_value': '2',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy3@gmail.com',
                                'name': 'C'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_year"}]',
                                'minimal_meeting_size': '2',
                                'minimal_meeting_value': '2',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy4@gmail.com',
                                'name': 'D',
                                'weighted_attendants': '[{"value":"A:-10"}, {"value":"B:11"}]'})
        _set_all_preference_email_verified(meeting)
        # Set C attend the meeting recently.
        recent_participant: MeetingPreference = MeetingPreference.objects.filter(name='C')[0]
        attendance: MeetingAttendance = MeetingAttendance.objects.get(
            attendant_preference=recent_participant)
        attendance.latest_confirmation_time = datetime.datetime(2021, 1, 1)
        attendance.save()

        meeting = Meeting.objects.get(meeting_code=self.meeting_code)
        dates_with_participants = get_feasible_meeting_dates_with_participants(
            meeting, start=datetime.date(2021, 12, 1), until=datetime.date(2022, 1, 1))

        self.assertEqual(len(dates_with_participants), 1)
        self.assertEqual(len(dates_with_participants[0][1]), 3)
        self.assertCountEqual(['A', 'B', 'D'], [p.name for p in dates_with_participants[0][1]])

    def test_get_feasible_meeting_multiple_dates_with_meeting_value_considered(self):
        # TODO, mock schedule_meeting.get_utc_now before 2025.1.1
        meeting = Meeting.objects.get(meeting_code=self.meeting_code)
        meeting.code_available_usage = 10
        meeting.code_max_usage = 10
        meeting.save()
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_month"}]',
                                'minimal_meeting_size': '2',
                                'minimal_meeting_value': '2',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy@gmail.com',
                                'name': 'A',
                                'weighted_attendants': '[{"value":"C:-10"}]'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_year"}]',
                                'minimal_meeting_size': '2',
                                'minimal_meeting_value': '2',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy2@gmail.com',
                                'name': 'B'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_year"}]',
                                'minimal_meeting_size': '2',
                                'minimal_meeting_value': '2',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy3@gmail.com',
                                'name': 'C'})
        _create_preference_form(
            self.client, self.meeting_code,
            override_post_data={'selected_attending_dates': '[{"value":"12/10/2021 - 12/25/2021:repeat_each_year"}]',
                                'minimal_meeting_size': '2',
                                'minimal_meeting_value': '2',
                                'prefer_to_attend_every_n_months': '12',
                                'email': 'dummy4@gmail.com',
                                'name': 'D',
                                'weighted_attendants': '[{"value":"A:-10"},{"value":"B:10"}]'})
        _set_all_preference_email_verified(meeting)
        # Set C attend the meeting recently.
        recent_participant: MeetingPreference = MeetingPreference.objects.filter(name='C')[0]
        attendance: MeetingAttendance = MeetingAttendance.objects.get(
            attendant_preference=recent_participant)
        attendance.latest_confirmation_time = datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc)
        attendance.save()

        meeting = Meeting.objects.get(meeting_code=self.meeting_code)
        dates_with_participants = get_feasible_meeting_dates_with_participants(
            meeting, start=datetime.date(2021, 12, 1), until=datetime.date(2022, 1, 1))

        self.assertEqual(len(dates_with_participants), 2)
        self.assertEqual(len(dates_with_participants[0][1]), 2)
        self.assertEqual(len(dates_with_participants[1][1]), 2)
        self.assertCountEqual(['A', 'B'], [p.name for p in dates_with_participants[0][1]])
        self.assertCountEqual(['C', 'D'], [p.name for p in dates_with_participants[1][1]])

    def test_get_feasible_meeting_dates_with_meeting_record_considered(self):
        pass
