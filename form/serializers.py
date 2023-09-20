# from django.contrib.auth.models import Permission
import datetime
from asyncore import read
from email.mime import application
from pickletools import read_long1

from django.conf import settings
from django.db.models import Avg
from msrest import Serializer
from rest_framework import serializers

import form.models as FormModel
import primary_data.serializers as PrimaryDataSerializer
from app.util import encryption
from company.models import Company
from scorecard.models import OverAllRatingDashboard, PositionScoreCard
from stage.models import PositionStage, Stage
from url_shortener import utils as url_shortner_utils
from url_shortener.models import ShortURL
from user.models import Media, Profile, User
from user.serializers import (
    BasicProfileSerializer,
    GetCustomProfileSerializer,
    GetProfileSerializer,
    MediaSerializer,
    PositionScoreCardSerializer,
    ProfileSerializer,
    ScorecardProfileSerializer,
)
from app.encryption import encrypt, decrypt
from .models import (
    Answer,
    AppliedPosition,
    CareerTemplate,
    CustomQuestion,
    OfferApproval,
    OfferLetter,
    PositionApproval,
    Reason,
    ReasonType,
    Reminder,
    UnapprovedAppliedPosition,
    UserSelectedField,
)


# TODO: Code clean up Pending
class FormSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.Form
        fields = "__all__"


class FieldTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.FieldType
        fields = "__all__"


class FieldSerializer(serializers.ModelSerializer):
    form_choices = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FormModel.Field
        fields = [
            "form_choices",
            "id",
            "description",
            "field_block",
            "field_name",
            "field_type",
            "form",
            "slug",
            "sort_order",
            "is_mandatory",
            "company",
        ]

    def get_form_choices(self, obj):
        data = []
        for choice in FormModel.FieldChoice.objects.filter(field=obj):
            temp_dict = {}
            temp_dict["choice_key"] = choice.choice_key
            temp_dict["choice_value"] = choice.choice_value
            temp_dict["sort_order"] = choice.sort_order
            data.append(temp_dict)
        return data


class FieldChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.FieldChoice
        fields = "__all__"


class FormDataSerializer(serializers.ModelSerializer):
    hiring_manager_name = serializers.SerializerMethodField(read_only=True)
    recruiter_name = serializers.SerializerMethodField(read_only=True)
    applied_candidates_count = serializers.SerializerMethodField()

    class Meta:
        model = FormModel.FormData
        fields = "__all__"

    def get_hiring_manager_name(self, obj):
        try:
            user_obj = User.objects.get(email__iexact=obj.hiring_manager, user_company=obj.company)
            return user_obj.get_full_name()
        except:
            return obj.hiring_manager

    def get_recruiter_name(self, obj):
        try:
            user_obj = User.objects.get(email__iexact=obj.recruiter, user_company=obj.company)
            return user_obj.get_full_name()
        except:
            return obj.recruiter

    def get_applied_candidates_count(self, obj):
        app_obj = AppliedPosition.objects.filter(form_data=obj.id)
        return app_obj.count()


class GetFormDataSerializer(serializers.ModelSerializer):
    created_by_profile = GetCustomProfileSerializer(read_only=True)
    hiring_manager_name = serializers.SerializerMethodField(read_only=True)
    recruiter_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FormModel.FormData
        fields = "__all__"

    def get_hiring_manager_name(self, obj):
        try:
            user_obj = User.objects.get(email__iexact=obj.hiring_manager, user_company=obj.company)
            return user_obj.get_full_name()
        except:
            return obj.hiring_manager

    def get_recruiter_name(self, obj):
        try:
            user_obj = User.objects.get(email__iexact=obj.recruiter, user_company=obj.company)
            return user_obj.get_full_name()
        except:
            return obj.recruiter


class PositionApprovalSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = FormModel.PositionApproval
        fields = "__all__"


class CreatePositionApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.PositionApproval
        fields = "__all__"


class OfferApprovalSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = FormModel.OfferApproval
        fields = "__all__"


