from datetime import timedelta

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.humanize.templatetags import humanize
from django.db.models import Q
from django.utils.encoding import (
    DjangoUnicodeDecodeError,
    force_str,
    smart_bytes,
    smart_str,
)
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from hashids import Hashids
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from company.models import Company, Department
from company.serializers import (
    CompanyIdSerializer,
    CompanySerializer,
    DepartmentSerializer,
)
from form.models import AppliedPosition, FormData
from primary_data import serializers as primary_data_serializer
from primary_data.models import Address, Country, Education, KeySkill
from role import serializers as role_serializer
from role.serializers import RoleSerializer
from scorecard.models import Attribute, Competency, PositionScoreCard

# from scorecard.serializers import AttributeSerializer
from user.models import ActivityLogs, ImportEmployeeFile

from .models import Media, Profile, Role, Team, User
from .utils import get_members_form_data


def encrypt(message):
    key = settings.ENCRY_KEY
    cypher = Hashids(salt=key, min_length=8)
    return cypher.encode(message)


def decrypt(message):
    key = settings.ENCRY_KEY
    cypher = Hashids(salt=key, min_length=8)
    return cypher.decode(message)[0]


class MediaSerializer(serializers.ModelSerializer):
    """
    MediaSerializer class is created with Media Model and added
    all field from MediaSerializer Model
    """

    class Meta:
        model = Media
        fields = "__all__"


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    UserSerializer class is created with user Model and added
    all field from UserSerializer Model
    """

    class Meta:
        model = User
        fields = ["is_active"]


class UserSerializer(serializers.ModelSerializer):
    """
    UserSerializer class is created with user Model and added
    all field from UserSerializer Model
    """

    user_role = role_serializer.GetRoleSerializer(read_only=True)

    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {
            "password": {"write_only": True},
            "user_permissions": {"write_only": True},
            "email_otp": {"write_only": True},
            "username": {"write_only": True},
            "is_superuser": {"write_only": True},
            "is_staff": {"write_only": True},
            "groups": {"write_only": True},
        }


class BasicProfileSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = "__all__"

    def get_user(self, obj):
        user_obj = {}
        user_obj["full_name"] = obj.user.get_full_name()
        user_obj["first_name"] = obj.user.first_name
        return user_obj


class ProfileSerializer(serializers.ModelSerializer):
    """
    ProfileSerializer class is created with profile Model and added
    all field from GetProfileSerializer Model
    """

    user = UserSerializer(read_only=True)
    address = primary_data_serializer.GetAddressSerializer()
    profile_image = serializers.SerializerMethodField(read_only=True)
    skill = serializers.SerializerMethodField(read_only=True)
    e_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Profile
        extra_kwargs = {"skill": {"required": False}}

        fields = "__all__"

    def get_e_id(self, obj):
        return encrypt(obj.id)

    def get_profile_image(self, obj):
        try:
            media_obj = Media.objects.get(profile=obj, field_name="avatar")
            return media_obj.media_file.url
        except:
            return None

    def get_skill(self, obj):
        skill = []
        for i in obj.skill.all():
            skill.append(i.skill)
        return skill


# profile  serializer for the team
class CustomProfileSerializer(serializers.ModelSerializer):
    """
    This serializer is being used for the TeamGetSerializer
    to add specific data like new hires, open and pending position
    counts.
    """

    new_hires = serializers.SerializerMethodField(read_only=True)
    open_position = serializers.SerializerMethodField(read_only=True)
    pending_position = serializers.SerializerMethodField(read_only=True)
    user = UserSerializer(read_only=True)
    profile_image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Profile
        fields = "__all__"

    # teams_obj, created = Team.objects.get_or_create(manager=pro_obj)
    # members_fd_list = get_members_form_data(teams_obj, temp_form_data, [])
    # members_fd_obj = FormData.objects.filter(id__in=members_fd_list)
    # result_list = members_fd_obj | own_form_data
    # if status:
    #     result_list = result_list.filter(status=status)
    # form_data = sort_data(result_list, sort_field, sort_dir)
    def get_positions(self, obj):
        own_form_data = FormData.objects.filter(Q(hiring_manager=obj.user.email) | Q(recruiter=obj.user.email)).filter(company=obj.user.user_company)
        temp_form_data = FormData.objects.filter(company=obj.user.user_company)
        teams_obj, created = Team.objects.get_or_create(manager=obj)
        members_fd_list = get_members_form_data(teams_obj, temp_form_data, [])
        members_fd_obj = FormData.objects.filter(id__in=members_fd_list)
        result_list = members_fd_obj | own_form_data
        return result_list

    def get_new_hires(self, obj):
        new_hires = 0
        result = self.get_positions(obj)
        for position in result.filter(status="closed"):
            hire_count = AppliedPosition.objects.filter(form_data=position, application_status="hired").count()
            new_hires += hire_count
        return new_hires

    def get_open_position(self, obj):
        result = self.get_positions(obj)
        return result.filter(status="active").count()

    def get_pending_position(self, obj):
        result = self.get_positions(obj)
        return result.filter(status="draft").count()

    def get_profile_image(self, obj):
        try:
            media_obj = Media.objects.get(profile=obj, field_name="avatar")
            return media_obj.media_file.url
        except:
            return None


class PositionScoreCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionScoreCard
        fields = "__all__"


class GetAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = "__all__"


class GetCompetencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Competency
        fields = "__all__"


class GetPositionScoreCardSerializer(serializers.ModelSerializer):
    attribute = GetAttributeSerializer()
    competency = GetCompetencySerializer()

    class Meta:
        model = PositionScoreCard
        fields = "__all__"


class PositionStageScoreCardSerializer(serializers.ModelSerializer):
    attribute = serializers.SerializerMethodField()

    class Meta:
        model = PositionScoreCard
        fields = "__all__"

    def get_attribute(self, obj):
        att_id = obj.attribute.id
        att_name = obj.attribute.attribute_name
        att_rating = obj.rating
        data = {"attribute_id": att_id, "attribute_name": att_name, "attribute_rating": att_rating}
        return data


class ProfileScoreCardSerializer(serializers.ModelSerializer):
    """
    ProfileSerializer class is created with profile Model and added
    all field from GetProfileSerializer Model
    """

    user = UserSerializer(read_only=True)
    id = serializers.SerializerMethodField()
    scorecard = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        extra_kwargs = {"skill": {"required": False}}

        fields = "__all__"

    def get_id(self, obj):
        return encrypt(obj.id)

    def get_scorecard(self, obj):
        candidate_id = self.context.get("candidate_id")
        position_id = self.context.get("position_id")
        position_stage_id = self.context.get("position_stage_id")
        # print(candidate_id, position_id, position_stage_id, obj.id)

        # position_scorecard = PositionScoreCard.objects.filter(
        #     position=position_id, applied_profiles=candidate_id, position_stage=position_stage_id, interviewer_profile=obj.id
        # )

        position_scorecard = PositionScoreCard.objects.filter(position=position_id, position_stage=position_stage_id, interviewer_profile=obj.id)
        # print(position_scorecard)
        position_scorecard = position_scorecard.prefetch_related()
        serializer = PositionStageScoreCardSerializer(position_scorecard, many=True)
        return serializer.data


# TODO: Code cleanup Pending
class GetProfileSerializer(serializers.ModelSerializer):
    """
    GetProfileSerializer class is created with profile Model and added
    all field from GetProfileSerializer Model
    """

    address = primary_data_serializer.GetAddressSerializer(read_only=True)
    skill = primary_data_serializer.KeySkillListSerializer(many=True, required=False, read_only=True)
    education = primary_data_serializer.GetEducationSerializer(many=True)
    user = UserSerializer(read_only=True)
    media = MediaSerializer(many=True, read_only=True)
    department = DepartmentSerializer()
    manager = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        extra_kwargs = {"skill": {"required": False}}

        fields = "__all__"

    def get_manager(self, obj):
        for i in Team.objects.all():
            if obj in i.members.all():
                return {"id": i.manager.id, "manager": i.manager.user.first_name}
        else:
            return {}


class GetCustomProfileSerializer(serializers.ModelSerializer):
    """
    GetProfileSerializer class is created with profile Model and added
    all field from GetProfileSerializer Model
    """

    address = primary_data_serializer.GetAddressSerializer(read_only=True)
    user = UserSerializer()
    skill = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    manager = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        extra_kwargs = {"skill": {"required": False}}

        fields = "__all__"

    def get_department(self, obj):
        if obj.department:
            return {"id": obj.department.id, "label": obj.department.department_name}
        else:
            return {}

    def get_manager(self, obj):
        for i in Team.objects.all():
            if obj in i.members.all():
                return {"id": i.manager.id, "label": i.manager.user.first_name}
        else:
            return {}

    def get_skill(self, obj):
        data = []
        for skill in obj.skill.all():
            data.append(skill.skill)
        return data


# TODO: Code cleanup Pending
class UpdateProfileProfileSerializer(serializers.ModelSerializer):
    """
    UpdateProfileProfileSerializer class is created with profile Model and added
    all field from UpdateProfileProfileSerializer Model
    """

    address = primary_data_serializer.AddressSerializer(read_only=False)
    education = primary_data_serializer.EducationSerializer(many=True, read_only=True)

    # education = serializers.ListField(child=serializers.CharField())
    # user = serializers.IntegerField(read_only=True)

    class Meta:
        model = Profile
        # extra_kwargs = {"skill": {"required": False}}

        # fields = "__all__"
        exclude = ("user", "user_refereed_by")

    def update(self, instance, validated_data):
        # nested_serializer_e = self.fields["education"]
        # nested_instance_e = instance.education
        # education_data = validated_data.pop("education")

        # print("-----------------------")
        # print(education_data)
        # for perm in education_data:
        #     print(perm)
        #     print(perm["id"])
        # print("-----------------------")

        nested_serializer = self.fields["address"]
        nested_instance = instance.address
        address_data = validated_data.pop("address")

        instance = super(UpdateProfileProfileSerializer, self).update(instance, validated_data)

        try:
            nested_serializer.update(nested_instance, address_data)
        except:
            raise serializers.ValidationError("address instance not present in over database")

        # nested_serializer_e.update(nested_instance_e, education_data)

        return instance


class GetUpdateProfileProfileSerializer(serializers.ModelSerializer):
    """
    UpdateProfileProfileSerializer class is created with profile Model and added
    all field from UpdateProfileProfileSerializer Model
    """

    address = primary_data_serializer.AddressSerializer(read_only=False)
    education = primary_data_serializer.EducationSerializer(many=True, read_only=True)
    department = DepartmentSerializer()

    # education = serializers.ListField(child=serializers.CharField())
    # user = serializers.IntegerField(read_only=True)

    class Meta:
        model = Profile
        # extra_kwargs = {"skill": {"required": False}}

        fields = "__all__"


class CandidateLoginDetailSerializer(serializers.ModelSerializer):
    """
    CandidateLoginDetailSerializer class is created with user Model and added
    all field from CandidateLoginDetailSerializer Model
    """

    user_role = role_serializer.RoleSerializer(read_only=True)
    profile_id = serializers.SerializerMethodField()
    # profile = ProfileSerializer()

    def get_profile_id(self, obj):
        return encrypt(obj.profile.id)

    class Meta(object):
        model = User
        fields = "__all__"
        extra_kwargs = {
            "password": {"write_only": True},
            "groups": {"write_only": True},
            "user_permissions": {"write_only": True},
        }


class CandidateSignUpSerializer(serializers.ModelSerializer):
    """
    CandidateSignUpSerializer class is created with user Model and added
    email,firstname,middlename and etc field from CandidateSignUpSerializer Model
    """

    email = serializers.EmailField(min_length=2)
    first_name = serializers.CharField(max_length=250, required=True)
    middle_name = serializers.CharField(max_length=250, required=False)
    last_name = serializers.CharField(max_length=250, required=False)
    phone_no = serializers.CharField(max_length=20, required=True)
    password = serializers.CharField(max_length=50, required=False)
    user_role = serializers.IntegerField(required=True)
    user_company = serializers.CharField(max_length=50, required=True)
    countrycode = serializers.CharField(max_length=50, required=False)

    class Meta(object):
        model = User
        fields = (
            "email",
            "first_name",
            "middle_name",
            "last_name",
            "phone_no",
            "password",
            "user_role",
            "email_otp",
            "user_company",
            "username",
            "countrycode",
        )

        # write_only not return password field in serialized data
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def validate_user_company(self, value):
        try:
            company_obj = Company.objects.get(url_domain__exact=value)
            return company_obj
        except:
            raise serializers.ValidationError("company not present in over database")

    def validate_user_role(self, value):
        # role object check
        try:
            role_obj = Role.objects.get(id=value)
        except:
            try:
                role_obj = Role.objects.get(slug="candidate")
            except:
                role_obj = Role.objects.create(name="candidate")

        return role_obj

    def create(self, validated_data):
        phone_no = validated_data.pop("phone_no")
        country_code = validated_data.pop("countrycode", None)
        try:
            country = Country.objects.get(phone_code__in=[country_code, country_code.lstrip("+")])
        except:
            country = None
        user_obj = User.objects.create(**validated_data)
        print(user_obj.user_role.name)
        if user_obj.user_role.name != "guest":
            user_obj.set_password(validated_data["password"])
        user_obj.is_active = False
        user_obj.is_superuser = False
        user_obj.is_staff = False
        user_obj.save()

        address_obj = Address.objects.create(country=country)
        address_obj.save()
        profile_obj = Profile.objects.create(user=user_obj, phone_no=phone_no, address=address_obj)
        profile_obj.save()
        return user_obj


# class ResetPasswordEmailRequestSerializer(serializers.Serializer):
#     email = serializers.EmailField(min_length=2)
#     redirect_url = serializers.CharField(max_length=500, required=False)

#     class Meta:
#         fields = ["email"]


class SetNewPasswordSerializer(serializers.Serializer):
    """
    SetNewPasswordSerializer class is created with user Model and added
    password,token,uidb64 fields from SetNewPasswordSerializer Model
    """

    password = serializers.CharField(min_length=6, max_length=68, write_only=True)
    token = serializers.CharField(min_length=1, write_only=True)
    uidb64 = serializers.CharField(min_length=1, write_only=True)

    class Meta:
        fields = ["password", "token", "uidb64"]

    def validate(self, attrs):
        try:
            password = attrs.get("password")
            token = attrs.get("token")
            uidb64 = attrs.get("uidb64")

            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise AuthenticationFailed("The reset link is invalid", 401)

            user.set_password(password)
            user.save()

            return user
        except Exception as e:
            raise AuthenticationFailed("The reset link is invalid", 401)
        return super().validate(attrs)


class LogoutSerializer(serializers.Serializer):
    """
    LogoutSerializer class is created with user Model and added
    functions and save the logout serializer
    """

    refresh = serializers.CharField()

    default_error_message = {"bad_token": ("Token is expired or invalid")}

    def validate(self, attrs):
        self.token = attrs["refresh"]
        return attrs

    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()

        except TokenError:
            raise serializers.ValidationError("invalid token")


class GetUserSerializer(serializers.ModelSerializer):
    """
    GetUserSerializer class is created with user Model and added
    all fields from the GetUserSerializer
    """

    profile = GetCustomProfileSerializer()
    user_role = RoleSerializer()

    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {
            "password": {"write_only": True},
            "user_permissions": {"write_only": True},
            "email_otp": {"write_only": True},
            "username": {"write_only": True},
            "is_superuser": {"write_only": True},
            "is_staff": {"write_only": True},
            "groups": {"write_only": True},
        }


class OpGetUserSerializer(serializers.ModelSerializer):
    """
    GetUserSerializer class is created with user Model and added
    all fields from the GetUserSerializer
    """

    profile = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "profile"]
        read_only_field = fields

    def get_profile(self, obj):
        data = {}
        try:
            data["id"] = obj.profile.id
            data["e_id"] = encrypt(obj.profile.id)
            data["first_name"] = obj.first_name
            data["middle_name"] = obj.middle_name
            data["last_name"] = obj.last_name
        except:
            pass
        return data


class CandidateProfileSerializer(serializers.ModelSerializer):
    """
    CandidateSerializer class is created with user Model for listing all the candidates
    """

    address = primary_data_serializer.GetAddressSerializer(read_only=True)
    skill = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        extra_kwargs = {"skill": {"required": False}}

        fields = "__all__"

    def get_skill(self, obj):
        data = []
        for skill in obj.skill.all():
            data.append(skill.skill)
        return data


class ExtendedGetUserSerializer(serializers.ModelSerializer):
    """
    GetUserSerializer class is created with user Model and added
    all fields from the GetUserSerializer
    """

    candidate_name = serializers.SerializerMethodField(read_only=True)
    applied_profile = serializers.SerializerMethodField(read_only=True)
    resume = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {
            "password": {"write_only": True},
            "user_permissions": {"write_only": True},
            "email_otp": {"write_only": True},
            "username": {"write_only": True},
            "is_superuser": {"write_only": True},
            "is_staff": {"write_only": True},
            "groups": {"write_only": True},
        }

    def get_candidate_name(self, obj):
        return obj.get_full_name()

    def get_applied_profile(self, obj):
        data = CandidateProfileSerializer(obj.profile).data
        data["education_details"] = primary_data_serializer.EducationSerializer(Education.objects.filter(profile=obj.profile), many=True).data
        # data["company_details"] = CompanySerializer(obj.user_company).data
        return data

    def get_resume(self, obj):
        media_objs = Media.objects.filter(profile=obj.profile, field_name="upload_resume")
        if media_objs:
            media_serializer = MediaSerializer(media_objs[0])
            return media_serializer.data
        else:
            return {}


class GetHMAndRecruiterSerializer(serializers.ModelSerializer):
    """
    GetUserSerializer class is created with user Model and added
    all fields from the GetUserSerializer
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("email", "id", "profile", "full_name")
        extra_kwargs = {
            "password": {"write_only": True},
            "user_permissions": {"write_only": True},
            "email_otp": {"write_only": True},
            "username": {"write_only": True},
            "is_superuser": {"write_only": True},
            "is_staff": {"write_only": True},
            "groups": {"write_only": True},
        }

    def get_full_name(self, obj):
        return obj.get_full_name()


