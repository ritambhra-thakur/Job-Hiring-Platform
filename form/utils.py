from url_shortener.models import ShortURL
from django.conf import settings
from stage.models import PositionStage
from user.models import Profile
from scorecard.models import PositionScoreCard, OverAllRatingDashboard


def get_value(data, target):
    for key, value in data.items():
        if isinstance(value, dict):
            yield from get_value(value, target)
        elif key == target:
            yield value


position_dict = {
    "Position Name": "position_name",
    "Position No": "show_id",
    "Status": "status",
    "Candidates Applied": "applied_candidates_count",
    "Job Description": "job_description",
    "Department": "department",
    "Recruiter": "recruiter_name",
    "Category": "category",
    "Location": "location",
    "Job Title": "job_title",
    "Country": "country",
    "Level": "level",
    "Employment Type": "employment_type",
    "Salary": "salary",
    "Hiring Manager": "hiring_manager_name",
    "Candidate Name": "first_name",
    "Source": "source",
    "Linkedin URL": "linkedin_url",
    "Personal URL": "personal_url",
    "Candidate Name": "candidate_name",
    "Email Address": "email",
    "Offer TTC": "target_compensation",
    "Salary": "salary",
    "External Link": "candidate_visibility_link",
    "Internal Link": "employee_visibility_link",
    # "Video JD": "job_description",
    "Hiring Stage Status": "stage_name",
    "Job Category": "job_category",
    "Description": "description",
    "My Skills": "skill",
}

offer_type_dict = {
    "Offer Type": "offer_type",
    "Offer ID": "offer_id",
    "Attach Offer Letter": "attached_letter",
    "Entity": "",
    "Last Updated": "updated_on",
    "Status": "status",
}

referral_dict = {
    "Referral Name": "referral_name",
    "Country": "country",
    "State": "state",
    "Payout": "referral_amount",
    "Attach Policy": "attach_referral_policy_document",
    "Referral Rate Start Date": "referral_rate_start_date",
    "Referral Rate End Date": "referral_rate_end_date",
}


def get_candidate_visibility_link(obj):
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
    else:
        return None


def get_employee_visibility_link(obj):
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
    else:
        return None


def get_complete_feedback(obj, profile_id):
    print("--------------------------------------")
    total_attributes = 0
    profiles = Profile.objects.filter(id=profile_id)
    print(profiles)
    for position_stage in PositionStage.objects.filter(position=obj.form_data, profiles__in=profiles):
        competencies = position_stage.competency
        for competency in competencies.all():
            total_attributes += competency.attribute.all().count()
    print(total_attributes)
    total_ratings_given = PositionScoreCard.objects.filter(
        position=obj.form_data, interviewer_profile__id=profile_id, applied_profiles=obj.applied_profile
    ).count()
    print(total_ratings_given)
    if total_ratings_given >= total_attributes and OverAllRatingDashboard.objects.filter(
        applied_position=obj, interviewer_id__id=profile_id, candidate_id=obj.applied_profile, is_deleted=False
    ):
        return True
    else:
        return False


import datetime


def get_days_in_status(obj):
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
