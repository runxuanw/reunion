import collections

from django.db import transaction
from django.http import Http404
import dataclasses
from django.db import models
from typing import Optional
import holidays
import pycountry
import datetime


DEFAULT_HOLIDAY_YEARS = (datetime.datetime.utcnow().year, datetime.datetime.utcnow().year+1)
NEAR_WEEKEND_DAYS = {0, 4, 5, 6}
VERIFIED_EMAIL_STATUS = 'Verified'
COUNTRY_TO_HOLIDAY_MAP_BY_YEAR = {}
REPEAT_EACH_YEAR = 'repeat_each_year'
REPEAT_EACH_MONTH = 'repeat_each_month'
REPEAT_EACH_WEEK = 'repeat_each_week'
NO_REPEAT = 'no_repeat'
REPEAT_OPTIONS = [(REPEAT_EACH_YEAR, 'repeat each year'),
                  (REPEAT_EACH_MONTH, 'repeat each month'),
                  (REPEAT_EACH_WEEK, 'repeat each week'),
                  (NO_REPEAT, 'no repeat')]
REPEAT_OPTIONS_SET = set([option[0] for option in REPEAT_OPTIONS])


@dataclasses.dataclass
class ValidForm:
    name: str
    model: Optional[models.Model]


# Returns the name of the form that matches the post_request.
def valid_request_from_forms(post_request, candidate_forms, raise_if_not_found=True, get_model=False):
    for candidate_form in candidate_forms:
        form_instance = candidate_form(post_request)
        if form_instance.is_valid():
            model = None
            if get_model:
                try:
                    # Not all forms can be saved.
                    model = form_instance.save(commit=False)
                except:
                    pass
            return ValidForm(name=form_instance.__class__.__name__, model=model)
        else:
            print(f'\n====debug invalid form {candidate_form.__name__}====')
            print(form_instance.errors)
            print(form_instance.non_field_errors)
    if raise_if_not_found:
        raise Http404('Not valid form entry.')
    return ''


@transaction.atomic
def record_new_meeting_preference(meeting, preference, meeting_attendance):
    meeting.save()
    preference.save()
    meeting_attendance.save()


def get_country_to_holidays_map(years=DEFAULT_HOLIDAY_YEARS):
    """Returns {country name: {holiday name: [holiday dates]}}."""
    global COUNTRY_TO_HOLIDAY_MAP_BY_YEAR
    if not COUNTRY_TO_HOLIDAY_MAP_BY_YEAR.get(years):
        country_code_map = {}
        for country in pycountry.countries:
            country_code_map[country.alpha_2] = country.name
            country_code_map[country.alpha_3] = country.name

        country_to_holidays_map = {}
        countries = holidays.list_supported_countries()
        for country in countries:
            country_holidays = holidays.CountryHoliday(
                country=country, years=years)

            reformatted_holidays = collections.defaultdict(list)
            for date, holiday_name in country_holidays.items():
                reformatted_holidays[holiday_name.replace(",", " ")].append(date)
            country_name = country
            if country.isupper():
                country_name = country_code_map.get(country)
            # Only add human readable country name.
            if country_name and (country_name[1:].islower() or (' ' in country_name)):
                country_to_holidays_map[country_name] = reformatted_holidays
        COUNTRY_TO_HOLIDAY_MAP_BY_YEAR[years] = country_to_holidays_map
    return COUNTRY_TO_HOLIDAY_MAP_BY_YEAR[years]


get_country_to_holidays_map()
