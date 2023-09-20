from django.contrib import admin

from .models import (
    AppliedPosition,
    CustomQuestion,
    Field,
    FieldChoice,
    FieldType,
    Form,
    FormData,
    JobCategory,
    JobLocation,
    OfferApproval,
    OfferLetter,
    OfferLetterTemplate,
    PositionAlert,
    PositionApproval,
    Reason,
    ReasonType,
    RecentViewJob,
    Reminder,
    SavedPosition,
)


# Register your models here.
class FieldInline(admin.TabularInline):
    model = Field
    extra = 1


class FormAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "form_name",
        "company",
        "description",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    inlines = [
        FieldInline,
    ]


class FieldTypeAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "field_type",
    )


class FieldAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "field_name",
        "field_type",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)


class FieldChoiceAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "choice_key",
        "choice_value",
        "field",
        "created_at",
        "updated_at",
    )


class FormDataAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "form",
        "company",
        "status",
        "candidate_visibility",
        "candidate_visibility_updated_at",
        "employee_visibility",
        "employee_visibility_updated_at",
        "is_cloned",
        "cloned_from_id",
        "created_by_profile",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("form",)


class PositionApprovalAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "slug",
        "position",
        "company",
        "profile",
        "is_approve",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("position",)


class OfferApprovalAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "slug",
        "position",
        "company",
        "profile",
        "is_approve",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("position",)


class JobCategoryAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "job_category",
        "company",
        "created_at",
        "updated_at",
    )


class JobLocationAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "country",
        "company",
        "created_at",
        "updated_at",
    )


class RecentViewJobAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "form_data",
        "profile",
        "company",
        "created_at",
        "updated_at",
    )


class SavedPositionAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "form_data",
        "profile",
        "company",
        "created_at",
        "updated_at",
    )


class PositionAlertAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "profile",
        "company",
        "created_at",
        "updated_at",
    )


class AppliedPositionAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = (
        "id",
        "form_data",
        "company",
        "applied_profile",
        "created_at",
        "updated_at",
    )


class ReasonAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "type",
        "reason",
        "company",
        "created_at",
        "updated_at",
    )
    search_fields = ("id", "reason", "type")
    list_per_page = 50


class ReasonTypeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reason_name",
        "created_at",
        "updated_at",
    )
    search_fields = ("reason_name",)
    list_per_page = 50


admin.site.register(Form, FormAdmin)
admin.site.register(Field, FieldAdmin)
admin.site.register(FieldType, FieldTypeAdmin)
admin.site.register(FieldChoice, FieldChoiceAdmin)
admin.site.register(FormData, FormDataAdmin)
admin.site.register(PositionApproval, PositionApprovalAdmin)
admin.site.register(OfferApproval, OfferApprovalAdmin)
admin.site.register(JobCategory, JobCategoryAdmin)
admin.site.register(JobLocation, JobLocationAdmin)
admin.site.register(RecentViewJob, RecentViewJobAdmin)
admin.site.register(SavedPosition, SavedPositionAdmin)
admin.site.register(PositionAlert, PositionAlertAdmin)
admin.site.register(AppliedPosition, AppliedPositionAdmin)
admin.site.register(Reason, ReasonAdmin)
admin.site.register(ReasonType, ReasonTypeAdmin)
admin.site.register(OfferLetterTemplate)
admin.site.register(OfferLetter)
admin.site.register(Reminder)
admin.site.register(CustomQuestion)
