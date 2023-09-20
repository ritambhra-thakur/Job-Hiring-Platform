from django.contrib import admin

from .models import Access, Role, RoleList, RolePermission

# Register your models here.
# class RolePermissionsInline(admin.TabularInline):
#     model = RolePermissions
#     extra = 1
#     raw_id_fields = ("permission",)


class UserPermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1


class RoleAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "company",
        "slug",
        "can_delete",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    search_fields = ("name",)
    list_filter = ("is_active", "is_deleted", "company")
    list_per_page = 50
    filter_horizontal = ("permission",)
    inlines = [
        UserPermissionInline,
    ]


class AccessAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "action_name",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    list_per_page = 50


class RolePermissionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "role",
        "access",
        "read",
        "create",
        "update",
        "delete",
    )
    list_display_links = ("id",)
    list_per_page = 50


class RoleListAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "role_name",
        "created_at",
        "updated_at",
    )
    list_display_links = ("id",)
    list_per_page = 50


admin.site.register(Role, RoleAdmin)
admin.site.register(Access, AccessAdmin)
admin.site.register(RolePermission, RolePermissionAdmin)
admin.site.register(RoleList, RoleListAdmin)
