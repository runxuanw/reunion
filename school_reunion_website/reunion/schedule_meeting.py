import datetime
import uuid

from .models import MeetingPreference, Meeting, MeetingRecord, MeetingAttendance
from .utils import ATTENDANT_PENDING_STATUS, VERIFIED_EMAIL_STATUS, get_country_to_holidays_map, REPEAT_OPTIONS_SET, NO_REPEAT, REPEAT_EACH_YEAR, REPEAT_EACH_WEEK, REPEAT_EACH_MONTH
import collections
from typing import List, Dict, Optional, Tuple, Union, Set
import random
from .emails import send_scheduled_meeting_notification
import json


ALL_DATES = 'all_dates'
# Consider to invite the candidate at least after 7 months if they prefer to attend every 10 months.
MIN_ATTENDING_INTERVAL_TO_PREFERRED_INTERVAL = 0.7
# Max participate value for people never attended the meeting: 365 * 4
MAX_PARTICIPATE_VALUE = 1460

# 1. {date: available people count with relax of 1 week} for 1 year from current time. (done)
# 2. iteratively generate meeting from most count date to least count date
#   2.0 filtering people
#   2.1 handle weighted people
#   2.2 when generate a meeting, weight more for unparticipated people in past meetings
#   2.3 consider time zone
# 3. send invitation for those who doesn't fit in the strict date rule (2 weeks)
# 4. send invitation if the meeting is possible, before 2 month, have 2 weeks to confirm

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


def _pick_next_date_to_participate(
        dates_with_participants_preference: Dict[datetime.date, List[MeetingPreference]],
        history_meetings_attendance: List[MeetingAttendance]) \
        -> Tuple[datetime.date, List[MeetingPreference]]:
    # Gets the date with most people want to attend.
    date_with_most_participants: Optional[Tuple[datetime.date, List[MeetingPreference]]] = None
    for date, preferences in dates_with_participants_preference.items():
        if date_with_most_participants and len(preferences) <= len(date_with_most_participants[1]):
            continue
        current_potential_participants = preferences
        while True:
            sanitized_participants = _sanitize_with_minimal_meeting_value_preference(
                current_potential_participants, history_meetings_attendance)
            sanitized_participants_confirm = _sanitize_with_meeting_size_preference(sanitized_participants)
            if len(sanitized_participants_confirm) == len(sanitized_participants):
                break
            current_potential_participants = sanitized_participants_confirm
        date_with_most_participants = (date, sanitized_participants)
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


def _sanitize_with_meeting_size_preference(potential_participants: List[MeetingPreference]) -> List[MeetingPreference]:
    participant_codes_to_minimal_meeting_size = []
    for meeting_preference in potential_participants:
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
    for meeting_preference in potential_participants:
        if meeting_preference.registered_attendant_code not in refuse_to_participate:
            updated_preferences.append(meeting_preference)
    return updated_preferences


def _sanitize_dates_with_meeting_size_preference(date_to_potential_participants):
    """Updates date_to_potential_participants with minimal meeting size requirement."""
    for date in date_to_potential_participants.keys():
        potential_participants = date_to_potential_participants[date]
        date_to_potential_participants[date] = _sanitize_with_meeting_size_preference(potential_participants)
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


def _get_meeting_value_data_for_preference(
        participant, all_participants_preference) -> Tuple[bool, List[MeetingPreference]]:
    """Return (would this participant prefer to be removed, [ways to choose in order for participant to attend])"""
    total_meeting_value = 0
    negative_meeting_value = 0
    negative_value_entries = []
    must_be_removed = False
    constrained_participants_pool = []
    all_participants_preference_name_map = {preference.name: preference for preference in all_participants_preference}

    for other_participant in all_participants_preference:
        value = participant.weighted_attendants.get(other_participant.name, 1)
        total_meeting_value += value
        # Include oneself as 1.
        if value < 1 and other_participant.name in all_participants_preference_name_map:
            negative_value_entries.append([value, all_participants_preference_name_map.get(other_participant.name)])
            negative_meeting_value += value
    if total_meeting_value >= participant.minimal_meeting_value:
        return must_be_removed, constrained_participants_pool

    # Check if there is a resolvable conflict in the meeting.
    if total_meeting_value - negative_meeting_value < participant.minimal_meeting_value:
        must_be_removed = True
    # If all the ways to choose is listed, it will be factorial. Just find the way with minimal people involved.
    else:
        # Shuffle the list so the same negative value has a equal chance been selected.
        random.shuffle(negative_value_entries)
        negative_value_entries.sort(key=lambda x: x[0])
        meeting_value = total_meeting_value
        for negative_entry in negative_value_entries:
            if meeting_value >= participant.minimal_meeting_value:
                break
            constrained_participants_pool.append(negative_entry[1])
            meeting_value += negative_entry[0]
    return must_be_removed, constrained_participants_pool


