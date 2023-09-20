import time
from contextlib import nullcontext
from email.policy import default
from operator import mod
from tkinter.tix import Tree
from tokenize import blank_re
from xmlrpc.client import Boolean

from django.db import models
from django.utils.text import slugify
from django_extensions.db.fields import AutoSlugField
from pyexpat import model

from app.choices import *
from company.models import Company
from primary_data.models import City, Country, State
from user.models import Profile, User


def get_json_default():
    return {}


def get_json_default_list():
    return []


# Create your models here.
class Form(models.Model):
    """
    Form model is belongs to Position Form in product flow
    Every company (User) has it's own Position form
    """

    form_name = models.CharField(max_length=150)
    slug = AutoSlugField(populate_from=["form_name", "company"])
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="form_company",
    )
    description = models.TextField(blank=True, null=True)
    # form_type = models.IntegerField(blank=True, null=True, help_text="1. Offer, 2. Position, 3. Application")

    # is_cloned = models.BooleanField(default=False)
    # cloned_from_id = models.IntegerField(blank=True, null=True)
    # created_by_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="form_created_by_profile")

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    # history = HistoricalRecords(table_name="form_history")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.form_name

    # update the slug field when UpdateForm API is hit.
    def save(self, *args, **kwargs):
        value = self.form_name[0:250] + "-" + str(self.company)
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)


class FieldType(models.Model):
    """
    FieldType model is belongs to type of field
    it is managed by product admin
    """

    field_type = models.CharField(max_length=150)
    # history = HistoricalRecords(table_name="field_type_history")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.field_type


class Field(models.Model):
    """
    FieldType model is belongs to Position Form field in product flow
    Every Position Form has it's own Field
    """

    field_name = models.CharField(max_length=150)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="field_company",
    )
    slug = AutoSlugField(populate_from=["field_name", "company"], max_length=255)
    form = models.ForeignKey(to=Form, on_delete=models.CASCADE, related_name="field")
    field_type = models.ForeignKey(FieldType, on_delete=models.CASCADE, related_name="type")
    field_block = models.CharField(max_length=150, null=True, blank=True)
    can_delete = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=1, help_text="Sort by")
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)
    is_mandatory = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    # history = HistoricalRecords(table_name="field_history")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.field_name

    # update the slug field when UpdateField API is hit.
    def save(self, *args, **kwargs):
        value = self.field_name[0:250] + "-" + str(self.company)
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)


class FieldChoice(models.Model):
    """
    FieldChoice model is belongs to Field model
    mainly it's belongs to drop down
    """

    choice_key = models.CharField(max_length=150)
    choice_value = models.CharField(max_length=150)
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    sort_order = models.IntegerField(default=1, help_text="Sort by")
    # history = HistoricalRecords(table_name="field_choice")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.choice_key


def contact_default():
    return {"key": "value"}


def form_data_slug_function(content):
    print(content)
    print(content.__dict__)
    return content.replace("_", "-").append(int(time.time())).lower()


class FormData(models.Model):
    """
    FormData model is belongs to Form model
    it contain form field by user
    """

    form = models.ForeignKey(to=Form, on_delete=models.CASCADE, null=True, blank=True, related_name="form_form_data")
    show_id = models.IntegerField(default=0)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="form_data_company",
    )
    recruiter = models.CharField(max_length=100, null=True, blank=True)
    hiring_manager = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=10, choices=POSITION_STATUS, default="draft")
    candidate_visibility = models.BooleanField(default=False)
    candidate_visibility_updated_at = models.DateTimeField(blank=True, null=True)
    employee_visibility = models.BooleanField(default=False)
    employee_visibility_updated_at = models.DateTimeField(blank=True, null=True)
    form_data = models.JSONField(default=contact_default)
    job_description = models.FileField(upload_to="media/jd", blank=True, null=True, help_text="Select file", default=None)
    is_cloned = models.BooleanField(default=False)
    cloned_from_id = models.IntegerField(blank=True, null=True)
    created_by_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, blank=True, related_name="form_created_by_profile")

    # profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="profile_form_data")
    history = models.JSONField(default=get_json_default_list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class ReasonType(models.Model):
    """
    ReasonType Model class is created with fields to add reasons
    """

    reason_name = models.CharField(max_length=50, null=True, blank=True, help_text="Enter Reason Name")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.reason_name


class Reason(models.Model):
    """
    Reason Model class is created with fields to add reasons
    """

    type = models.ForeignKey(
        ReasonType,
        on_delete=models.CASCADE,
        related_name="reason_type_company",
        null=False,
        blank=False,
    )
    reason = models.CharField(max_length=200, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=False, blank=False, related_name="reason_company")
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.reason


class PositionApproval(models.Model):
    """
    model contains data related to jobpost approval details
    """

    position = models.ForeignKey(FormData, on_delete=models.CASCADE, null=True, blank=True, related_name="position_approvals")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="form_data_approval_company",
    )
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="employee profile who are going to approve this position",
    )

    approval_type = models.CharField(choices=APPROVAL_TYPE, default="one to one", max_length=11, null=True, blank=True)
    sort_order = models.IntegerField(default=1, help_text="Sort by", null=True, blank=True)
    show = models.BooleanField(default=True)
    reason = models.ForeignKey(Reason, on_delete=models.CASCADE, null=True, blank=True)
    reject_reason = models.TextField(null=True, blank=True)
    is_approve = models.BooleanField(default=False)
    is_reject = models.BooleanField(default=False)

    slug = AutoSlugField(populate_from=["position", "company", "profile"])

    # history = HistoricalRecords(table_name="position_approval_history")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OfferApproval(models.Model):
    """
    model contains data related to jobpost offer approval employee details related to jobpost
    """

    position = models.ForeignKey(FormData, on_delete=models.CASCADE, null=True, blank=True, related_name="offer_approvals")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="form_data_offer_approval_company",
    )
    profile = models.ForeignKey(
        Profile,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="employee profile who are going to approve this position",
    )

    approval_type = models.CharField(choices=APPROVAL_TYPE, default="one to one", max_length=11, null=True, blank=True)
    sort_order = models.IntegerField(default=1, help_text="Sort by", null=True, blank=True)
    show = models.BooleanField(default=True)
    is_approve = models.BooleanField(default=False)
    is_reject = models.BooleanField(default=False)
    slug = AutoSlugField(populate_from=["position", "company", "profile"])

    candidate = models.ForeignKey(Profile, related_name="offered_to_profile", null=True, blank=True, on_delete=models.SET_NULL)
    # history = HistoricalRecords(table_name="offer_approval_history")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class JobCategory(models.Model):
    """
    JobCategory model contains list of job category
    job_category field is belongs to Field model
    """

    job_category = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_category_company",
        help_text="Choose job category company name",
    )
    # history = HistoricalRecords(table_name="job_category_history")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.job_category


