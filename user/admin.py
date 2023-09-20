from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from primary_data.models import Education, Experience
from role.permissions import permissions

from .form import EducationInlineForm, ExperienceInlineForm, ProfileForm
from .models import Media, Profile, User

# Register your models here.
# class permissionsAdmin(UserAdmin):
#     list_per_page = 50


class UserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Personal info",
            {"fields": ("middle_name",)},
        ),
        (
            "Email Fields",
            {
                "fields": (
                    "email_otp",
                    "email_verified",
                )
            },
        ),
        (
            "Role Fields",
            {"fields": ("user_role",)},
        ),
        (
            "Company Fields",
            {"fields": ("user_company",)},
        ),
    )
    list_display = (
        "id",
        "first_name",
        "middle_name",
        "last_name",
        "user_company",
        "user_role",
        "username",
        "email",
        "email_verified",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    search_fields = (
        "email",
        "username",
        "first_name",
        "middle_name",
        "last_name",
        "user_company__company_name",
    )
    list_filter = ("user_role", "user_company")
    list_per_page = 50
    raw_id_fields = ("user_role",)


class EducationInline(admin.TabularInline):
    model = Education
    form = EducationInlineForm
    extra = 1


class ExperienceInline(admin.TabularInline):
    model = Experience
    form = ExperienceInlineForm
    extra = 1


class MediaInline(admin.TabularInline):
    model = Media
    extra = 1


class ProfileAdmin(admin.ModelAdmin):
    form = ProfileForm

    list_display = (
        "id",
        "user",
        "phone_no",
        "phone_verified",
        "personal_url",
        "linked_url",
        "github_url",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    search_fields = ("user__first_name",)
    list_per_page = 50
    filter_horizontal = ("skill",)
    raw_id_fields = (
        "address",
        "user",
    )
    inlines = [
        EducationInline,
        MediaInline,
        ExperienceInline,
    ]


class MediaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "profile",
        "media_file",
        "media_file_name",
        "file_type",
        "is_active",
        "is_deleted",
        "can_delete",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)


# Register your models here.
admin.site.register(User, UserAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Media, MediaAdmin)

# admin.site.register(permissions)