class FormDataListSerializer(serializers.ModelSerializer):
    created_by_profile = ProfileSerializer(read_only=True)
    is_saved = serializers.SerializerMethodField(read_only=True)
    is_applied = serializers.SerializerMethodField(read_only=True)
    applied_candidates_count = serializers.SerializerMethodField()
    job_link = serializers.SerializerMethodField()
    position_approvals = PositionApprovalSerializer(many=True)
    hiring_manager_name = serializers.SerializerMethodField(read_only=True)
    recruiter_name = serializers.SerializerMethodField(read_only=True)
    candidate_visibility_link = serializers.SerializerMethodField(read_only=True)
    employee_visibility_link = serializers.SerializerMethodField(read_only=True)
    days_in_status = serializers.SerializerMethodField(read_only=True)
    hire_details = serializers.SerializerMethodField(read_only=True)
    sposition_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FormModel.FormData
        fields = "__all__"

    def to_representation(self, obj):
        response = super().to_representation(obj)
        response["position_approvals"] = sorted(response["position_approvals"], key=lambda x: x["sort_order"])
        return response

    def get_sposition_id(self, obj):
        return obj.show_id

    def get_hire_details(self, obj):
        if obj.status in ["close", "closed"]:
            hire_obj = AppliedPosition.objects.filter(form_data=obj, application_status="hired")
            if hire_obj:
                offer_obj = OfferLetter.objects.filter(offered_to=hire_obj[0])
                if offer_obj:
                    return {
                        "candidate_name": offer_obj[0].offered_to.applied_profile.user.get_full_name(),
                        "start_date": str(offer_obj[0].start_date),
                    }
        return {}

    def get_candidate_visibility_link(self, obj):
        if obj.candidate_visibility:
            domain_name = settings.DOMAIN_NAME
            if obj.company.url_domain == "localhost":
                complete_url = "http://localhost:3000/guest/search-job-description/{}/".format(obj.id)
            else:
                complete_url = "https://{}.{}/guest/search-job-description/{}/".format(obj.company.url_domain, domain_name, obj.id)
            try:
                short_url_obj = ShortURL.objects.filter(long_url=complete_url, internal=False).last()
                return short_url_obj.short_url
            except Exception as e:
                print(e)
                return "No Url. Create first"
                # short_url_tag = url_shortner_utils.short_url()
                # short_url = "{}.{}/job/{}".format(obj.company.url_domain, domain_name, short_url_tag)
                # short_url_obj = ShortURL.objects.create(long_url=complete_url, short_url=short_url)
                # return short_url_obj.short_url
        else:
            return None

    def get_days_in_status(self, obj):
        data = {"active": 0, "hold": 0, "closed": 0, "canceled": 0, "draft": 0, None: 0}
        last_status = None
        for status in obj.history:
            if last_status:
                last_dt = datetime.datetime.strptime(last_status["date"].split()[0], "%Y-%m-%d")
                curr_dt = datetime.datetime.strptime(status["date"], "%Y-%m-%d")
                diff = curr_dt - last_dt
                data[last_status["status"]] += diff.days
            last_status = status
        else:
            diff = datetime.datetime.now().date() - obj.updated_at.date()
            data[obj.status] += diff.days
        # if last_status and last_status["status"]:
        #     last_dt = datetime.datetime.strptime(last_status["date"].split()[0], "%Y-%m-%d")
        #     diff = datetime.datetime.now() - last_dt
        #     data[last_status["status"]] += diff.days
        return data

    def get_employee_visibility_link(self, obj):
        if obj.employee_visibility:
            domain_name = settings.DOMAIN_NAME
            if obj.company.url_domain in "localhost":
                complete_url = "http://localhost:3000/guest/search-job-description/{}/".format(obj.id)
            else:
                complete_url = "https://{}.{}/internal/internal-search-job-description/{}/".format(obj.company.url_domain, domain_name, obj.id)
            try:
                short_url_obj = ShortURL.objects.filter(long_url=complete_url, internal=True).last()
                return short_url_obj.short_url
            except Exception as e:
                print(e)
                return "No Url. Create first"
                # short_url_tag = url_shortner_utils.short_url()
                # short_url = "{}.{}/job/{}".format(obj.company.url_domain, domain_name, short_url_tag)
                # short_url_obj = ShortURL.objects.create(long_url=complete_url, short_url=short_url)
                # return short_url_obj.short_url
        else:
            return None

    def get_is_saved(self, obj):
        obj_dict = {"is_saved": False}
        if str(self.context["request"].user) != "AnonymousUser":
            queryset_object = FormModel.SavedPosition.objects.filter(form_data=obj.id, profile=self.context["request"].user.profile.id)
            if queryset_object:
                obj_dict["is_saved"] = True
                obj_dict["saved_position_id"] = int(queryset_object[0].id)
        return obj_dict

    def get_is_applied(self, obj):
        obj_dict = {"is_applied": False}
        if str(self.context["request"].user) != "AnonymousUser":
            queryset_object = FormModel.AppliedPosition.objects.filter(form_data=obj.id, applied_profile=self.context["request"].user.profile.id)

            if queryset_object:
                obj_dict["is_applied"] = True
                obj_dict["is_applied_id"] = int(queryset_object[0].id)

        return obj_dict

    def get_applied_candidates_count(self, obj):
        app_obj = AppliedPosition.objects.filter(form_data=obj.id)
        return app_obj.count()

    def get_job_link(self, obj):
        try:
            res = "https://{}.{}/guest/search-job-description/{}".format(obj.company.url_domain, settings.DOMAIN_NAME, obj.id)
            return res
        except:
            return None

    def get_hiring_manager_name(self, obj):
        try:
            user_obj = User.objects.get(email__iexact=obj.hiring_manager, user_company=obj.company)
            return user_obj.get_full_name()
        except:
            return obj.hiring_manager

    def get_recruiter_name(self, obj):
        try:
            user_obj = User.objects.get(email__iexact=obj.recruiter, user_company=obj.company)
            return user_obj.get_full_name()
        except Exception as e:
            print(e, obj.id)
            return obj.recruiter


class GetPositionApprovalsSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = FormModel.PositionApproval
        fields = "__all__"


class PositionApprovalListSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    position = GetFormDataSerializer(read_only=True)
    position_approval_details = serializers.SerializerMethodField()
    reminder_status = serializers.SerializerMethodField()

    class Meta:
        model = FormModel.PositionApproval
        fields = "__all__"

    def get_position_approval_details(self, obj):
        position_obj = PositionApproval.objects.filter(position=obj.position.id).exclude(profile=obj.profile.id)
        serializer = GetPositionApprovalsSerializer(position_obj, many=True)
        return serializer.data

    def get_reminder_status(self, obj):
        reminder_count = Reminder.objects.filter(position=obj.id).count()
        return reminder_count

    # def get_reminder_status(self, obj):
    #     reminder_count = Reminder.objects.filter(position=obj.id).count()
    #     if reminder_count > 0:
    #         return True
    #     else:
    #         return False


class OfferApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.OfferApproval
        fields = "__all__"


class GetOfferApprovalsSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = FormModel.OfferApproval
        fields = "__all__"


class JobCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.JobCategory
        fields = "__all__"


class JobCategoryListSerializer(serializers.ModelSerializer):
    job_count = serializers.SerializerMethodField()
    applied_category_count = serializers.SerializerMethodField()

    class Meta:
        model = FormModel.JobCategory
        fields = "__all__"

    def get_job_count(self, obj):
        url_domain = self.context["request"].headers.get("domain")
        req = self.context.get("request")
        company_id = Company.objects.filter(url_domain=url_domain)[0].id
        data = self.context["request"].GET
        employee_visibility = data.get("employee_visibility")
        candidate_visibility = data.get("candidate_visibility")
        form_data_queryset = FormModel.FormData.objects.filter(form_data__job_category__id=obj.id, company=company_id, status="active")
        if candidate_visibility is not None:
            if candidate_visibility == "true":
                form_data_queryset = form_data_queryset.filter(candidate_visibility=True)
            else:
                form_data_queryset = form_data_queryset.filter(candidate_visibility=False)
        if employee_visibility is not None:
            if employee_visibility == "true":
                form_data_queryset = form_data_queryset.filter(employee_visibility=True)
            else:
                form_data_queryset = form_data_queryset.filter(employee_visibility=False)

        if self.context["request"].GET.get("profile_id", 0):
            profile_id = self.context["request"].GET.get("profile_id", 0)
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
            all_forms = form_data_queryset.values_list("id", flat=True)
            applied_forms = AppliedPosition.objects.filter(form_data__in=form_data_queryset, applied_profile__id=profile_id).values_list(
                "form_data__id", flat=True
            )
            return len(list(set(all_forms) - set(applied_forms)))
        else:
            form_data_queryset = form_data_queryset.count()
            return form_data_queryset

    def get_applied_category_count(self, obj):
        profile = self.context.get("profile")
        form_data = FormModel.FormData.objects.filter(form_data__job_category__id=obj.id, status="active").values_list("id")
        cat_obj = AppliedPosition.objects.filter(form_data__id__in=form_data, applied_profile=profile)
        cat_obj = cat_obj.count()
        return cat_obj


class JobLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.JobLocation
        fields = "__all__"


class JobLocationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.JobLocation
        fields = "__all__"


class JobLocationListSerializer(serializers.ModelSerializer):
    country = serializers.SerializerMethodField(read_only=True)
    state = PrimaryDataSerializer.GetStateSerializer(read_only=True, many=True)
    city = PrimaryDataSerializer.GetCitySerializer(read_only=True, many=True)
    job_count = serializers.SerializerMethodField()
    country_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FormModel.JobLocation
        fields = "__all__"

    def get_country(self, obj):
        return {"id": obj.id, "name": obj.country.name}

    def get_country_id(self, obj):
        return obj.country.id

    def get_job_count(self, obj):
        url_domain = self.context["request"].headers.get("domain")
        company_id = Company.objects.filter(url_domain=url_domain)[0].id
        data = self.context["request"].GET
        candidate_visibility = data.get("candidate_visibility")
        employee_visibility = data.get("employee_visibility")
        form_data_queryset = FormModel.FormData.objects.filter(form_data__country__id=obj.id, company=company_id, status="active")
        if candidate_visibility is not None:
            if candidate_visibility == "true":
                form_data_queryset = form_data_queryset.filter(candidate_visibility=True)
            else:
                form_data_queryset = form_data_queryset.filter(candidate_visibility=False)
        if employee_visibility is not None:
            if employee_visibility == "true":
                form_data_queryset = form_data_queryset.filter(employee_visibility=True)
            else:
                form_data_queryset = form_data_queryset.filter(employee_visibility=False)

        # form_data_queryset = form_data_queryset.count()
        if self.context["request"].GET.get("profile_id", 0):
            profile_id = self.context["request"].GET.get("profile_id", 0)
            try:
                profile_id = int(decrypt(profile_id))
            except:
                pass
            all_forms = form_data_queryset.values_list("id", flat=True)
            applied_forms = AppliedPosition.objects.filter(form_data__in=form_data_queryset, applied_profile__id=profile_id).values_list(
                "form_data__id", flat=True
            )
            return len(list(set(all_forms) - set(applied_forms)))
        else:
            form_data_queryset = form_data_queryset.count()
            return form_data_queryset


class JobLocationListTwoSerializer(serializers.ModelSerializer):
    country = PrimaryDataSerializer.GetCountrySerializer(read_only=True)
    state = PrimaryDataSerializer.GetStateSerializer(read_only=True, many=True)
    city = PrimaryDataSerializer.GetCitySerializer(read_only=True, many=True)

    class Meta:
        model = FormModel.JobLocation
        fields = "__all__"


class RecentViewJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.RecentViewJob
        fields = "__all__"


class RecentViewJobListSerializer(serializers.ModelSerializer):
    form_data = FormDataSerializer(read_only=True)

    class Meta:
        model = FormModel.RecentViewJob
        fields = "__all__"


class SavedPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.SavedPosition
        fields = "__all__"


class PositionAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.PositionAlert
        fields = "__all__"


class PositionAlertListSerializer(serializers.ModelSerializer):
    job_category = JobCategorySerializer(read_only=True, many=True)
    job_location = JobLocationListTwoSerializer(read_only=True, many=True)

    class Meta:
        model = FormModel.PositionAlert
        fields = "__all__"


class AppliedPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.AppliedPosition
        fields = "__all__"