class JobLocation(models.Model):
    """
    JobLocation model contains list of job locations
    to specific company
    """

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Choose your Country",
    )
    country_image = models.FileField(
        upload_to="media/",
        blank=True,
        null=True,
        help_text="Select file",
    )
    state = models.ManyToManyField(
        State,
        blank=True,
        help_text="Choose your State",
    )
    city = models.ManyToManyField(
        City,
        blank=True,
        help_text="Choose your city",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_location_company",
        help_text="Choose job location for specific company",
    )
    # history = HistoricalRecords(table_name="job_location_history")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.country.name


class RecentViewJob(models.Model):
    """
    RecentViewJob model contains list of job recently viewed by user
    """

    form_data = models.ForeignKey(FormData, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recent_view_job_company",
        help_text="Choose job location for specific company",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SavedPosition(models.Model):
    """
    SavedPosition model contain saved position belongs to specific user
    """

    form_data = models.ForeignKey(FormData, on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="saved_position_company",
        help_text="Choose job location for specific company",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PositionAlert(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)
    job_category = models.ManyToManyField(JobCategory, blank=True)
    job_location = models.ManyToManyField(JobLocation, blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="position_alert_company",
        help_text="Choose company for specific profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


def get_ref_default():
    return {}


class AppliedPosition(models.Model):
    """
    this model contais candidate applied job details
    """

    form_data = models.ForeignKey(FormData, on_delete=models.CASCADE)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="applied_position_company",
        help_text="Choose job location for specific company",
    )
    applied_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="applied_profile")
    refereed_by_profile = models.JSONField(null=True, blank=True, default=get_ref_default)
    application_status = models.CharField(max_length=15, choices=APPLICATION_STATUS, default="active")
    rejection_mail_sent = models.BooleanField(default=True, null=True, blank=True)
    withdrawn = models.BooleanField(default=False)
    data = models.JSONField(default=contact_default)
    joining_date = models.DateField(null=True, blank=True, help_text="joining_date")
    applicant_details = models.JSONField(default=contact_default)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class UnapprovedAppliedPosition(models.Model):
    """
    this model contais candidate applied job details
    """

    form_data = models.ForeignKey(FormData, on_delete=models.CASCADE)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="unapproved_applied_position_company",
        help_text="Choose job location for specific company",
    )
    email = models.CharField(max_length=255)
    refereed_by_profile = models.JSONField(null=True, blank=True, default=get_ref_default)
    data = models.JSONField(default=contact_default)
    applicant_details = models.JSONField(default=contact_default)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OfferLetterTemplate(models.Model):
    """
    This models contains the data of Offer Letter
    templates which are added from the admin panel
    """

    offer_type = models.CharField(max_length=250)
    offer_id = models.CharField(max_length=12)
    attached_letter = models.FileField(upload_to="offer_letter_templates")
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, default=None, blank=True, null=True)
    # entiry = models.CharField(max_length=250, default="Template", )
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="offer_letter_country", default=None, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="offer_letter_state", default=None, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="offer_letter_ctiy", default=None, null=True, blank=True)
    job_category = models.ForeignKey(
        JobCategory, on_delete=models.CASCADE, related_name="offer_letter_job_category", default=None, null=True, blank=True
    )
    employment_type = models.JSONField(default=get_json_default)
    status = models.BooleanField(default=True)
    updated_on = models.DateTimeField(auto_now=True)


