from django.contrib import admin

from scorecard.models import *

# # Register your models here.
# # class CategoryAdmin(admin.ModelAdmin):
# #     list_display = (
# #         "id",
# #         "category_name",
# #         "company",
# #         "slug",
# #         "is_active",
# #         "is_deleted",
# #         "created_at",
# #         "updated_at",
# #     )
# #     list_per_page = 100


class AttributeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "attribute_name",
        "company",
        "slug",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_per_page = 100


class CompetencyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "competency",
        "company",
        "slug",
        "created_at",
        "updated_at",
    )
    list_per_page = 100
    filter_horizontal = ("attribute",)


class PositionCompetencyAndAttributeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "position",
        "competency",
        "created_at",
        "updated_at",
    )
    list_per_page = 100
    filter_horizontal = ("attribute",)


class PositionScoreCardAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "position",
        "interviewer_profile",
        "applied_profiles",
        "competency",
        "attribute",
        "rating",
        "comment",
    )
    list_per_page = 100


OverAllRatingDashboard


class OverAllRatingDashboardAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "applied_position",
        "interviewer_id",
        "candidate_id",
        "created_at",
        "updated_at",
    )
    list_per_page = 100


# # class ScoreCardAdmin(admin.ModelAdmin):
# #     list_display = (
# #         "id",
# #         "competency",
# #         "attribute",
# #         "rating",
# #         "position",
# #         "company",
# #         "slug",
# #         "created_at",
# #         "updated_at",
# #     )
# #     # filter_horizontal = ("attribute_and_competency",)

# #     list_per_page = 100


# # class AttributeAndCompetencyAdmin(admin.ModelAdmin):
# # list_display = (
# #     "id",
# #     "attribute",
# #     "waitage",
# #     "competency",
# #     "company",
# #     "slug",
# # )

# # list_per_page = 100


class PositionAttributeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "slug",
        "position",
        "company",
        "created_at",
        "updated_at",
    )

    list_per_page = 100


# # admin.site.register(Category, CategoryAdmin)
admin.site.register(Attribute, AttributeAdmin)
admin.site.register(Competency, CompetencyAdmin)
admin.site.register(PositionCompetencyAndAttribute, PositionCompetencyAndAttributeAdmin)
admin.site.register(PositionScoreCard, PositionScoreCardAdmin)
# # admin.site.register(ScoreCard, ScoreCardAdmin)
