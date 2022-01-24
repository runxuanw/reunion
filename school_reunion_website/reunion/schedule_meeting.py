import datetime

from .models import MeetingPreference, Meeting, MeetingRecord, MeetingAttendance
from .utils import get_country_to_holidays_map, REPEAT_OPTIONS_SET, NO_REPEAT, REPEAT_EACH_YEAR, REPEAT_EACH_WEEK, REPEAT_EACH_MONTH
import collections
from typing import List, Dict, Optional, Tuple, Union

ALL_DATES = 'all_dates'
# Consider to invite the candidate at least after 7 months if they prefer to attend every 10 months.
MIN_ATTENDING_INTERVAL_TO_PREFERRED_INTERVAL = 0.7

# 1. {date: available people count with relax of 1 week} for 1 year from current time. (done)
# 2. iteratively generate meeting from most count date to least count date
#   2.0 filtering people
#   2.1 handle weighted people
#   2.2 when generate a meeting, weight more for unparticipated people in past meetings
#   2.3 consider time zone
# 3. send invitation for those who doesn't fit in the strict date rule (2 weeks)
# 4. send invitation if the meeting is possible, before 1 month, have 2 weeks to confirm

# 5. create email thread for all people in meeting (before two weeks)
# 6. create online link for meeting


def _get_near_weekend_dates(date: datetime.date):
    # Monday
    if date.weekday() == 0:
        return [date - datetime.timedelta(days=1), date - datetime.timedelta(days=2)]
    if date.weekday() == 4:
        return [date + datetime.timedelta(days=1), date + datetime.timedelta(days=2)]
    if date.weekday() == 5:
        return [date + datetime.timedelta(days=1)]
    if date.weekday() == 6:
        return [date - datetime.timedelta(days=1)]
    return []


def _transfer_holiday_to_dates(holiday_entry, start: datetime.date, until: datetime.date):
    """Gets holiday dates with its adjacent weekend."""
    country, holiday = holiday_entry.split(':')
    country = country.replace('_', ' ')
    check_years = tuple(range(start.year, until.year+1))
    country_to_holidays_map = get_country_to_holidays_map(check_years)
    dates = []
    holidays_map = country_to_holidays_map.get(country)
    if not holidays_map:
        return dates
    if holiday.startswith('Select All '):
        for holiday, holiday_dates in holidays_map.items():
            dates.extend(holiday_dates)
    else:
        dates = holidays_map.get(holiday, [])

    final_dates = set()
    for date in dates:
        final_dates.add(date)
        for weekend_dates in _get_near_weekend_dates(date):
            final_dates.add(weekend_dates)
    return [date for date in list(final_dates) if start <= date <= until]


def _transfer_custom_input_to_dates(custom_entry, start: datetime.date, until: datetime.date):
    date_range, repeated_option = custom_entry.split(':')
    if repeated_option not in REPEAT_OPTIONS_SET:
        return []

    input_start_date, input_end_date = date_range.split(' - ')
    input_start_date = datetime.datetime.strptime(input_start_date, '%m/%d/%Y').date()
    input_end_date = datetime.datetime.strptime(input_end_date, '%m/%d/%Y').date()
    diff_date = input_end_date - input_start_date

    dates = []
    repeated_rule_set = set()

    current_input_date = input_start_date
    # Note if one year with 365 days is selected, Feb 29 will not be included.
    if repeated_option == REPEAT_EACH_YEAR:
        if diff_date > datetime.timedelta(days=365):
            return [ALL_DATES]
        while current_input_date <= input_end_date:
            repeated_rule_set.add(f'{current_input_date.month}-{current_input_date.day}')
            current_input_date += datetime.timedelta(days=1)
    # Note if whole February is selected, day 30 and 31 will not be included.
    elif repeated_option == REPEAT_EACH_MONTH:
        if diff_date > datetime.timedelta(days=30):
            return [ALL_DATES]
        while current_input_date <= input_end_date:
            repeated_rule_set.add(current_input_date.day)
            current_input_date += datetime.timedelta(days=1)
    elif repeated_option == REPEAT_EACH_WEEK:
        if diff_date > datetime.timedelta(days=6):
            return [ALL_DATES]
        while current_input_date <= input_end_date:
            repeated_rule_set.add(current_input_date.weekday())
            current_input_date += datetime.timedelta(days=1)

    current_date = start
    while current_date <= until:
        if repeated_option == REPEAT_EACH_YEAR:
            if f'{current_date.month}-{current_date.day}' in repeated_rule_set:
                dates.append(current_date)
        elif repeated_option == REPEAT_EACH_MONTH:
            if current_date.day in repeated_rule_set:
                dates.append(current_date)
        elif repeated_option == REPEAT_EACH_WEEK:
            if current_date.weekday() in repeated_rule_set:
                dates.append(current_date)
        # No repeat.
        elif input_start_date < current_date < input_end_date:
            dates.append(current_date)
        current_date += datetime.timedelta(days=1)
    return dates


