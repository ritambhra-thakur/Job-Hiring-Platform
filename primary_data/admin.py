from django.contrib import admin

from .forms import AddressForm
from .models import *


# Register your models here.
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "iso2",
        "iso3",
        "phone_code",
        "capital",
        "currency",
    )
    list_display_links = ("name",)
    search_fields = (
        "name",
        "iso2",
        "iso3",
        "phone_code",
        "capital",
        "currency",
    )
    list_filter = ("currency",)
    list_per_page = 50


class StateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "country",
    )
    list_display_links = ("name",)
    search_fields = (
        "name",
        "country__name",
    )
    list_filter = ("country",)
    list_per_page = 100


class CityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "state",
        "country",
    )
    list_display_links = ("name",)
    search_fields = (
        "name",
        "country__name",
        "state__name",
    )
    list_filter = ("country",)
    list_per_page = 100


class UniversityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "domain",
        "web_page",
        "country",
    )
    list_display_links = ("name",)
    search_fields = (
        "name",
        "domain",
        "web_page",
    )
    list_filter = ("country",)
    list_per_page = 100


class KeySkillAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "skill",
        "verified",
    )
    list_display_links = ("id",)
    search_fields = ("skill",)
    list_per_page = 100


class AddressAdmin(admin.ModelAdmin):
    form = AddressForm

    list_display = (
        "id",
        "address_one",
        "address_two",
        "address_three",
        "pin_code",
        "country",
        "state",
        "city",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    search_fields = (
        "pin_code",
        "address_one",
        "address_two",
        "address_three",
        "country__name",
        "state__name",
        "city__name",
    )
    list_per_page = 100


class EducationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "profile",
        "university",
        "passing_out_year",
        "country",
        "created_at",
        "updated_at",
    )
    list_per_page = 100


class ExperienceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "company_name",
        "role_and_responsibilities",
        "is_current_company",
        "admin_skill",
        "join_date",
        "leave_date",
        "created_at",
        "updated_at",
    )
    list_per_page = 100


class EducationTypeAdmin(admin.ModelAdmin):
    list_per_page = 100


admin.site.register(Country, CountryAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(University, UniversityAdmin)
admin.site.register(KeySkill, KeySkillAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Education, EducationAdmin)
admin.site.register(Experience, ExperienceAdmin)
admin.site.register(EducationType, EducationTypeAdmin)
admin.site.register(Industry)