class UnapprovedAppliedPositionSer(serializers.ModelSerializer):
    class Meta:
        model = UnapprovedAppliedPosition
        fields = "__all__"


class GetOfferLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferLetter
        fields = "__all__"


class OfferLetterSerializer(serializers.ModelSerializer):
    position_id = serializers.SerializerMethodField(read_only=True)
    candidate_name = serializers.SerializerMethodField(read_only=True)
    title = serializers.SerializerMethodField(read_only=True)
    location = serializers.SerializerMethodField(read_only=True)
    city = serializers.SerializerMethodField(read_only=True)
    ttc = serializers.SerializerMethodField(read_only=True)
    email = serializers.SerializerMethodField(read_only=True)
    interview_data = serializers.SerializerMethodField(read_only=True)
    applied_position = serializers.SerializerMethodField(read_only=True)
    form_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FormModel.OfferLetter
        fields = "__all__"

    def get_position_id(self, obj):
        return obj.offered_to.form_data.id

    def get_candidate_name(self, obj):
        return obj.offered_to.applied_profile.user.get_full_name()

    def get_title(self, obj):
        return obj.offered_to.form_data.form_data.get("job_title")

    def get_location(self, obj):
        country_dict = obj.offered_to.form_data.form_data.get("country")
        return country_dict.get("name")

    def get_city(self, obj):
        city_dict = obj.offered_to.form_data.form_data.get("city")
        return city_dict.get("name")

    def get_ttc(self, obj):
        return obj.target_compensation

    def get_email(self, obj):
        return obj.offered_to.applied_profile.user.email

    def get_interview_data(self, obj):
        if "interview_schedule_data" in obj.offered_to.data:
            return obj.offered_to.data["interview_schedule_data"]
        else:
            return {}

    def get_applied_position(self, obj):
        return AppliedPositionSerializer(obj.offered_to).data

    def get_form_data(self, obj):
        return FormDataSerializer(obj.offered_to.form_data).data


class HiringSourceSerializer(serializers.ModelSerializer):
    offered_to = AppliedPositionSerializer()
    form_data = serializers.SerializerMethodField()
    stage = serializers.SerializerMethodField()

    class Meta:
        model = FormModel.OfferLetter
        fields = "__all__"

    def get_form_data(self, obj):
        return FormDataSerializer(obj.offered_to.form_data).data

    def get_stage(self, obj):
        return obj.offered_to.data["history_detail"][-1]["name"]


class OfferLetterTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.OfferLetterTemplate
        fields = "__all__"


class OfferLetterTemplateGetSerializer(serializers.ModelSerializer):
    country = serializers.SerializerMethodField(read_only=True)
    city = serializers.SerializerMethodField(read_only=True)
    state = serializers.SerializerMethodField(read_only=True)
    job_category = serializers.SerializerMethodField(read_only=True)
    employment_type = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FormModel.OfferLetterTemplate
        fields = "__all__"

    def get_country(self, obj):
        if obj.country:
            country_serializer = PrimaryDataSerializer.CountrySerializer(obj.country)
            return [country_serializer.data]
        return [{}]

    def get_city(self, obj):
        if obj.city:
            return {"label": obj.city.name, "value": obj.city.id}
        return {}

    def get_state(self, obj):
        if obj.state:
            return {"label": obj.state.name, "value": obj.state.id}
        return {}

    def get_job_category(self, obj):
        if obj.job_category:
            return {"label": obj.job_category.job_category, "value": obj.job_category.id}
        return {}

    def get_employment_type(self, obj):
        if obj.employment_type:
            return obj.employment_type
        return {}


class StageSerializer(serializers.ModelSerializer):
    """
    StageSerializer class is created with Stage Model and added
    all field from StageSerializer Model
    """

    class Meta:
        model = Stage
        fields = "__all__"


class PositionStageSerializer(serializers.ModelSerializer):
    """
    PositionStageSerializer class is created with PositionStage Model and added
    all field from PositionStageSerializer Model
    """

    stage = StageSerializer()

    class Meta:
        model = PositionStage
        fields = "__all__"


class AppliedPositionReferralSerializer(serializers.ModelSerializer):
    applied_profile = ProfileSerializer()
    form_data = GetFormDataSerializer(read_only=True)
    current_stage_details = serializers.SerializerMethodField()

    class Meta:
        model = FormModel.AppliedPosition
        fields = "__all__"

    def get_current_stage_details(self, obj):
        try:
            app_obj = obj.data["position_stage_id"]
            stage_id = PositionStage.objects.get(id=app_obj)
            serializer = PositionStageSerializer(stage_id)
            return serializer.data
        except:
            return {}


class AppliedPositionOpReferralSerializer(serializers.ModelSerializer):
    applied_profile = serializers.SerializerMethodField(read_only=True)
    form_data = serializers.SerializerMethodField(read_only=True)
    current_stage_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FormModel.AppliedPosition
        fields = "__all__"

    def get_applied_profile(self, obj):
        data = {}
        data["candidate_name"] = obj.applied_profile.user.get_full_name()
        return data

    def get_form_data(self, obj):
        data = {}
        data["id"] = obj.form_data.id
        data["form_data"] = {}
        data["form_data"]["job_title"] = obj.form_data.form_data["job_title"]
        data["form_data"]["location"] = obj.form_data.form_data["location"][0]["label"]
        return data

    def get_current_stage_details(self, obj):
        try:
            app_obj = obj.data["position_stage_id"]
            stage_id = PositionStage.objects.get(id=app_obj)
            serializer = PositionStageSerializer(stage_id)
            return serializer.data
        except:
            return {}


