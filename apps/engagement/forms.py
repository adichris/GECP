from django import forms
from crispy_forms.helper import FormHelper
from .models import Submission

class SubmissionForm(forms.ModelForm):
    consent = forms.BooleanField(label='I agree that this site may use these details to respond to my enquiry or application.')
    website = forms.CharField(required=False, widget=forms.HiddenInput)
    class Meta:
        model = Submission
        fields = ['name', 'email', 'message', 'consent']
        widgets = {'message': forms.Textarea(attrs={'rows': 5})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
    def clean_website(self):
        if self.cleaned_data['website']:
            raise forms.ValidationError('Unable to submit this form.')
        return ''


class ProgrammeIntakeForm(SubmissionForm):
    def __init__(self, *args, intake, **kwargs):
        super().__init__(*args, **kwargs)
        self.detail_names = []
        for name, label in intake['fields']:
            self.detail_names.append(name)
            field = forms.URLField if name.endswith('_url') else forms.CharField
            options = {'assume_scheme': 'https'} if name.endswith('_url') else {}
            self.fields[name] = field(label=label, max_length=500, required='optional' not in label.lower(), **options)
        self.order_fields(['name', 'email', *self.detail_names, 'message', 'consent', 'website'])
        self.fields['message'].label = 'Anything else you would like us to know?'
        self.fields['message'].required = False

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.details = {name: self.cleaned_data[name] for name in self.detail_names}
        if commit:
            obj.save()
        return obj
