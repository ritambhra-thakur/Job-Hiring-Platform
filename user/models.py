import datetime

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils.timezone import now
from django_extensions.db.fields import AutoSlugField
from pyexpat import model
import uuid
from app import choices
from company.models import Company, Department
from primary_data import models as primary_model
from role.models import Role

# from simple_history.models import HistoricalRecords


def default_json():
    return {"key": "value"}


# Create your models here.
def upload_user_avatar(instance, filename):
    """
    upload_user_avatar model class is created to add extentions and details like name, new name
    """
    extension = filename.split(".")[-1]
    new_name = str(datetime.datetime.now()).split(".")[0].replace(" ", "_")
    new_name = new_name + "." + extension
    return "avatars/{}/{}/".format(instance.id, new_name)


class AppUserManager(UserManager):
    """
    AppUserManager model class is created with functions to manage the
    user app
    """

    def get_by_natural_key(self, username):
        return self.get(email__iexact=username)

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()

        address_obj = primary_model.Address.objects.create()
        address_obj.save()
        profile_obj = Profile.objects.create(user=user, address=address_obj)
        profile_obj.save()

        return user

    """Created and saves a new superuser with given details."""

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create a Super Admin. Not to be used by any API. Only used for django-admin command.
        :param email:
        :param password:
        :param extra_fields:
        :return:
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        try:
            role_obj = Role.objects.get(slug="superuser")
        except:
            role_obj = Role.objects.create(name="superuser")

        try:
            company_obj = Company.objects.get(company_name="Infertalent")
        except:
            company_obj = Company.objects.create(company_name="Infertalent", url_domain="infer")

        extra_fields.setdefault("user_company", company_obj)
        extra_fields.setdefault("user_role", role_obj)
        user = self._create_user(email, password, **extra_fields)
        return user


"""Respents a user verification with some fields"""