class CsvUserSerializer(serializers.ModelSerializer):
    """
    GetUserSerializer class is created with user Model and added
    all fields from the GetUserSerializer
    """

    class Meta:
        model = User
        fields = ["username", "email"]


class ActivityLogsSerializer(serializers.ModelSerializer):
    """
    Activity Logs Serializer
    """

    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = ActivityLogs
        fields = "__all__"

    def get_time_ago(self, obj):
        updated_at = obj.updated_at + timedelta(minutes=23)
        return humanize.naturaltime(updated_at)


class ScorecardProfileSerializer(serializers.ModelSerializer):
    """
    Activity Logs Serializer
    """

    scorecard_details = serializers.SerializerMethodField()
    user = UserSerializer()

    class Meta:
        model = Profile
        fields = "__all__"

    def get_scorecard_details(self, obj):
        applied_position_obj = self.context.get("applied_position_obj")
        score_obj = PositionScoreCard.objects.filter(
            interviewer_profile=obj.id, position=applied_position_obj.form_data, applied_profiles=applied_position_obj.applied_profile
        )
        score_obj = score_obj.prefetch_related("attribute", "competency")
        return GetPositionScoreCardSerializer(score_obj, many=True).data


class TeamGetSerializer(serializers.ModelSerializer):
    manager = CustomProfileSerializer(read_only=True)
    members = CustomProfileSerializer(read_only=True, many=True)

    class Meta:
        model = Team
        fields = ("id", "manager", "members")


class TeamCreatUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ("members", "manager")

    def create(self, validated_data):
        members_list = validated_data.pop("members")
        team_obj = Team.objects.create(**validated_data)
        for member in members_list:
            team_obj.members.add(member)
        team_obj.save()

        return team_obj

    def update(self, instance, validated_data):
        if "members" in validated_data:
            members_list = validated_data.pop("members")
        else:
            members_list = []
        instance.name = validated_data.get("name", instance.name)
        instance.manager = validated_data.get("manager", instance.manager)
        if members_list:
            instance.members.clear()
            for member in members_list:
                instance.members.add(member)
        instance.save()

        return instance


class DemoSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "user_company")

    def create(self, validated_data):
        role = Role.objects.filter(name="superadmin")[0]
        validated_data["user_role"] = role
        validated_data["username"] = validated_data.get("email")
        user_obj = User.objects.create(**validated_data)
        return user_obj


class ImportEmployeeFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportEmployeeFile
        fields = "__all__"
