from django.contrib import admin

from stage.models import *


# Register your models here.
class PipelineAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pipeline_name",
        "slug",
        "company",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    list_per_page = 50


class StageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "stage_name",
        "company",
        "slug",
        "pipeline",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    list_per_page = 50


class PositionStageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "position",
        "stage",
        "sort_order",
        "company",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    list_per_page = 50



admin.site.register(Pipeline, PipelineAdmin)
admin.site.register(Stage, StageAdmin)
admin.site.register(PositionStage, PositionStageAdmin)
