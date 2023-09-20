from dal import autocomplete
from django import forms

from primary_data.models import Education

from .models import Profile


class EducationInlineForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = "__all__"

        widgets = {
            "university": autocomplete.ModelSelect2(
                url="primary_data:university-autocomplete",
                attrs={
                    # Set some placeholder
                    # 'data-placeholder': 'Autocomplete ...',
                    # Only trigger autocompletion after 3 characters have been typed
                    "data-minimum-input-length": 1,
                    "class": "",
                },
            ),
        }

    class Media:
        css = {
            "all": ("select2_custom.css",),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = (
            "date_created",
            "date_updated",
        )
        widgets = {
            "skill": autocomplete.ModelSelect2Multiple(
                url="primary_data:key-skill-autocomplete"
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ExperienceInlineForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = (
            "date_created",
            "date_updated",
        )
        widgets = {
            "skill": autocomplete.ModelSelect2Multiple(
                url="primary_data:key-skill-autocomplete"
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
