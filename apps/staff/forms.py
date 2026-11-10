from urllib.parse import urlsplit
from django import forms
from apps.programmes.models import Project
from .images import clean_image, validate_upload
from .models import PortfolioItem, StaffProfile


class ProjectChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.name} — {obj.initiative.programme.name}'


class CleanImageMixin:
    """Validate uploads, then store a metadata-free re-encoded copy."""
    image_field = ''
    image_prefix = ''

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get(self.image_field)
        if upload and hasattr(upload, 'content_type'):  # a new upload, not the existing file
            try:
                validate_upload(upload)
                cleaned[self.image_field] = clean_image(upload, self.image_prefix)
            except forms.ValidationError as error:
                self.add_error(self.image_field, error)
        return cleaned


class StaffProfileForm(CleanImageMixin, forms.ModelForm):
    image_field, image_prefix = 'photo', 'staff'

    class Meta:
        model = StaffProfile
        fields = ['display_name', 'job_title', 'bio', 'photo', 'programmes', 'website_url', 'linkedin_url', 'is_public']
        labels = {'display_name': 'Name shown publicly', 'job_title': 'Role or job title', 'bio': 'About you',
                  'website_url': 'Personal website (optional)', 'linkedin_url': 'LinkedIn profile (optional)',
                  'is_public': 'Show my profile in the public team directory'}
        widgets = {'bio': forms.Textarea(attrs={'rows': 6}), 'programmes': forms.CheckboxSelectMultiple,
                   'photo': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['programmes'].queryset = self.fields['programmes'].queryset.filter(is_active=True).order_by('name')
        self.fields['programmes'].required = False
        self.fields['photo'].help_text = 'Optional. JPEG, PNG or WebP up to 5 MB. Location data is removed.'

    def clean_linkedin_url(self):
        url = self.cleaned_data['linkedin_url']
        host = (urlsplit(url).hostname or '').lower()
        if url and host != 'linkedin.com' and not host.endswith('.linkedin.com'):
            raise forms.ValidationError('Enter a linkedin.com profile address.')
        return url


class PortfolioItemForm(CleanImageMixin, forms.ModelForm):
    image_field, image_prefix = 'image', 'work'
    projects = ProjectChoiceField(
        queryset=Project.objects.none(), required=False, widget=forms.CheckboxSelectMultiple,
        label='GECP projects you worked on (optional)',
        help_text='Select any projects this work was part of. Leave blank for independent work.',
    )

    class Meta:
        model = PortfolioItem
        fields = ['title', 'kind', 'role', 'summary', 'description', 'projects', 'started_on', 'ended_on',
                  'link_url', 'image', 'is_public']
        labels = {'kind': 'Type of work', 'role': 'Your role (optional)', 'summary': 'Short summary',
                  'description': 'Details (optional)', 'started_on': 'Start date (optional)',
                  'ended_on': 'End date (optional)', 'link_url': 'Link to the work (optional)',
                  'image': 'Image (optional)', 'is_public': 'Show this item on my public portfolio'}
        widgets = {'description': forms.Textarea(attrs={'rows': 6}),
                   'started_on': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'ended_on': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
                   'image': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['projects'].queryset = (
            Project.objects.filter(initiative__programme__is_active=True)
            .exclude(name='Demonstration delivery pilot')  # seeded placeholder, hidden on programme sites too
            .select_related('initiative__programme').order_by('initiative__programme__name', 'name')
        )
        self.fields['image'].help_text = 'JPEG, PNG or WebP up to 5 MB. Location data is removed.'
