from django import forms
from .models import MeetingPreference, Meeting
from crispy_forms.helper import FormHelper
from crispy_forms.bootstrap import InlineRadios, FormActions, InlineCheckboxes
from bootstrap_datepicker_plus.widgets import TimePickerInput
from crispy_forms.layout import Layout, Submit, Row, Column, Button, ButtonHolder, HTML, Div
from .utils import get_country_to_holidays_map, REPEAT_OPTIONS
from taggit.forms import TagField, TagWidget
import ast
from django.urls import reverse


class TagifyField(TagField):
    def clean(self, value):
        value = forms.CharField.clean(self, value)
        if not value:
            return ''
        try:
            eval_list = ast.literal_eval(value)
            if not isinstance(eval_list, list):
                return ''
            return ','.join([item['value'] for item in eval_list if isinstance(item, dict)])
        except ValueError:
            raise forms.ValidationError("Please provide a comma-separated list of tags.")


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
        self.helper.form_action = reverse('reunion:meeting_preference')
        self.helper.form_class = 'col-md-4'
        self.helper.layout = Layout(

            Row(
                Column('meeting_code')),
            Row(
                Column('registered_attendant_code')),
            Row(
                FormActions(Submit('submit', 'JOIN MEETING/UPDATE PREFERENCE', css_class='bin-success')),
                css_class='text-center my-2'),
            Row(
                HTML('<hr class="hr-line">'),
                css_class='form-row justify-content-center text-center my-4'),
            Row(
                ButtonHolder(
                    HTML('<a class="btn btn-primary bin-success"'
                         ' href={% url "reunion:meeting_generation" %}>CREATE NEW MEETING</a>')),
                css_class='form-row justify-content-center text-center'),
        )


class MeetingGenerationForm(forms.ModelForm):
    class Meta:
        model = Meeting
        fields = ('display_name', 'code_max_usage', 'contact_email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('reunion:meeting_generation')
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
    country = forms.ChoiceField(
        choices=tuple([(country, country) for country, _ in country_to_holidays.items()]), required=False)
    choices = []
    for country_name, holidays in country_to_holidays.items():
        class_name = country_name.replace(' ', '_')
        choices.append((f'{country_name}_0',
                        {'label': f'Select All {country_name} Holidays',
                         'class': class_name,
                         'style': 'display: none'}))
        for idx, (holiday_name, _) in enumerate(holidays.items()):
            choices.append((f'{country_name}_{idx+1}',
                            {'label': f'{holiday_name}',
                             'class': class_name,
                             'style': 'display: none'}))
    holiday = forms.ChoiceField(label='Holiday (repeat each year)',
                                choices=tuple(choices),
                                widget=SelectWithAttribute,
                                required=False)
    custom_dates = forms.CharField(widget=forms.DateInput, required=False)
    repeat_option_for_adding_custom_dates = forms.ChoiceField(
        choices=REPEAT_OPTIONS,
        widget=forms.RadioSelect,
        required=False)
    selected_attending_dates = TagifyField(widget=TagWidget)

    earliest_meeting_time = forms.TimeField(widget=TimePickerInput())
    latest_meeting_time = forms.TimeField(widget=TimePickerInput())
    online_attending_time_zone = forms.ChoiceField(
        choices=[(i-12, f'UTC{i-12 if i < 12 else f"+{i-12}"}') for i in reversed(range(25))]
    )
    preferred_meeting_duration = forms.TimeField(widget=TimePickerInput())
    acceptable_meeting_methods = forms.MultipleChoiceField(
        choices=[('online', 'Online'), ('offline', 'Offline')],
        widget=forms.CheckboxSelectMultiple,
        required=False)

    acceptable_offline_meeting_cities = TagifyField(widget=TagWidget)

    other_attendant = forms.CharField(label='Other Attendant (press enter to add)', required=False)
    other_attendant_weight = forms.FloatField(label='Attendant Value (default 1; press enter to add)', required=False)
    weighted_attendants = TagifyField(widget=TagWidget, label='Special valued attendants', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('reunion:meeting_preference')
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-4 mb-0'),
                Column('email', css_class='form-group col-md-4 mb-0'),
                Column('prefer_to_attend_every_n_months', css_class='form-group col-md-4 mb-0'),
                css_class='form-row',
            ),

            Row(
                Column('country', css_class='form-group col-md-4 mb-0'),
                Column('holiday', css_class='form-group col-md-8 mb-0'),
                css_class='form-row',
            ),
            Row(
                Column(InlineRadios('repeat_option_for_adding_custom_dates'), css_class='form-group col-md-6 mb-0'),
                Column('custom_dates', css_class='form-group col-md-6 mb-0'),
                css_class='form-row',
            ),

            # 'repeat_option_for_adding_custom_dates',
            # 'custom_dates',
            'selected_attending_dates',

            Row(
                Column('earliest_meeting_time', css_class='form-group col-md-3 mb-0'),
                Column('latest_meeting_time', css_class='form-group col-md-3 mb-0'),
                Column('online_attending_time_zone', css_class='form-group col-md-3 mb-0'),
                Column('preferred_meeting_duration', css_class='form-group col-md-3 mb-0'),
                css_class='form-row',
            ),

            InlineCheckboxes('acceptable_meeting_methods'),
            'acceptable_offline_meeting_cities',

            Row(
                Column('other_attendant', css_class='form-group col-md-6 mb-0'),
                Column('other_attendant_weight', css_class='form-group col-md-6 mb-0'),
                css_class='form-row',
            ),
            'weighted_attendants',
            Row(
                Column('minimal_meeting_value', css_class='form-group col-md-6 mb-0'),
                Column('minimal_meeting_size', css_class='form-group col-md-6 mb-0'),
                css_class='form-row',
            ),

            FormActions(Submit('submit', 'Submit', css_class='bin-success'))
        )
