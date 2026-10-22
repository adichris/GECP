from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Thread
from .guests import EMOJIS


class SafeForm(forms.Form):
    def __init__(self, *args, guest=False, **kwargs):
        super().__init__(*args, **kwargs)
        if guest:
            self.fields["guest_name"] = forms.RegexField(
                regex=r"^[A-Za-z0-9][A-Za-z0-9 _-]{1,29}$",
                max_length=30,
                label="Guest username",
                help_text="2–30 letters, numbers, spaces, underscores or hyphens. Guest identities are not verified.",
            )
            self.fields["guest_emoji"] = forms.ChoiceField(choices=[(e, e) for e in EMOJIS], label="Your emoji")
            self.order_fields(["guest_name", "guest_emoji", "title", "category", "body", "website", "consent"])

    website = forms.CharField(required=False, widget=forms.HiddenInput)
    consent = forms.BooleanField(
        label="I agree to the community guidelines and understand that my username and approved contribution will be public."
    )

    def clean_website(self):
        if self.cleaned_data["website"]:
            raise forms.ValidationError("Unable to submit this form.")
        return ""


class ThreadForm(SafeForm):
    title = forms.CharField(max_length=180)
    category = forms.ChoiceField(choices=Thread._meta.get_field("category").choices)
    body = forms.CharField(max_length=8000, widget=forms.Textarea(attrs={"rows": 7}), label="Your message")


class CommentForm(SafeForm):
    body = forms.CharField(max_length=4000, widget=forms.Textarea(attrs={"rows": 4}), label="Your comment")


class ReportForm(forms.Form):
    reason = forms.CharField(
        max_length=1500, widget=forms.Textarea(attrs={"rows": 4}), label="Why are you reporting this contribution?"
    )


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(help_text="Used for password recovery; never shown publicly.")
    consent = forms.BooleanField(label="I agree to the community guidelines and privacy information.")
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta(UserCreationForm.Meta):
        fields = ["username", "email"]

    def clean_website(self):
        if self.cleaned_data["website"]:
            raise forms.ValidationError("Unable to register.")
        return ""

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Unable to use this email. Try signing in or recovering your password.")
        return email