def _get_all_dates(start: datetime.date, until: datetime.date):
    dates = []
    current_date = start
    while current_date <= until:
        dates.append(current_date)
        current_date += datetime.timedelta(days=1)
    return dates


def get_available_dates(preference: MeetingPreference, start: datetime.date, until: datetime.date):
    attending_rules = preference.selected_attending_dates.split(',')
    available_dates = set()
    for attending_rule in attending_rules:
        if len(attending_rule.split(':')) != 2:
            continue
        tmp_dates = (_transfer_holiday_to_dates(attending_rule, start, until)
                     or _transfer_custom_input_to_dates(attending_rule, start, until))
        if ALL_DATES in tmp_dates:
            return _get_all_dates(start, until)
        for tmp_date in tmp_dates:
            available_dates.add(tmp_date)
    return list(available_dates)


def _pick_next_date_to_participate(dates_with_participants_preference: Dict[datetime.date, List[MeetingPreference]]) \
        -> Tuple[datetime.date, List[MeetingPreference]]:
    # Gets the date with most people want to attend.
    date_with_most_participants: Optional[Tuple[datetime.date, List[MeetingPreference]]] = None
    for date, preferences in dates_with_participants_preference.items():
        if not date_with_most_participants or len(preferences) > len(date_with_most_participants[1]):
            date_with_most_participants = (date, preferences)
    return date_with_most_participants


def _update_other_dates_after_picking_meeting_date(
        picked_date, participants_preference_in_picked_date, date_to_potential_participants):
    """Excludes people in the picked date from attending meeting dates in date_to_potential_participants."""
    participants_code_to_unavailable_date_range = {}
    for participant_preference in participants_preference_in_picked_date:
        participants_code_to_unavailable_date_range[participant_preference.registered_attendant_code] = (
            _get_unavailable_date_range(picked_date, participant_preference))

    for date in date_to_potential_participants.keys():
        updated_preferences = []
        for meeting_preference in date_to_potential_participants[date]:
            unavailable_date_range = participants_code_to_unavailable_date_range.get(
                meeting_preference.registered_attendant_code)
            if not unavailable_date_range:
                updated_preferences.append(meeting_preference)
            elif not unavailable_date_range[0] < date < unavailable_date_range[1]:
                updated_preferences.append(meeting_preference)
        date_to_potential_participants[date] = updated_preferences
    _sanitize_empty_dates(date_to_potential_participants)


def _sanitize_dates_with_meeting_size_preference(date_to_potential_participants):
    """Updates date_to_potential_participants with minimal meeting size requirement."""
    for date in date_to_potential_participants.keys():
        participant_codes_to_minimal_meeting_size = []
        for meeting_preference in date_to_potential_participants[date]:
            participant_codes_to_minimal_meeting_size.append(
                [meeting_preference.registered_attendant_code, meeting_preference.minimal_meeting_size])
        # Iterate reversely because it's could be a chain reaction,
        # e.g. date with 10 people selected could end up with no one want to participate.
        participant_codes_to_minimal_meeting_size.sort(key=lambda x: x[1], reverse=True)

        current_meeting_size = len(participant_codes_to_minimal_meeting_size)
        refuse_to_participate = set()
        for code, minimal_meeting_size in participant_codes_to_minimal_meeting_size:
            if minimal_meeting_size > current_meeting_size:
                current_meeting_size -= 1
                refuse_to_participate.add(code)
        updated_preferences = []
        for meeting_preference in date_to_potential_participants[date]:
            if meeting_preference.registered_attendant_code not in refuse_to_participate:
                updated_preferences.append(meeting_preference)
        date_to_potential_participants[date] = updated_preferences
    _sanitize_empty_dates(date_to_potential_participants)


