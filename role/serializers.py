from django.contrib.auth.models import Permission
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from company.models import Company
from role.models import Access, Role, RoleList, RolePermission
from role.permissions import permissions


# TODO: Code clean up Pending
class PermissionSerializer(serializers.ModelSerializer):
    """
    PermissionSerializer class is created with Permission Model and added
    id, name field from PermissionSerializer Model
    """

    class Meta(object):
        model = Permission
        fields = ("id", "name")


class GetRoleSerializer(serializers.ModelSerializer):
    """
    GetRoleSerializer class is created with Role Model and added
    id,name,slug,company field from GetRoleSerializer Model
    """

    class Meta:
        model = Role
        fields = ["id", "name", "slug", "company"]


class RoleCreateUpdateSerializer(serializers.ModelSerializer):
    """
    RoleCreateUpdateSerializer class is created with Role Model and added
    all field from RoleCreateUpdateSerializer Model
    """

    # permissions = serializers.ListField(child=serializers.CharField())
    name = serializers.CharField(required=False)
    # company_domain = serializers.CharField(
    #     required=True, source="company.url_domain"
    # )
    # """
    # it is used to change the behaviour of model with all fields and validators is used for
    # validation has create update
    # """
    class Meta(object):
        model = Role
        # fields = ("id", "name", "permission", "company_domain")
        fields = "__all__"
        validators = [UniqueTogetherValidator(queryset=Role.objects.all(), fields=["name", "company"])]

    # def validate_company_domain(self, value):
    #     try:
    #         company_obj = Company.objects.get(url_domain__exact=value)
    #         return company_obj
    #     except:
    #         raise serializers.ValidationError(
    #             "company not present in over database"
    #         )

    # validation of meta class with name and lowercase

    def validate_name(self, value):
        return value.lower()

    # def validate(self, attrs):
    #     print(attrs["name"])
    #     name = attrs["name"]
    #     company_domain = attrs["company_domain"]
    #     print(name)
    #     print(company_domain)
    #     role = Role.objects.filter(
    #         name=name,
    #         company=company_domain,
    #     ).exists()
    #     if role:
    #         return ResponseBadRequest(
    #             {
    #                 "data": {
    #                     "role": ["present in database"],
    #                 },
    #                 "code": 400,
    #                 "message": "Serializer error",
    #             }
    #         )
    #     else:
    #         return attrs

    def create(self, validated_data):

        # company_domain = validated_data.pop("company_domain")
        if "permission" in validated_data:
            permission = validated_data.pop("permission")

        print(validated_data)
        role_obj = Role.objects.create(**validated_data)
        # role_obj.company = company_domain
        role_obj.save()

        for perm in permission:
            print(perm)
            role_obj.permission.add(perm)

        return role_obj

    def update(self, instance, validated_data):

        if "permission" in validated_data:
            permission = validated_data.pop("permission")

        instance.name = validated_data.get("name", instance.name)
        instance.save()

        instance.permission.clear()

        for perm in permission:
            print(perm)
            instance.permission.add(perm)

        return instance


# class PermissionDetailSerializer(serializers.ModelSerializer):
#     """
#     This is for Retrieving full data
#     """

#     permission = serializers.SerializerMethodField()

#     def get_permission(self, obj):
#         try:
#             permission_check = Permission.objects.get(id=obj.permission.id)
#             return {"id": permission_check.id, "name": permission_check.name}
#         except:
#             return None

#     class Meta(object):
#         model = RolePermissions
#         fields = ("permission",)


# class RoleDetailSerializer(serializers.ModelSerializer):
#     permissions = serializers.SerializerMethodField()

#     def get_permissions(self, obj):
#         permissions = []
#         role_permission = RolePermissions.objects.filter(role=obj.id)
#         if len(role_permission) == 0:
#             return permissions
#         else:
#             for obj in role_permission:
#                 permission_check = Permission.objects.get(id=obj.permission.id)
#                 data = {
#                     "id": permission_check.id,
#                     "name": permission_check.name,
#                 }
#                 permissions.append(data)
#             return permissions

#     class Meta(object):
#         model = Role
#         fields = (
#             "id",
#             "name",
#             "permissions",
#         )


class AccessSerializer(serializers.ModelSerializer):
    """
    AccessSerializer class is created with Access Model and added
    all field from Access Model
    """

    class Meta:
        model = Access
        fields = "__all__"


class RolePermissionSerializer(serializers.ModelSerializer):
    """
    RolePermissionSerializer class is created with RolePermission Model and added
    all field from RolePermission Model
    """

    class Meta:
        model = RolePermission
        fields = "__all__"


class RolePermissionListSerializer(serializers.ModelSerializer):
    """
    RolePermissionSerializer class is created with RolePermission Model and added
    all field from RolePermission Model
    """

    access = AccessSerializer(read_only=True)

    class Meta:
        model = RolePermission
        fields = "__all__"


class RoleSerializer(serializers.ModelSerializer):
    """
    RoleSerializer class is created with Role Model and added
    all field from RoleSerializer Model
    """

    # TODO: remove default django permission and use RolePermission model for permission
    # permission = PermissionSerializer(many=True)
    permission_role = RolePermissionListSerializer(many=True)

    class Meta:
        model = Role
        fields = "__all__"


class RoleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleList
        fields = "__all__"


