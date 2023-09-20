from django.contrib import admin

from .models import EmailTemplate, TemplateType


# Register your models here.
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "template_name",
    )


class TemplateTypeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "template_type_name",
    )


# Register your models here.
admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(TemplateType, TemplateTypeAdmin)
# admin.site.register(Currency, CurrencyAdmin)