def _sanitize_with_minimal_meeting_value_preference(
        potential_participants: List[MeetingPreference],
        history_meeting_attendance: List[MeetingAttendance]):
    """Updates potential_participants with no negative meeting value requirement."""
    current_potential_participants = potential_participants
    # Because removing participants could results in a chain reaction. Need to run this two times to confirm.
    # (not efficient though)
    while True:
        sanitized_potential_participants = _sanitize_with_minimal_meeting_value_preference_one_time(
            current_potential_participants, history_meeting_attendance)
        sanitized_potential_participants_confirm = _sanitize_with_minimal_meeting_value_preference_one_time(
            sanitized_potential_participants, history_meeting_attendance)
        if len(sanitized_potential_participants) == len(sanitized_potential_participants_confirm):
            return sanitized_potential_participants
        current_potential_participants = sanitized_potential_participants_confirm


def _sanitize_with_minimal_meeting_value_preference_one_time(
        potential_participants: List[MeetingPreference],
        history_meeting_attendance: List[MeetingAttendance]) -> List[MeetingPreference]:
    """Updates potential_participants with no negative meeting value requirement."""
    conflict_constrain = []
    conflict_participant_codes = set()
    unresolvable_participant_codes = set()
    for participant in potential_participants:
        must_be_removed, tmp_conflict_constrain = (
            _get_meeting_value_data_for_preference(participant, potential_participants))
        if must_be_removed:
            unresolvable_participant_codes.add(participant.registered_attendant_code)
            continue
        elif not tmp_conflict_constrain:
            continue
        else:  # resolvable conflict
            conflict_constrain.append((participant, tmp_conflict_constrain))
            conflict_participant_codes.add(participant.registered_attendant_code)
            conflict_participant_codes.update([p.registered_attendant_code for p in tmp_conflict_constrain])

    # Handle conflict_constrain. Search through all combination O(N*2^N), N is number of people.
    resolved_participant_codes = _get_participants_and_resolve_conflict(
        conflict_constrain, history_meeting_attendance)

    sanitized_potential_participants = []
    for participant in potential_participants:
        attendance_code = participant.registered_attendant_code
        if attendance_code in unresolvable_participant_codes:
            continue
        if (attendance_code in conflict_participant_codes
                and participant.registered_attendant_code not in resolved_participant_codes):
            continue
        sanitized_potential_participants.append(participant)

    return sanitized_potential_participants


# This is an approximation of meeting value. The meeting records should be used for better estimation.
def _get_participant_meeting_value(attendance: MeetingAttendance, now: datetime.datetime):
    return (now - attendance.last_confirmation_time).days


def get_utc_now():
    # Must be aware of timezone.
    return datetime.datetime.now(datetime.timezone.utc)