class User(AbstractUser):
    """
    User model class is created with functions and fields to verify the email
    , otp and user role
    """

    middle_name = models.CharField(max_length=200, default=None, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    email_otp = models.CharField(max_length=10, null=True, blank=True)
    user_role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_role",
    )
    user_company = models.ForeignKey("company.Company", on_delete=models.CASCADE)
    encoded_id = models.CharField(max_length=20, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    # history = HistoricalRecords(table_name="user_history")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    manager = AppUserManager()

    def __str__(self):
        return self.username

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = "%s %s" % (self.first_name, self.last_name)
        full_name = "{}{}{}".format(
            self.first_name if self.first_name else "",
            " " + self.middle_name if self.middle_name else "",
            " " + self.last_name if self.last_name else "",
        )
        return full_name.strip()


class Profile(models.Model):
    """user profile class creation and one to one field is used in it and fields are
    phone number, otp, phone verified address and many other fields
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="Enter user number",
    )
    # id = models.CharField(primary_key=True, editable=False)
    # uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True)
    employee_id = models.CharField(max_length=20, default=None, null=True, blank=True, help_text="Enter User ID")
    source = models.CharField(max_length=20, default=None, null=True, blank=True, help_text="Enter Source")
    user_refereed_by = models.JSONField(default=default_json)
    secondary_email = models.EmailField(null=True, blank=True)

    phone_no = models.CharField(
        max_length=20,
        default=None,
        null=True,
        blank=True,
        help_text="Enter your contact number",
    )
    phone_otp = models.CharField(max_length=10, null=True, blank=True, help_text="Enter the OTP")  # creation for otp with max digit
    phone_verified = models.BooleanField(default=False, help_text="Select tick box")
    address = models.OneToOneField("primary_data.Address", on_delete=models.SET_NULL, help_text="Enter your Address", null=True, blank=True)
    experience_type = models.CharField(choices=choices.EXPERIENCE_TYPE, max_length=20, null=True, blank=True, help_text="user experience type")
    about = models.TextField(null=True, blank=True, help_text="Tell us about yourself")
    cover_letter = models.TextField(null=True, blank=True, help_text="Add description in Cover letter")
    skill = models.ManyToManyField(
        "primary_data.KeySkill",
        blank=True,
        help_text="Add your skills and ",
    )
    linked_url = models.TextField(blank=True, null=True, help_text="Enter your Linkedin URL")
    github_url = models.TextField(blank=True, null=True, help_text="Enter your github URL")
    personal_url = models.TextField(blank=True, null=True, help_text="Enter your personal URL")
    # was_candidate = models.BooleanField(default=None, null=True, blank=True)
    joined_date = models.DateTimeField(default=None, null=True, blank=True)
    # consent = models.BooleanField(default=False)
    # consent_given_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created date and time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.user.username  # used for to add username who has make the changes


class Token(models.Model):
    """
    token class created in model and fields are added like token, user, token type etc
    """

    token = models.CharField(max_length=300)
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    token_type = models.CharField(max_length=20, choices=choices.TOKEN_TYPE_CHOICES)
    device = models.JSONField(default=default_json)
    created_on = models.DateTimeField(default=now, null=True, blank=True)  # token created datetime field is used
    expired_on = models.DateTimeField(default=now, null=True, blank=True)  # token expired datetime field is used


""" ia class is created in model """


class Media(models.Model):
    """
    Media class created in model and fields are added to upload media, media name, field name
    eith unicode functions
    """

    # id = models.AutoField(primary_key=True)
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="media",
        help_text="Choose your profile",
    )
    media_file = models.FileField(upload_to="media/", blank=True, null=True, help_text="Select file")
    media_file_name = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        help_text="Enter Media file name",
    )
    field_name = models.CharField(max_length=250, blank=True, null=True, help_text="Enter field name")
    file_type = models.CharField(max_length=120, blank=True, null=True, help_text="Enter file type")
    is_active = models.BooleanField(default=True, help_text="Select your prefrences")
    is_deleted = models.BooleanField(default=False, help_text="Select your prefrences")
    can_delete = models.BooleanField(default=True, help_text="Select your prefrences")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Select your prefrences")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated time")
    # history = HistoricalRecords(table_name="media_history")

    def __unicode__(
        self,
    ):  # get a bunch of garbage that is not really informative.
        return self.id  # id will show who use this function

    # class Meta:
    #     db_table = "upload_media"
    #     indexes = [models.Index(fields=["id"])]


class ActivityLogs(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="media", help_text="Choose your user")
    applied_position = models.ForeignKey(
        "form.AppliedPosition",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_applied_position",
        help_text="Enter applied position",
    )
    candidate = models.ForeignKey(
        Profile, on_delete=models.CASCADE, null=True, blank=True, related_name="user_candidate", help_text="Enter candidate"
    )
    action_by = models.ForeignKey(
        Profile, on_delete=models.CASCADE, null=True, blank=True, related_name="user_action_by", help_text="Enter action by user"
    )
    description = models.CharField(max_length=250, blank=True, null=True, help_text="Enter description")
    type = models.CharField(max_length=120, blank=True, null=True, help_text="Enter type")
    details = models.CharField(max_length=120, blank=True, null=True, help_text="Enter Details")
    redirect = models.CharField(max_length=200, null=True, blank=True)
    type_id = models.IntegerField(null=True, blank=True, help_text="1. Position Approval, 2.Offer Approval, 3. Form Data, 4. Applied Position")
    created_at = models.DateTimeField(auto_now_add=True, help_text="created_time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated time")

    def __unicode__(self):
        return self.id


class Team(models.Model):
    """
    Model containing teams and its member along with the manager.
    """

    manager = models.ForeignKey("user.Profile", on_delete=models.CASCADE, related_name="team")
    members = models.ManyToManyField("user.Profile", help_text="add team members", blank=True, related_name="members")


class MediaText(models.Model):
    """
    This model contains the text data of the media file
    It is used in boolean search for the deep search
    based on the resume data.
    """

    media = models.ForeignKey(Media, related_name="media_text", on_delete=models.CASCADE)
    profile = models.ForeignKey(Profile, related_name="media_text", on_delete=models.CASCADE)
    text = models.TextField()


class OktaState(models.Model):
    state = models.CharField(max_length=255)
    code_challenge = models.CharField(max_length=255)


class GDPRAcceptence(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    accpted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, help_text="created_time")
    updated_at = models.DateTimeField(auto_now=True, help_text="updated time")


class DeviceVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    device = models.JSONField()
    otp = models.IntegerField()
    verified = models.BooleanField(default=False)


class ImportEmployeeFile(models.Model):
    file = models.FileField(upload_to="importEmployeesFile")
