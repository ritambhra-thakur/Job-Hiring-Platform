from django.contrib import admin

from .models import Notifications, NotificationType


# Register your models here.
class NotificationsAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "title",
        "body",
        "is_read",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    search_fields = ("user","title","body",)
    list_filter = ("is_active", "is_deleted","is_read")
    list_per_page = 50


# Register your models here.
admin.site.register(Notifications, NotificationsAdmin)
admin.site.register(NotificationType)
