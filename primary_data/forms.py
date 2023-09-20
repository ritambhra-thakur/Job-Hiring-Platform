from dal import autocomplete
from django import forms

from .models import Address


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = "__all__"
        widgets = {
            "state": autocomplete.ModelSelect2(
                url="primary_data:state-autocomplete",
                forward=["country"],
            ),
            "city": autocomplete.ModelSelect2(
                url="primary_data:city-autocomplete",
                forward=["state"],
            ),
        }

    class Media:
        css = {
            "all": ("select2_custom.css",),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
