from django import forms
from .models import MeetingPreference, Meeting
from crispy_forms.helper import FormHelper
from crispy_forms.bootstrap import InlineRadios, FormActions, InlineCheckboxes
from bootstrap_datepicker_plus.widgets import TimePickerInput
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from .utils import get_country_to_holidays_map
from taggit.forms import TagField, TagWidget


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
    custom_dates = forms.DateField(widget=forms.DateInput)
    repeat_option_for_adding_custom_dates = forms.ChoiceField(
        choices=[('repeat_each_year', 'repeat each year'),
                 ('repeat_each_month', 'repeat each month'),
                 ('repeat_each_week', 'repeat each week'),
                 ('no_repeat', 'no repeat')],
        widget=forms.RadioSelect)

    earliest_meeting_time = forms.TimeField(widget=TimePickerInput())
    latest_meeting_time = forms.TimeField(widget=TimePickerInput())
    expected_attending_time_zone = forms.ChoiceField(
        choices=[(i-12, f'UTC{i-12 if i < 12 else f"+{i-12}"}') for i in reversed(range(25))]
    )
    acceptable_meeting_methods = forms.MultipleChoiceField(
        choices=[('online', 'online'), ('offline', 'offline')],
        widget=forms.CheckboxSelectMultiple)

    selected_attending_dates = TagField(widget=TagWidget)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-4 mb-0'),
                Column('email', css_class='form-group col-md-4 mb-0'),
                Column('preferred_attending_frequency_in_months', css_class='form-group col-md-4 mb-0'),
                css_class='form-row',
            ),

            Row(
                Column('country', css_class='form-group col-md-4 mb-0'),
                Column('holiday', css_class='form-group col-md-8 mb-0'),
                css_class='form-row',
            ),
            InlineRadios('repeat_option_for_adding_custom_dates'),
            'custom_dates',
            'selected_attending_dates',

            Row(
                Column('earliest_meeting_time', css_class='form-group col-md-3 mb-0'),
                Column('latest_meeting_time', css_class='form-group col-md-3 mb-0'),
                Column('expected_attending_time_zone', css_class='form-group col-md-3 mb-0'),
                Column('preferred_meeting_duration_in_hour', css_class='form-group col-md-3 mb-0'),
                css_class='form-row',
            ),

            InlineCheckboxes('acceptable_meeting_methods'),
            'acceptable_offline_meeting_locations',
            'preferred_meeting_activities',
            'weighted_attendants',

            Row(
                Column('minimal_meeting_value', css_class='form-group col-md-6 mb-0'),
                Column('minimal_meeting_size', css_class='form-group col-md-6 mb-0'),
                css_class='form-row',
            ),

            FormActions(Submit('submit', 'Submit', css_class='bin-success'))
        )
