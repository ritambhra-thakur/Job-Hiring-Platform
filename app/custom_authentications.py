from rest_framework.permissions import BasePermission


class CustomAuthenticated(BasePermission):
    """
    Allows access only to authenticated users for GET Method.
    """

    # def has_permission(self, request, view):
    #     return bool(request.user and request.user.is_authenticated)
    def has_permission(self, request, view):
        if request.method.lower() in ("update", "destroy", "delete", "post", "put"):
            return request.user.is_authenticated
        return True