class AppliedPositionListSerializer(serializers.ModelSerializer):
    form_data = FormDataSerializer(read_only=True)
    applied_profile = GetCustomProfileSerializer(read_only=True)
    stage_details = serializers.SerializerMethodField(read_only=True)
    pending_scorecard_details = serializers.SerializerMethodField(read_only=True)
    average_scorecard_rating = serializers.SerializerMethodField(read_only=True)
    scorecard_ratings = serializers.SerializerMethodField(read_only=True)
    all_score_details = serializers.SerializerMethodField(read_only=True)
    offer_status = serializers.SerializerMethodField(read_only=True)
    offer_approval_details = serializers.SerializerMethodField()
    offer_letter = serializers.SerializerMethodField(read_only=True)
    resume = serializers.SerializerMethodField(read_only=True)
    complete_feedback = serializers.SerializerMethodField(read_only=True)
    sposition_id = serializers.SerializerMethodField()

    class Meta:
        model = FormModel.AppliedPosition
        fields = "__all__"

    def get_sposition_id(self, obj):
        return obj.form_data.show_id

    def get_resume(self, obj):
        media_objs = Media.objects.filter(profile=obj.applied_profile, field_name="upload_resume")
        if media_objs:
            media_serializer = MediaSerializer(media_objs[0])
            return media_serializer.data
        else:
            return {}

    def get_offer_approval_details(self, obj):
        offer_approval_obj = OfferApproval.objects.filter(position=obj.form_data).order_by("sort_order")
        # serializer = OfferApprovalListSerializer(offer_approval_obj, many=True)
        # return serializer.data
        # Using custom serializer to avoid looping with OfferApprovalListSerializer
        data = []
        for offer_approval in offer_approval_obj:
            temp_dict = {}
            temp_dict["approval_type"] = offer_approval.approval_type
            temp_dict["company"] = offer_approval.company.id
            temp_dict["created_at"] = offer_approval.created_at
            temp_dict["id"] = offer_approval.id
            temp_dict["is_approve"] = offer_approval.is_approve
            temp_dict["is_reject"] = offer_approval.is_reject
            temp_dict["position"] = offer_approval.position.id
            temp_dict["slug"] = offer_approval.slug
            temp_dict["sort_order"] = offer_approval.sort_order
            temp_dict["updated_at"] = offer_approval.updated_at
            profile_serializer = ProfileSerializer(offer_approval.profile)
            temp_dict["profile"] = profile_serializer.data
            data.append(temp_dict)
        return data

    def get_stage_details(self, obj):
        try:
            # position_stage_id = obj.data["position_stage_id"]
            # stage = PositionStage.objects.get(id=position_stage_id)
            # serializer = PositionStageSerializer(stage)
            # data = serializer.data
            # data = {"stage": {"stage_name": obj.data["history_detail"][-1]["name"]}}
            try:
                stage_detail = Stage.objects.get(id=obj.data["current_stage_id"])
                data = {"stage": {"stage_name": stage_detail.stage_name}}
            except:
                data = {"stage": {"stage_name": obj.data["history_detail"][-1]["name"]}}
            try:
                if obj.application_status in ["reject", "rejected", "calcel", "offer-decline", "approved", "offer-rejected"]:
                    data["stage"]["stage_name"] = obj.application_status.title()
                if obj.application_status == "pending-offer":
                    data["stage"]["stage_name"] = "Offer"
                if obj.application_status in ["hire", "hired"]:
                    data["stage"]["stage_name"] = "Hired"
                if obj.applied_profile.id == self.context.get("own_id"):
                    if obj.application_status in ["reject", "rejected", "calcel", "offer-decline", "offer-rejected"]:
                        data["stage"]["stage_name"] = "Rejected"
                    else:
                        data["stage"]["stage_name"] = "Resume Review"
            except:
                pass
            return data
        except Exception as e:
            return None

    def get_pending_scorecard_details(self, obj):
        try:
            interviewer_id = self.context.get("pending_interviewer_ids")
            interview_obj = Profile.objects.filter(id__in=interviewer_id)
            interview_obj = interview_obj.prefetch_related("user", "address")
            serializer = ProfileSerializer(interview_obj, many=True)
            return serializer.data
        except:
            return []

    def get_average_scorecard_rating(self, obj):
        interviewer_id = self.context.get("own_id")

        position_scorecard_obj = PositionScoreCard.objects.filter(position=obj.form_data.id, applied_profiles=obj.applied_profile.id)
        if interviewer_id:
            position_scorecard_obj.filter(interviewer_profile=interviewer_id)
        position_scorecard_obj = position_scorecard_obj.aggregate(Avg("rating"))["rating__avg"]
        if position_scorecard_obj is None:
            position_scorecard_obj = 0
        return position_scorecard_obj

    def get_complete_feedback(self, obj):
        total_attributes = 0
        profiles = Profile.objects.filter(id=self.context.get("own_id"))
        for position_stage in PositionStage.objects.filter(position=obj.form_data, profiles__in=profiles):
            competencies = position_stage.competency
            for competency in competencies.all():
                total_attributes += competency.attribute.all().count()
        total_ratings_given = PositionScoreCard.objects.filter(
            position=obj.form_data, interviewer_profile__id=self.context.get("own_id"), applied_profiles=obj.applied_profile
        ).count()
        if total_ratings_given >= total_attributes and OverAllRatingDashboard.objects.filter(
            applied_position=obj, interviewer_id__id=self.context.get("own_id"), candidate_id=obj.applied_profile, is_deleted=False
        ):
            return True
        else:
            return False

    def get_scorecard_ratings(self, obj):
        interviewer_id = self.context.get("own_id")

        position_scorecard_obj = PositionScoreCard.objects.filter(
            position=obj.form_data.id, interviewer_profile=interviewer_id, applied_profiles=obj.applied_profile.id
        )

        # return position_scorecard_obj
        return PositionScoreCardSerializer(position_scorecard_obj, many=True).data

    def get_all_score_details(self, obj):
        pending_interviewer_list = []
        try:
            interviewer_ids = obj.data["interview_schedule_data"]["Interviewer"]
            for interviewer in interviewer_ids:
                pending_interviewer_list.append(interviewer["profile_id"])
        except:
            interviewer_ids = []

        profile_obj = Profile.objects.filter(id__in=pending_interviewer_list)
        context = {"applied_position_obj": obj}
        profile_obj = profile_obj.prefetch_related("user")
        serializer = ScorecardProfileSerializer(profile_obj, many=True, context=context)
        data = serializer.data
        return data

    def get_offer_status(self, obj):
        """
        1 = No OfferApproval Sent
        2 = One of the OfferApproval is Rejected
        3 = All Approvers are have still not accepted the OfferApproval
        4 = All Approvers has accepted the Approval
        """
        offer_obj = OfferApproval.objects.filter(position=obj.form_data.id)
        if offer_obj.count() == 0:
            return 1
        else:
            for offer in offer_obj:
                if offer.is_reject is True:
                    return 2
                if offer.is_approve is False:
                    return 3
            return 4

    def get_offer_letter(self, obj):
        try:
            offerletter_obj = OfferLetter.objects.get(offered_to=obj)
            if offerletter_obj.data:
                return offerletter_obj.data
            else:
                offerletter_serializer = OfferLetterSerializer(offerletter_obj)
                return offerletter_serializer.data
        except Exception as e:
            return {"erorr": str(e)}


