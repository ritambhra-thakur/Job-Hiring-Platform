from django.contrib import admin

# Register your models here.
from .models import JobSites


class JobSitesAdmin(admin.ModelAdmin):
    list_per_page = 50
    list_display = ("id", "job_site")
    search_fields = (
        "id",
        "job_site",
    )


admin.site.register(JobSites, JobSitesAdmin)
