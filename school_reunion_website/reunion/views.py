import uuid

from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from .utils import valid_request_from_forms, record_new_meeting_preference

from .models import Meeting, MeetingPreference
from .forms import MeetingPreferenceForm, EntryForm, MeetingGenerationForm
import threading


# TODO: Simple global threading lock to prevent meeting over booked. May need to use better way.
#  Also, no concurrent test.
lock = threading.Lock()


def index(request):
    entry_form = EntryForm()
    pop_message = request.session.get('pop_message')
    request.session['pop_message'] = None
    return render(request, 'reunion/index.html', {'entry_form': entry_form,
                                                  'pop_message': pop_message})


def meeting_preference(request):
    if request.method == 'POST':
        valid_form = valid_request_from_forms(request.POST, [MeetingPreferenceForm, EntryForm], get_model=True)
        # currently, must all fields of MeetingPreferenceForm are filled, then it will be valid.
        print('MeetingPreferenceForm== debug== '+str(MeetingPreferenceForm(request.POST).is_valid()))

        meeting_code = request.POST.get('meeting_code', request.session.get('meeting_code'))
        meeting = get_object_or_404(Meeting, pk=meeting_code)
        registered_attendant_code = request.POST.get('registered_attendant_code',
                                                     request.session.get('registered_attendant_code'))
        if not registered_attendant_code and meeting.code_available_usage <= 0:
            raise Http404('This meeting has no available slot!')

        if valid_form.name == 'MeetingPreferenceForm':
            preference: MeetingPreference = valid_form.model
            if not registered_attendant_code:
                lock.acquire()
                # Need to fetch again to refresh the available slot.
                meeting = get_object_or_404(Meeting, pk=meeting_code)
                if meeting.code_available_usage <= 0:
                    raise Http404('This meeting has no available slot!')
                registered_attendant_code = uuid.uuid4()
                while MeetingPreference.objects.filter(registered_attendant_code=registered_attendant_code).exists():
                    registered_attendant_code = uuid.uuid4()
                meeting.code_available_usage -= 1
                preference.registered_attendant_code = str(registered_attendant_code)
                preference.meeting_id = meeting_code
                record_new_meeting_preference(meeting, preference)
                lock.release()
                # todo: Pop message with attendant id and send verification email.
                request.session['pop_message'] = f'Thank you for registration!' \
                                                 f'\nYour Registered Attendant Code is: {registered_attendant_code}'
                return redirect('reunion:index')
            else:
                preference.registered_attendant_code = registered_attendant_code
                preference.meeting_id = meeting_code
                preference.save()
                # todo: Pop success tab.
                request.session['pop_message'] = f'Your change is saved!'
                return redirect('reunion:index')

        elif valid_form.name == 'EntryForm':
            request.session['meeting_code'] = meeting_code
            meeting_preference_form = MeetingPreferenceForm()
            if registered_attendant_code:
                print("debug== entry_form.registered_attendant_code " + str(request.POST.get('registered_attendant_code')))
                request.session['registered_attendant_code'] = registered_attendant_code
                preference = get_object_or_404(MeetingPreference, pk=registered_attendant_code)
                meeting_preference_form = MeetingPreferenceForm(instance=preference)
            return render(request, 'reunion/meeting_preference.html', {'form': meeting_preference_form})


def meeting_generation(request):
    if request.method == 'POST':
        valid_request_from_forms(request.POST, [MeetingGenerationForm])

        meeting_code = uuid.uuid4()
        while Meeting.objects.filter(meeting_code=meeting_code).exists():
            meeting_code = uuid.uuid4()
        meeting = Meeting()
        meeting.display_name = request.POST['display_name']
        meeting.code_max_usage = request.POST['code_max_usage']
        meeting.code_available_usage = request.POST['code_max_usage']
        meeting.contact_email = request.POST['contact_email']
        meeting.meeting_code = meeting_code
        meeting.save()
        request.session['pop_message'] = f'Created Meeting with Code: {meeting_code}'
        return redirect('reunion:index')
    generation_form = MeetingGenerationForm()
    return render(request, 'reunion/meeting_generation.html', {'form': generation_form})
