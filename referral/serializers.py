from dataclasses import fields

from pyexpat import model
from rest_framework import serializers

from primary_data.serializers import CountrySerializer, StateSerializer
from referral.models import Currency, ReferralPolicy


class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralPolicy
        fields = "__all__"


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = "__all__"


class ReferralListSerializer(serializers.ModelSerializer):
    state = StateSerializer(read_only=True)
    country = CountrySerializer(read_only=True)
    currency = CurrencySerializer(read_only=True)

    class Meta:
        model = ReferralPolicy
        fields = "__all__"


class CsvReferralSerializer(serializers.ModelSerializer):
    """
    CsvReferralSerializer class is created with user Model and added
    all fields from the CsvReferralSerializer
    """

    class Meta:
        model = ReferralPolicy
        fields = [
            "referral_name",
            "country",
            "state",
            "country_payout_policy",
            "attach_referral_policy_document",
            "is_active",
        ]
