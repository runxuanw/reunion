from django.db import transaction
from django.http import Http404
import dataclasses
from django.db import models
from typing import Optional


VERIFIED_EMAIL_STATUS = 'Verified'


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
    if raise_if_not_found:
        raise Http404('Not valid form entry.')
    return ''


@transaction.atomic
def record_new_meeting_preference(meeting, preference):
    meeting.save()
    preference.save()