def _sanitize_empty_dates(date_to_potential_participants):
    """If one date has no participants, it should be removed from date_to_potential_participants."""
    empty_dates = []
    for date in date_to_potential_participants.keys():
        if not date_to_potential_participants[date]:
            empty_dates.append(date)
    for date in empty_dates:
        date_to_potential_participants.pop(date)


def _get_unavailable_date_range(
        last_meeting_date: Union[datetime.datetime, datetime.date],
        meeting_preference) -> Tuple[datetime.date, datetime.date]:
    """Given last meeting date and the meeting preference of a person,
        show the range of dates that should not be considered for this person."""
    if isinstance(last_meeting_date, datetime.datetime):
        last_meeting_date = last_meeting_date.date()

    minimal_attending_interval = datetime.timedelta(
        days=meeting_preference.prefer_to_attend_every_n_months*30*MIN_ATTENDING_INTERVAL_TO_PREFERRED_INTERVAL)
    unavailability_start_date = last_meeting_date - minimal_attending_interval
    unavailability_end_date = last_meeting_date + minimal_attending_interval
    return unavailability_start_date, unavailability_end_date


def get_feasible_meeting_dates_with_participants(
        meeting: Meeting, start: datetime.date, until: datetime.date) \
        -> List[Tuple[datetime.date, List[MeetingPreference]]]:
    meeting_preferences = MeetingPreference.objects.filter(meeting=meeting.meeting_code)
    date_to_potential_participants = collections.defaultdict(list)
    # Iterate through all preference to filter out recently participated ones.
    for meeting_preference in meeting_preferences:
        attendance = MeetingAttendance.objects.get(
            registered_attendant_code=meeting_preference.registered_attendant_code)
        available_dates = get_available_dates(meeting_preference, start=start, until=until)
        # Also consider the notification sent but haven't received a reply: last_invitation_time.
        _, earliest_acceptable_date = _get_unavailable_date_range(
            max(attendance.last_confirmation_time, attendance.last_invitation_time), meeting_preference)
        for available_date in available_dates:
            if earliest_acceptable_date <= available_date:
                date_to_potential_participants[available_date].append(meeting_preference)

    # Now consider other rules, e.g. everyone will get positive value from the meeting and
    # the meeting meets the minimal size for participants.
    # TODO: consider negative meeting value rule.
    _sanitize_dates_with_meeting_size_preference(date_to_potential_participants)

    # Use greedy algorithm to arrange meetings. With the date most people can participate being considered first.
    dates_with_participants_preference: List[Tuple[datetime.date, List[MeetingPreference]]] = []
    while date_to_potential_participants:
        next_meeting_date, participants_preference = _pick_next_date_to_participate(date_to_potential_participants)
        date_to_potential_participants.pop(next_meeting_date)
        dates_with_participants_preference.append((next_meeting_date, participants_preference))
        _update_other_dates_after_picking_meeting_date(
            next_meeting_date, participants_preference, date_to_potential_participants)
        _sanitize_dates_with_meeting_size_preference(date_to_potential_participants)

    return dates_with_participants_preference


def schedule_meeting(meeting: Meeting):
    utcnow = datetime.datetime.utcnow()
    dates_with_participants_preference = get_feasible_meeting_dates_with_participants(
        meeting,
        start=utcnow.date(),
        until=(utcnow+datetime.timedelta(days=365)).date())
    for date, participants_preference in dates_with_participants_preference:
        # Send notification only when at least two months are available and
        # don't send notification if it is more than three months.
        if (utcnow+datetime.timedelta(days=60)).date() <= date <= (utcnow+datetime.timedelta(days=90)).date():
            # Create new meeting record with data.
            pass
