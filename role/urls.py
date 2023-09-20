from django.urls import path

from role import views

app_name = "role"

urlpatterns = [
    path("api/v1/list/", views.GetAllRole.as_view()),
    path("api/v1/op-list/", views.GetAllOpRole.as_view()),
    path("api/v1/list/Dummy/", views.GetAllDummyRole.as_view()),
    path("api/v1/get/<int:pk>/", views.GetRole.as_view()),
    path("api/v1/create/", views.CreateRole.as_view()),
    path("api/v1/update/<int:pk>/", views.UpdateRole.as_view()),
    path("api/v1/update-role-access/<int:pk>/", views.UpdateRoleAndAccess.as_view()),
    path("api/v1/delete/<int:pk>/", views.DeleteRole.as_view()),
    path("api/v1/list-permission/", views.GetAllPermissionViews.as_view()),
    # Access
    path("access/api/v1/list/", views.GetAllAccess.as_view()),
    path("access/api/v1/get/<int:pk>/", views.GetAccess.as_view()),
    path("access/api/v1/create/", views.CreateAccess.as_view()),
    path("access/api/v1/update/<int:pk>/", views.UpdateAccess.as_view()),
    path("access/api/v1/delete/<int:pk>/", views.DeleteAccess.as_view()),
    # Permission
    path("role_permission/api/v1/list/", views.GetAllRolePermission.as_view()),
    path("role_permission/api/v1/get/<int:pk>/", views.GetRolePermission.as_view()),
    path("role_permission/api/v1/create/", views.CreateRolePermission.as_view()),
    path("role_permission/api/v1/update/<int:pk>/", views.UpdateRolePermission.as_view()),
    path("role_permission/api/v1/delete/<int:pk>/", views.DeleteRolePermission.as_view()),
    # role_list
    path("role_list/api/v1/list/", views.GetAllRoleList.as_view()),
    # CSV Export
    path(
        "api/v1/export/csv/<str:company_id>/",
        views.RoleCSVExport.as_view(),
    ),
]
