from django.db import transaction
from django.http import Http404
import dataclasses
from django.db import models
from typing import Optional
import holidays
import pycountry
import datetime


VERIFIED_EMAIL_STATUS = 'Verified'
COUNTRY_TO_HOLIDAY_MAP = {}
REPEAT_OPTIONS = [('repeat_each_year', 'repeat each year'),
                  ('repeat_each_month', 'repeat each month'),
                  ('repeat_each_week', 'repeat each week'),
                  ('no_repeat', 'no repeat')]


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
def record_new_meeting_preference(meeting, preference):
    meeting.save()
    preference.save()


def get_country_to_holidays_map():
    """Returns {country name: list of holidays}."""
    global COUNTRY_TO_HOLIDAY_MAP
    if not COUNTRY_TO_HOLIDAY_MAP:
        country_code_map = {}
        for country in pycountry.countries:
            country_code_map[country.alpha_2] = country.name
            country_code_map[country.alpha_3] = country.name

        country_to_holidays_map = {}
        holiday_countries = holidays.list_supported_countries()
        for country in holiday_countries:
            country_holidays = holidays.CountryHoliday(
                country=country, years=datetime.datetime.utcnow().year)
            country_name = country
            if country.isupper():
                country_name = country_code_map.get(country)
            if country_name and (country_name[1:].islower() or (' ' in country_name)):
                country_to_holidays_map[country_name] = country_holidays
        COUNTRY_TO_HOLIDAY_MAP = country_to_holidays_map
    return COUNTRY_TO_HOLIDAY_MAP
