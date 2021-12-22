from django import forms
from .models import MeetingPreference, Meeting
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit
from .utils import get_country_to_holidays_map


class SelectWithAttribute(forms.widgets.Select):
    """
    Select With Option Attributes:
        subclass of Django's Select widget that allows attributes in options,
        like disabled="disabled", title="help text", class="some classes",
              style="background: color;"...

    Pass a dict instead of a string for its label:
        choices = [ ('value_1', 'label_1'),
                    ...
                    ('value_k', {'label': 'label_k', 'foo': 'bar', ...}),
                    ... ]
    The option k will be rendered as:
        <option value="value_k" foo="bar" ...>label_k</option>
    """

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        if isinstance(label, dict):
            opt_attrs = label.copy()
            label = opt_attrs.pop('label')
        else:
            opt_attrs = {}
        option_dict = super(SelectWithAttribute, self).create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs)
        for key, val in opt_attrs.items():
            option_dict['attrs'][key] = val
        return option_dict


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

    country_to_holidays = get_country_to_holidays_map()
    country = forms.ChoiceField(choices=tuple([(country, country) for country, _ in country_to_holidays.items()]))
    choices = []
    for country_name, holidays in country_to_holidays.items():
        choices.append((f'{country_name}_0',
                        {'label': f'Select All {country_name} Holidays',
                         'class': country_name,
                         'style': 'display: none'}))
        for idx, (date, holiday_name) in enumerate(holidays.items()):
            choices.append((f'{country_name}_{idx+1}',
                            {'label': f'{date} {holiday_name}',
                             'class': country_name,
                             'style': 'display: none'}))
    holiday = forms.ChoiceField(choices=tuple(choices), widget=SelectWithAttribute)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'name',
            'email',
            'preferred_attending_frequency_in_months',
            'country',
            'holiday',
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
