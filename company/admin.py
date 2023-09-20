from django.contrib import admin

from company.models import Company, Department, FeaturesEnabled, ServiceProviderCreds


# Register your models here.
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "company_name",
        "slug",
        "url_domain",
        "company_host",
        "company_owner",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    search_fields = ("company_name",)
    list_filter = ("is_active", "is_deleted")
    list_per_page = 50


# Register your models here.
admin.site.register(Company, CompanyAdmin)
admin.site.register(Department)
admin.site.register(ServiceProviderCreds)
admin.site.register(FeaturesEnabled)