class OfferLetter(models.Model):
    """
    Model contains data of offer letter provided to
    top rated candidates by hiring manager
    """

    show_offer_id = models.IntegerField(default=0)
    offered_to = models.ForeignKey(AppliedPosition, on_delete=models.CASCADE, related_name="offered_to")
    offered_by_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="offered_by_profile")
    offer_created_mail = models.BooleanField(default=False)
    data = models.JSONField(default=get_json_default())
    basic_salary = models.CharField(max_length=200, default=0, null=True, blank=True)
    bonus = models.CharField(default=0, null=True, blank=True, max_length=200)
    guarantee_bonus = models.CharField(default=0, null=True, blank=True, max_length=200)
    sign_on_bonus = models.CharField(max_length=200, default=0, null=True, blank=True)
    relocation_bonus = models.CharField(max_length=200, default=0, null=True, blank=True)
    start_date = models.DateField()
    has_joined = models.BooleanField(default=False)
    start_date_change = models.BooleanField(default=False)
    email_changed = models.BooleanField(default=False)
    target_compensation = models.CharField(max_length=200, default=None, null=True, blank=True)
    visa_required = models.CharField(default="Visa is not required.", max_length=250, null=True, blank=Tree)
    allowance = models.CharField(max_length=200, default=0, null=True, blank=True)
    accepted = models.BooleanField(default=None, null=True, blank=True)
    currency = models.CharField(max_length=12, default="INR")
    reporting_manager = models.CharField(max_length=250, null=True, blank=True, default=None)
    signed_file = models.FileField(upload_to="offer-letters/", default=None, blank=True, null=True)
    withdraw = models.BooleanField(default=False)
    is_decline = models.BooleanField(default=False)
    decline_reason = models.CharField(max_length=250, default="No Reason")
    response_date = models.DateField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(null=True, blank=True, default=None)
    # Docusign
    docusign_envelope_id = models.CharField(max_length=255, default=None, null=True, blank=True)


class Reminder(models.Model):
    """
    this model contais reminder
    """

    position = models.ForeignKey(PositionApproval, on_delete=models.CASCADE, related_name="position_reminder", null=True, blank=True)
    offer = models.ForeignKey(OfferApproval, on_delete=models.CASCADE, related_name="offer_reminder", null=True, blank=True)
    reminder_to = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="user_reminder", null=True, blank=True)
    sender_profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="profile_sender", null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    type = models.IntegerField(null=True, blank=True, help_text="1.Position Approval, 2.Offer Approval")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class JobBoardTemplate(models.Model):
    """
    RecentViewJob model contains list of job recently viewed by user
    """

    template = models.TextField(null=True, blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_board_template_company",
        help_text="Job board template for specific company",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class JobDescriptionImages(models.Model):
    Image_file = models.FileField(upload_to="media/", blank=True, null=True, help_text="Select file")
    image_file_name = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        help_text="Enter the image file name",
    )
    image_field_name = models.CharField(max_length=250, blank=True, null=True, help_text="Enter image field name")
    image_file_type = models.CharField(max_length=120, blank=True, null=True, help_text="Enter image file type")
    is_active = models.BooleanField(default=True, help_text="Select your prefrences")
    is_deleted = models.BooleanField(default=False, help_text="Select your prefrences")
    can_delete = models.BooleanField(default=True, help_text="Select your prefrences")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Select your prefrences")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated time")


class ApplicantDocuments(models.Model):
    doucument = models.FileField(upload_to="media/", blank=True, null=True, help_text="Select_file")
    applied_position = models.ForeignKey(AppliedPosition, on_delete=models.CASCADE, null=False, blank=False, related_name="applied_document")
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def __unicode__(self):
        return self.id


class CareerTemplate(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="career_template",
    )
    is_internal = models.BooleanField(default=False)
    template_type = models.CharField(max_length=50)
    data = models.JSONField()
    design = models.JSONField(default=get_json_default)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, help_text="created time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated time")


class UserSelectedField(models.Model):

    """
    This models stores the selected fields of the user
    in the filter by column option.
    """

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    selected_fields = models.JSONField()
    select_type = models.CharField(max_length=255)


class CustomQuestion(models.Model):
    """
    Model containing custom questions
    """

    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, default=None, related_name="custom_questions")
    position = models.ManyToManyField(FormData, null=True, blank=True)
    question = models.TextField()
    description = models.TextField(null=True, blank=True, default=None)
    answer_type = models.CharField(max_length=100, null=True, blank=True, default=None)
    options = models.JSONField(default=None, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_mandatory = models.BooleanField(default=True)
    max = models.IntegerField(default=None, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, default=None, related_name="custom_questions")
    created_by_email = models.CharField(max_length=50, null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Answer(models.Model):
    question = models.ForeignKey(CustomQuestion, on_delete=models.CASCADE)
    position = models.ForeignKey(FormData, null=True, blank=True, on_delete=models.CASCADE)
    answer = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by_email = models.CharField(max_length=50, null=True, blank=True, default=None)
    updated_at = models.DateTimeField(auto_now=True)
