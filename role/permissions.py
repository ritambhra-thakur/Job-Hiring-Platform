from re import T

from django.contrib.auth.models import Permission
from django.db.models.query import QuerySet
from django.http import Http404
from rest_framework import exceptions, permissions, views

from role.models import Role, RolePermission


class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to admin users.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.user_role.slug == "superadmin")


class IsHiringManagerUser(permissions.BasePermission):
    """
    Allows access only to Hiring Manager users.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.user_role.slug == "hiring-manager")


class IsCandidateUser(permissions.BasePermission):
    """
    Allows access only to Candidate users.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.user_role.slug == "candidate")


class IsRecruiterUser(permissions.BasePermission):
    """
    Allows access only to Recruiter users.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.user_role.slug == "recruiter")


class IsEmployeeUser(permissions.BasePermission):
    """
    Allows access only to Employee users.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.user_role.slug == "employee")


class CUDModelPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        model = getattr(view, "queryset", None)
        model_name = (model.__dict__["model"].__name__).lower()
        if request.method == "GET":
            code_name = "view_" + str(model_name)
        elif request.method == "DELETE":
            code_name = "delete_" + str(model_name)
        elif request.method == "PUT":
            code_name = "change_" + str(model_name)
        elif request.method == "POST":
            code_name = "add_" + str(model_name)
        else:
            return False

        try:
            check_permission = Permission.objects.get(codename=code_name)

            permission = (
                Role.objects.filter(
                    pk=request.user.user_role.id,
                    permission__in=[check_permission],
                )
                .distinct()
                .count()
            )
            if permission > 0:
                return True
            else:
                return False

        except:
            return False


class RolePermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        print("-----------------------------------")
        print(self)
        print(request)
        print(request.user)
        print(request.user.user_role.id)

        role_queryset = Role.objects.get(id=request.user.user_role.id)
        print(role_queryset.__dict__)
        role_permission = RolePermission.objects.filter(role=role_queryset)
        print(role_permission)
        print(view)
        print("-----------------------------------")
        return True
