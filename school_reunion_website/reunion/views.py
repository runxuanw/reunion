import uuid

from django.http import HttpResponseRedirect, Http404
from django.template import loader
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from .models import Meeting
from .forms import MeetingPreferenceForm, EntryForm, MeetingGenerationForm


def index(request):
    # latest_question_list = Question.objects.order_by('-pub_date')[:5]
    # context = {
    #     'latest_question_list': latest_question_list,
    # }
    entry_form = EntryForm()
    return render(request, 'reunion/index.html', {'entry_form': entry_form,
                                                  'created_meeting': request.session.get('created_meeting')})


def meeting_preference(request):
    if request.method == 'POST':
        form = MeetingPreferenceForm(request.POST)
        if form.is_valid():
            form.save()
            # Pop success tab and send verification email.

    preference_form = MeetingPreferenceForm()
    return render(request, 'reunion/meeting_preference.html', {'form': preference_form})


def meeting_generation(request):
    if request.method == 'POST':
        form = MeetingGenerationForm(request.POST)
        if form.is_valid():
            meeting_code = uuid.uuid4()
            while Meeting.objects.filter(meeting_code=meeting_code).exists():
                meeting_code = uuid.uuid4()
            meeting = Meeting()
            meeting.display_name = request.POST['display_name']
            meeting.code_max_usage = request.POST['code_max_usage']
            meeting.contact_email = request.POST['contact_email']
            meeting.meeting_code = meeting_code
            meeting.save()
            request.session['created_meeting'] = str(meeting_code)
            return redirect('reunion:index')
    generation_form = MeetingGenerationForm()
    return render(request, 'reunion/meeting_generation.html', {'form': generation_form})


# def results(request, question_id):
#     question = get_object_or_404(Question, pk=question_id)
#     return render(request, 'reunion/results.html', {'question': question})


# def vote(request, question_id):
#     question = get_object_or_404(Question, pk=question_id)
#     try:
#         selected_choice = question.choice_set.get(pk=request.POST['choice'])
#     except (KeyError, Choice.DoesNotExist):
#         # Redisplay the question voting form.
#         return render(request, 'reunion/detail.html', {
#             'question': question,
#             'error_message': "You didn't select a choice.",
#         })
#     else:
#         selected_choice.votes += 1
#         selected_choice.save()
#         # Always return an HttpResponseRedirect after successfully dealing
#         # with POST data. This prevents data from being posted twice if a
#         # user hits the Back button.
#         return HttpResponseRedirect(reverse('reunion:results', args=(question.id,)))