class OpAppliedPositionListSerializer(serializers.ModelSerializer):
    form_data = serializers.SerializerMethodField(read_only=True)
    applied_profile = serializers.SerializerMethodField(read_only=True)
    stage_details = serializers.SerializerMethodField(read_only=True)
    resume = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FormModel.AppliedPosition
        fields = "__all__"
        read_only_fields = ["form_data", "applied_profile", "stage_details", "resume"]

    def get_applied_profile(self, obj):
        data = {}
        data["id"] = obj.applied_profile.id
        data["user"] = {}
        data["user"]["first_name"] = obj.applied_profile.user.first_name
        data["user"]["last_name"] = obj.applied_profile.user.last_name
        data["user"]["middle_name"] = obj.applied_profile.user.middle_name
        return data

    def get_form_data(self, obj):
        data = {}
        try:
            user_obj = User.objects.get(email__iexact=obj.form_data.recruiter, user_company=obj.company)
            data["recruiter_name"] = user_obj.get_full_name()
        except:
            data["recruiter_name"] = obj.form_data.recruiter
        data["form_data"] = obj.form_data.form_data
        return data

    def get_resume(self, obj):
        media_objs = Media.objects.filter(profile=obj.applied_profile, field_name="upload_resume")
        if media_objs:
            media_serializer = MediaSerializer(media_objs[0])
            return media_serializer.data
        else:
            return {}

    def get_stage_details(self, obj):
        try:
            try:
                stage_detail = Stage.objects.get(id=obj.data["current_stage_id"])
                data = {"stage": {"stage_name": stage_detail.stage_name}}
            except:
                data = {"stage": {"stage_name": obj.data["history_detail"][-1]["name"]}}
            try:
                if obj.application_status in ["reject", "rejected", "calcel", "offer-decline", "approved", "offer-rejected"]:
                    data["stage"]["stage_name"] = obj.application_status.title()
                if obj.application_status == "pending-offer":
                    data["stage"]["stage_name"] = "Offer"
                if obj.application_status in ["hire", "hired"]:
                    data["stage"]["stage_name"] = "Hired"
                if obj.applied_profile.id == self.context.get("own_id"):
                    if obj.application_status in ["reject", "rejected", "calcel", "offer-decline", "offer-rejected"]:
                        data["stage"]["stage_name"] = "Rejected"
                    else:
                        data["stage"]["stage_name"] = "Resume Review"
            except:
                pass
            return data
        except Exception as e:
            return None


class InternalApplicantSerializer(serializers.ModelSerializer):
    form_data = serializers.SerializerMethodField(read_only=True)
    applied_profile = ProfileSerializer(read_only=True)
    stage_details = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FormModel.AppliedPosition
        fields = ["form_data", "applied_profile", "stage_details", "applicant_details", "created_at", "id", "updated_at"]

    def get_form_data(self, obj):
        data = {}
        try:
            user_obj = User.objects.get(email__iexact=obj.form_data.recruiter, user_company=obj.company)
            data["recruiter_name"] = user_obj.get_full_name()
        except:
            data["recruiter_name"] = obj.form_data.recruiter
        data["form_data"] = obj.form_data.form_data
        data["id"] = obj.form_data.id
        return data

    def get_stage_details(self, obj):
        try:
            # data = {"stage": {"stage_name": obj.data["history_detail"][-1]["name"]}}
            try:
                stage_detail = Stage.objects.get(id=obj.data["current_stage_id"])
                data = {"stage": {"stage_name": stage_detail.stage_name}}
            except:
                data = {"stage": {"stage_name": obj.data["history_detail"][-1]["name"]}}
            try:
                if obj.application_status in ["reject", "rejected", "calcel", "offer-decline", "approved", "offer-rejected"]:
                    data["stage"]["stage_name"] = obj.application_status.title()
                if obj.application_status == "pending-offer":
                    data["stage"]["stage_name"] = "Offer"
                if obj.application_status in ["hire", "hired"]:
                    data["stage"]["stage_name"] = "Hired"
                if obj.applied_profile.id == self.context.get("own_id"):
                    if obj.application_status in ["reject", "rejected", "calcel", "offer-decline", "offer-rejected"]:
                        data["stage"]["stage_name"] = "Rejected"
                    else:
                        data["stage"]["stage_name"] = "Resume Review"
            except:
                pass
            return data
        except Exception as e:
            return None


