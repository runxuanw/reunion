import datetime

from .models import MeetingPreference, Meeting, MeetingRecord, MeetingAttendance
from .utils import get_country_to_holidays_map, REPEAT_OPTIONS_SET, NO_REPEAT, REPEAT_EACH_YEAR, REPEAT_EACH_WEEK, REPEAT_EACH_MONTH
import collections

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


def schedule_meeting(meeting: Meeting):
    meeting_records = MeetingRecord.objects.get(meeting=meeting.meeting_code)
    meeting_preferences = MeetingPreference.objects.get(meeting=meeting.meeting_code)
    date_to_potential_participants = collections.defaultdict(list)
    for meeting_preference in meeting_preferences:
        attendance = (
                MeetingAttendance.objects.get(registered_attendant_code=meeting_preference.registered_attendant_code)
                or MeetingAttendance(registered_attendant_code=meeting_preference.registered_attendant_code))
        available_dates = get_available_dates(
            meeting_preference,
            start=datetime.datetime.utcnow().date(),
            until=(datetime.datetime.utcnow()+datetime.timedelta(days=365)).date())
        minimal_attending_interval = datetime.timedelta(
            days=meeting_preference.prefer_to_attend_every_n_months*30*MIN_ATTENDING_INTERVAL_TO_PREFERRED_INTERVAL)
        earliest_acceptable_date = (attendance.last_confirmation_time + minimal_attending_interval).date()
        for available_date in available_dates:
            if earliest_acceptable_date <= available_date:
                date_to_potential_participants[available_date].append(meeting_preference)

    # Now consider other rules, e.g. everyone will get positive value from the meeting and
    # the meeting meets the minimal size for participants.

    # Here is the algorithm to schedule meetings:
    # We would like to optimize the total value of meetings for the considered period.
    # Each meeting's value is calculated as the N*(N-1), N is the number of meeting participants,
    # e.g. 10 people's meeting has value of 90, which is better than 2 meetings with 7 people each (2 * (6*7) = 84).
    # This is approximated by each participant will add 1 value to other participants in the meeting.
    # Also, if one person attended multiple meetings WITHIN their preferred interval, seeing the same people again
    # will not add value to them, meeting new people who they haven't seen within the preferred period will add value.
    # The weighted attendance in meeting preference only matters when filtering people because of conflict.
    # Maybe consider using it to improve the scheduling in future.
    # This issue becomes an interval scheduling problem with dynamical weight of each interval.

    # Need to think about what to do if some people update their preference.
