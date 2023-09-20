from django.contrib import admin

from .models import Currency, ReferralPolicy


class ReferralPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "referral_name",
        "country",
        "company",
        "referral_amount",
        "country_payout_policy",
    )


class CurrencyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "currency_name",
    )


# Register your models here.
admin.site.register(ReferralPolicy, ReferralPolicyAdmin)
admin.site.register(Currency, CurrencyAdmin)