def _get_participants_and_resolve_conflict(
        conflict_constrain: List[Tuple[MeetingPreference, List[MeetingPreference]]],
        history_meeting_attendance: List[MeetingAttendance]) -> Set[str]:
    conflict_edges: Dict[str, Set[str]] = collections.defaultdict(set)
    participants_value: Dict[str, int] = collections.defaultdict(int)
    utc_now = get_utc_now()
    # Shorten UUID to index, {UUID: str(index)}.
    uuid_to_shorten_codes_dict = {}

    # Construct the conflict as edges in both direction.
    for conflict in conflict_constrain:
        conflict_starter_code = conflict[0].registered_attendant_code
        if conflict_starter_code not in uuid_to_shorten_codes_dict:
            uuid_to_shorten_codes_dict[conflict_starter_code] = str(len(uuid_to_shorten_codes_dict))
        for conflict_receiver in conflict[1]:
            conflict_receiver_code = conflict_receiver.registered_attendant_code
            if conflict_receiver_code not in uuid_to_shorten_codes_dict:
                uuid_to_shorten_codes_dict[conflict_receiver_code] = str(len(uuid_to_shorten_codes_dict))
            conflict_edges[uuid_to_shorten_codes_dict[conflict_starter_code]].add(uuid_to_shorten_codes_dict[conflict_receiver_code])
            conflict_edges[uuid_to_shorten_codes_dict[conflict_receiver_code]].add(uuid_to_shorten_codes_dict[conflict_starter_code])
    for attendance in history_meeting_attendance:
        if attendance.attendant_preference.registered_attendant_code not in uuid_to_shorten_codes_dict:
            continue
        participants_value[uuid_to_shorten_codes_dict[attendance.attendant_preference.registered_attendant_code]] = (
            _get_participant_meeting_value(attendance, utc_now))

    # {ordered unchecked participants: (cached optimal value, [actual participants])} e.g. {'5,6,7,9': (321, [5, 7, 9])}
    optimal_meeting_value_with_participants_cache: Dict[str, Tuple[int, List[str]]] = {}
    shorten_codes_to_uuid_dict = {val: key for key, val in uuid_to_shorten_codes_dict.items()}

    # 2^N = sum(C(i, N)) for 0<=i<=N.
    # Memory usage C(max_cache_key_depth, N).
    optimal_value, participants_index = _get_optimal_meeting_value_with_participants(
        [str(i) for i in range(len(uuid_to_shorten_codes_dict))],
        conflict_edges, participants_value,
        optimal_meeting_value_with_participants_cache,
        max_cache_key_depth=7)

    # Decode index to UUID.
    return set([shorten_codes_to_uuid_dict[index] for index in participants_index])


def _get_optimal_meeting_value_with_participants(
        participants_to_be_check: List[str],
        conflict_edges: Dict[str, Set[str]],
        participants_value: Dict[str, int],
        optimal_meeting_value_with_participants_cache: Dict[str, Tuple[int, List[str]]],
        max_cache_key_depth: int):
    if not participants_to_be_check:
        return 0, []
    if len(participants_to_be_check) == 1:
        return participants_value.get(participants_to_be_check[0], MAX_PARTICIPATE_VALUE), [participants_to_be_check[0]]
    cache_key = ''
    if len(participants_to_be_check) <= max_cache_key_depth:
        cache_key = ','.join(participants_to_be_check)
        if cache_key in optimal_meeting_value_with_participants_cache:
            value, participants = optimal_meeting_value_with_participants_cache[cache_key]
            return value, participants.copy()

    # If we don't choose the first participants in list.
    optimal_value_if_skip, participants_if_skip = _get_optimal_meeting_value_with_participants(
        [p for p in participants_to_be_check[1:]], conflict_edges, participants_value,
        optimal_meeting_value_with_participants_cache,
        max_cache_key_depth)
    # If we choose the first participants in list.
    choose_participant = participants_to_be_check[0]
    conflict_edges_for_chosen = conflict_edges.get(choose_participant)
    optimal_value_if_choose, participants_if_choose = _get_optimal_meeting_value_with_participants(
        [p for p in participants_to_be_check[1:] if p not in conflict_edges_for_chosen],
        conflict_edges,
        participants_value,
        optimal_meeting_value_with_participants_cache,
        max_cache_key_depth)
    optimal_value_if_choose += participants_value.get(choose_participant, MAX_PARTICIPATE_VALUE)
    participants_if_choose.append(choose_participant)

    if optimal_value_if_skip > optimal_value_if_choose:
        optimal_value = optimal_value_if_skip
        optimal_participants = participants_if_skip
    elif optimal_value_if_skip < optimal_value_if_choose:
        optimal_value = optimal_value_if_choose
        optimal_participants = participants_if_choose
    # Pick the meeting with max people, if everything else is the same.
    elif len(participants_if_choose) > len(participants_if_skip):
        optimal_value = optimal_value_if_choose
        optimal_participants = participants_if_choose
    else:
        optimal_value = optimal_value_if_skip
        optimal_participants = participants_if_skip
    if len(participants_to_be_check) <= max_cache_key_depth:
        optimal_meeting_value_with_participants_cache[cache_key] = (optimal_value, optimal_participants.copy())

    return optimal_value, optimal_participants


def get_weighted_attendants_as_dictionary(weighted_attendants: str):
    """Parses the weighted_attendants string to dictionary, e.g. assa:-1,lala:-10,haha:20"""
    weighted_attendants_dict = {}
    for weighted_attendant_str in weighted_attendants.split(','):
        try:
            split_value = weighted_attendant_str.split(':')
            if len(split_value) != 2:
                continue
            weighted_attendants_dict[split_value[0]] = float(split_value[1])
        except:
            continue
    return weighted_attendants_dict


