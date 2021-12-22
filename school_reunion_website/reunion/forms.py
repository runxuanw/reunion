from django import forms
from .models import MeetingPreference, Meeting
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit


class EntryForm(forms.Form):
    meeting_code = forms.CharField(required=True)
    registered_attendant_code = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'meeting_code',
            'registered_attendant_code',
            Submit('submit', 'Submit', css_class='bin-success')
        )


class MeetingGenerationForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ('display_name', 'code_max_usage', 'contact_email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'display_name',
            'code_max_usage',
            'contact_email',
            Submit('submit', 'Submit', css_class='bin-success')
        )


class MeetingPreferenceForm(forms.ModelForm):
    class Meta:
        model = MeetingPreference
        exclude = ('registered_attendant_code', 'meeting', 'email_verification_code')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'name',
            'email',
            'preferred_attending_frequency_in_months',
            'repeated_available_holidays',
            'repeated_available_dates_each_year',
            'one_time_available_dates',
            'acceptable_meeting_time_range_in_day',
            'expected_attending_time_zones',
            'acceptable_offline_meeting_locations',
            'preferred_meeting_duration_in_hour',
            'acceptable_meeting_methods',
            'preferred_meeting_activities',
            'weighted_attendants',
            'minimal_meeting_value',
            'minimal_meeting_size',
            Submit('submit', 'Submit', css_class='bin-success')
        )