class AppliedPositionSerializerInterview(AppliedPositionListSerializer):
    interviews = serializers.SerializerMethodField()

    def get_interviews(self, obj):
        return 0


class AppliedPositionListForManagerSerializer(serializers.ModelSerializer):
    form_data = GetFormDataSerializer(read_only=True)
    applied_profile = ProfileSerializer(read_only=True)
    stage_details = serializers.SerializerMethodField(read_only=True)
    pending_scorecard_details = serializers.SerializerMethodField()
    average_scorecard_rating = serializers.SerializerMethodField()
    scorecard_ratings = serializers.SerializerMethodField()
    all_score_details = serializers.SerializerMethodField()

    class Meta:
        model = FormModel.AppliedPosition
        fields = "__all__"

    def get_stage_details(self, obj):
        try:
            # position_stage_id = obj.data["position_stage_id"]
            # stage = PositionStage.objects.get(id=position_stage_id)
            # serializer = PositionStageSerializer(stage)
            # data = serializer.data
            # data = {"stage": {"stage_name": obj.data["history_detail"][-1]["name"]}}
            try:
                stage_detail = Stage.objects.get(id=obj.data["current_stage_id"])
                data = {"stage": {"stage_name": stage_detail.stage_name}}
            except:
                data = {"stage": {"stage_name": obj.data["history_detail"][-1]["name"]}}
            try:
                if obj.application_status in ["reject", "rejected", "calcel", "offer-decline", "approved", "offer-rejected"]:
                    data["stage"]["stage_name"] = obj.application_status.title()
                if obj.application_status == "pending-offer":
                    data["stage"]["stage_name"] = "Offer"
                if obj.application_status in ["hire", "hired"]:
                    data["stage"]["stage_name"] = "Hired"
                if obj.applied_profile.id == self.context.get("own_id"):
                    if obj.application_status in ["reject", "rejected", "calcel", "offer-decline", "offer-rejected"]:
                        data["stage"]["stage_name"] = "Rejected"
                    else:
                        data["stage"]["stage_name"] = "Resume Review"
            except:
                pass
            return data
        except Exception as e:
            return None

    def get_pending_scorecard_details(self, obj):
        try:
            interviewer_id = self.context.get("pending_interviewer_ids")
            interview_obj = Profile.objects.filter(id__in=interviewer_id)
            serializer = ProfileSerializer(interview_obj, many=True)
            return serializer.data
        except:
            return []

    def get_average_scorecard_rating(self, obj):
        interviewer_id = self.context.get("own_id")

        position_scorecard_obj = PositionScoreCard.objects.filter(position=obj.form_data.id, applied_profiles=obj.applied_profile.id).aggregate(
            Avg("rating")
        )["rating__avg"]
        if position_scorecard_obj is None:
            position_scorecard_obj = 0
        return position_scorecard_obj

    def get_scorecard_ratings(self, obj):
        interviewer_id = self.context.get("own_id")

        position_scorecard_obj = PositionScoreCard.objects.filter(
            position=obj.form_data.id, interviewer_profile=interviewer_id, applied_profiles=obj.applied_profile.id
        )

        # return position_scorecard_obj
        return PositionScoreCardSerializer(position_scorecard_obj, many=True).data

    def get_all_score_details(self, obj):
        pending_interviewer_list = []
        # try:
        #     interviewer_ids = obj.data["interview_schedule_data"]["Interviewer"]
        #     for interviewer in interviewer_ids:
        #         pending_interviewer_list.append(interviewer["profile_id"])
        # except:
        #     interviewer_ids = []
        interviewer_ids = (
            PositionScoreCard.objects.filter(position=obj.form_data, applied_profiles=obj.applied_profile)
            .distinct("interviewer_profile")
            .values_list("interviewer_profile__id", flat=True)
        )

        # profile_obj = Profile.objects.filter(id__in=pending_interviewer_list)
        profile_obj = Profile.objects.filter(id__in=interviewer_ids)
        context = {"applied_position_obj": obj}
        serializer = ScorecardProfileSerializer(profile_obj, many=True, context=context)
        return serializer.data


class ResumeReviewSerialzer(serializers.ModelSerializer):
    form_data = FormDataSerializer(read_only=True)
    applied_profile = BasicProfileSerializer()

    class Meta:
        model = FormModel.AppliedPosition
        fields = "__all__"


class AppliedPositionRatingListSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()
    form_data = GetFormDataSerializer(read_only=True)  # 400+
    applied_profile = ProfileSerializer(read_only=True)  # 500+
    resume = serializers.SerializerMethodField(read_only=True)  # 100+

    class Meta:
        model = FormModel.AppliedPosition
        fields = "__all__"

    def get_resume(self, obj):
        media_objs = Media.objects.filter(profile=obj.applied_profile, field_name="upload_resume")
        if media_objs:
            media_serializer = MediaSerializer(media_objs[0])
            return media_serializer.data
        else:
            return {}

    def get_rating(self, obj):
        try:
            app_obj = obj.data
            stage_id = app_obj["current_stage_id"]
            profile_id = obj.applied_profile.id
            rating_obj = PositionScoreCard.objects.filter(position_stage=stage_id, applied_profiles=profile_id)
            serializer = PositionScoreCardSerializer(rating_obj, many=True)
            return serializer.data
        except:
            return []


class ReasonTypeSerializer(serializers.ModelSerializer):
    """
    ReasonTypeSerializer class is created with ReasonType Model and added
    type and reason field from ReasonTypeSerializer Model
    """

    class Meta(object):
        model = ReasonType
        fields = "__all__"


class ReasonSerializer(serializers.ModelSerializer):
    """
    ReasonSerializer class is created with Reason Model and added
    type and reason field from ReasonSerializer Model
    """

    type = ReasonTypeSerializer()

    class Meta(object):
        model = Reason
        fields = "__all__"


class CreateReasonSerializer(serializers.ModelSerializer):
    """
    ReasonSerializer class is created with Reason Model and added
    type and reason field from ReasonSerializer Model
    """

    class Meta(object):
        model = Reason
        fields = "__all__"


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.Reminder
        fields = "__all__"


class GetReminderSerializer(serializers.ModelSerializer):
    sender_profile = ProfileSerializer()

    class Meta:
        model = FormModel.Reminder
        fields = "__all__"


class JobBoardTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.JobBoardTemplate
        fields = "__all__"


class JobDescriptionImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.JobDescriptionImages
        fields = ["Image_file"]


class CreateApplicantDocumentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormModel.ApplicantDocuments
        fields = "__all__"


class GetApplicantDocumentsSerializer(serializers.ModelSerializer):
    applied_position = AppliedPositionListSerializer()

    class Meta:
        model = FormModel.ApplicantDocuments
        fields = "__all__"


class OfferApprovalListSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    position = GetFormDataSerializer(read_only=True)
    offer_approval_details = serializers.SerializerMethodField()
    offer_approved_candidates = serializers.SerializerMethodField()
    reminder_status = serializers.SerializerMethodField()
    offer_letter = serializers.SerializerMethodField()

    class Meta:
        model = FormModel.OfferApproval
        fields = "__all__"

    def get_offer_approval_details(self, obj):
        offer_obj = OfferApproval.objects.filter(position=obj.position.id).exclude(id=obj.id).order_by("sort_order")
        serializer = GetOfferApprovalsSerializer(offer_obj, many=True)
        return serializer.data

    def get_offer_approved_candidates(self, obj):
        app_obj = AppliedPosition.objects.filter(form_data=obj.position.id)
        app_obj = app_obj.filter(data__has_key="offer")
        return AppliedPositionListSerializer(app_obj, many=True).data

    def get_reminder_status(self, obj):
        reminder_count = Reminder.objects.filter(offer=obj.id).count()
        if reminder_count > 0:
            return True
        else:
            return False

    def get_offer_letter(self, obj):
        try:
            offer_obj = OfferLetter.objects.filter(offered_to__form_data=obj.position).last()
            offer_serializer = OfferLetterSerializer(offer_obj)
            return offer_serializer.data
        except:
            return {}


class CareerTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerTemplate
        fields = "__all__"


class UserSelectedFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSelectedField
        fields = "__all__"


class CustomQuestionSerializer(serializers.ModelSerializer):
    position_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomQuestion
        fields = "__all__"

    def get_position_name(self, obj):
        data = []
        for position in obj.position.all():
            data.append(position.form_data.get("job_title"))
        return data


class AnswerSerailizer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = "__all__"


class CustomReportCandidateDataSerializer(serializers.ModelSerializer):
    form_data = GetFormDataSerializer(read_only=True)
    applied_profile = ProfileSerializer(read_only=True)
    offer_status = serializers.SerializerMethodField()
    offer_letter = serializers.SerializerMethodField(read_only=True)
    resume = serializers.SerializerMethodField(read_only=True)
    current_hiring_stage = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FormModel.AppliedPosition
        fields = "__all__"

    def get_resume(self, obj):
        media_objs = Media.objects.filter(profile=obj.applied_profile, field_name="upload_resume")
        if media_objs:
            media_serializer = MediaSerializer(media_objs[0])
            return media_serializer.data
        else:
            return {}

    def get_offer_status(self, obj):
        """
        1 = No OfferApproval Sent
        2 = One of the OfferApproval is Rejected
        3 = All Approvers are have still not accepted the OfferApproval
        4 = All Approvers has accepted the Approval
        """
        offer_obj = OfferApproval.objects.filter(position=obj.form_data.id)
        if offer_obj.count() == 0:
            return 1
        else:
            for offer in offer_obj:
                if offer.is_reject is True:
                    return 2
                if offer.is_approve is False:
                    return 3
            return 4

    def get_offer_letter(self, obj):
        try:
            offerletter_obj = OfferLetter.objects.get(offered_to=obj)
            offerletter_serializer = OfferLetterSerializer(offerletter_obj)
            return offerletter_serializer.data
        except Exception as e:
            return {"erorr": str(e)}

    def get_current_hiring_stage(self, obj):
        try:
            return Stage.objects.get(id=obj.data["current_stage_id"]).stage_name
        except:
            return None