def get_feasible_meeting_dates_with_participants(
        meeting: Meeting, start: datetime.date, until: datetime.date) \
        -> List[Tuple[datetime.date, List[MeetingPreference]]]:
    meeting_preferences = MeetingPreference.objects.filter(meeting=meeting.meeting_code)
    date_to_potential_participants = collections.defaultdict(list)
    # Iterate through all preference to filter out recently participated ones.
    history_meetings_attendance = []
    for meeting_preference in meeting_preferences:
        if meeting_preference.email_verification_code != VERIFIED_EMAIL_STATUS:
            continue
        # Sanitize the weighted attendants to dictionary.
        meeting_preference.weighted_attendants = (
            get_weighted_attendants_as_dictionary(meeting_preference.weighted_attendants))
        attendance = MeetingAttendance.objects.get(
            attendant_preference=meeting_preference.registered_attendant_code)
        history_meetings_attendance.append(attendance)
        available_dates = get_available_dates(meeting_preference, start=start, until=until)
        # Also consider the notification sent but haven't received a reply: last_invitation_time.
        _, earliest_acceptable_date = _get_unavailable_date_range(
            max(attendance.last_confirmation_time, attendance.last_invitation_time), meeting_preference)
        for available_date in available_dates:
            if earliest_acceptable_date <= available_date:
                date_to_potential_participants[available_date].append(meeting_preference)

    # Consider minimal meeting size preference.
    _sanitize_dates_with_meeting_size_preference(date_to_potential_participants)

    # Use greedy algorithm to arrange meetings. With the date most people can participate being considered first.
    picked_dates_with_participants_preference: List[Tuple[datetime.date, List[MeetingPreference]]] = []
    while date_to_potential_participants:
        next_meeting_date, participants_preference = (
            _pick_next_date_to_participate(date_to_potential_participants, history_meetings_attendance))
        date_to_potential_participants.pop(next_meeting_date)
        if participants_preference:
            picked_dates_with_participants_preference.append((next_meeting_date, participants_preference))
        _update_other_dates_after_picking_meeting_date(
            next_meeting_date, participants_preference, date_to_potential_participants)
        _sanitize_dates_with_meeting_size_preference(date_to_potential_participants)

    return picked_dates_with_participants_preference


# TODO: to be implemented
def create_online_meeting_link():
    return ''


def arrange_new_meeting(host_meeting: Meeting,
                        meeting_date: datetime.date,
                        participants_preference: List[MeetingPreference]):
    record = MeetingRecord(meeting=host_meeting)
    # TODO: timezone and start time to be implemented
    record.meeting_start_time = meeting_date
    # TODO: timezone and end time to be implemented
    record.meeting_end_time = meeting_date + datetime.timedelta(days=1)
    # TODO: offline meeting location to be implemented
    record.online_meeting_link = create_online_meeting_link()
    invitation_code_to_attendant_code = (
        {str(uuid.uuid4()): p.registered_attendant_code for p in participants_preference})
    record.invitation_link_to_attendant_code = json.dumps(invitation_code_to_attendant_code)
    record.attendant_code_to_status = json.dumps(
        {p.registered_attendant_code: ATTENDANT_PENDING_STATUS for p in participants_preference})
    record.save()
    # TODO: update last invitation time?
    for participant_preference in participants_preference:
        send_scheduled_meeting_notification(record, participant_preference, participants_preference)


def schedule_meeting(meeting: Meeting):
    utcnow = datetime.datetime.get_utc_now()
    schedule_start_date = (utcnow + datetime.timedelta(days=60)).date()
    schedule_until_date = (utcnow + datetime.timedelta(days=365+60)).date()
    notification_until_date = (utcnow + datetime.timedelta(days=90)).date()
    dates_with_participants_preference = get_feasible_meeting_dates_with_participants(
        meeting,
        start=schedule_start_date,
        until=schedule_until_date)
    for date, participants_preference in dates_with_participants_preference:
        # Send notification only when at least two months are available and
        # don't send notification if it is more than three months.
        if schedule_start_date <= date <= notification_until_date:
            arrange_new_meeting(meeting, date, participants_preference)
