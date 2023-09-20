from django.core.validators import MaxValueValidator
from django.db import models

from app.choices import *
from user.models import Profile

# from simple_history.models import HistoricalRecords


# Create your models here.
class Country(models.Model):
    """
    Country Model class is created with fields to add Country Details
    """

    name = models.CharField(max_length=200, help_text="Name of the Country")
    iso2 = models.CharField(max_length=50, blank=True, help_text="Enter ISO2")
    iso3 = models.CharField(max_length=50, blank=True, help_text="Enter ISO3")
    phone_code = models.CharField(blank=True, max_length=100, help_text="Enter your 10 digit number")
    capital = models.CharField(max_length=100, blank=True, help_text="Enter Name of the Capital")
    currency = models.CharField(max_length=100, blank=True, help_text="Currency type")
    description = models.TextField(blank=True, help_text="Add description")
    country_image = models.FileField(upload_to="media/", blank=True, null=True, help_text="Select country representative image")
    # history = HistoricalRecords(table_name="country_history")
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time in Country model",
    )
    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now=True,
        help_text="updated date and time",
    )

    def __str__(self):
        return self.name


class State(models.Model):
    """
    State Model class is created with fields to add State details
    """

    name = models.CharField(max_length=200, help_text="Enter your State")
    country = models.ForeignKey(
        Country,
        on_delete=models.RESTRICT,
        help_text="Choose your Country",
    )
    description = models.TextField(blank=True, help_text="Add description")
    # history = HistoricalRecords(table_name="state_history")
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.name


class City(models.Model):
    """
    City Model class is created with fields to add city details
    """

    name = models.CharField(max_length=200, help_text="Enter name of your city")
    country = models.ForeignKey(Country, on_delete=models.RESTRICT, help_text="Choose your Country")
    state = models.ForeignKey(State, on_delete=models.RESTRICT, help_text="Choose your State")
    description = models.TextField(blank=True, help_text="Add description")
    # history = HistoricalRecords(table_name="city_history")
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.name


# education
class University(models.Model):
    """
    University class Model class is created with fields to add university details
    """

    name = models.CharField(max_length=200, help_text="Enter name of your university")
    country = models.ForeignKey(Country, on_delete=models.RESTRICT, help_text="Choose your Country", null=True, blank=True)
    domain = models.CharField(
        max_length=200,
        blank=True,
        help_text="Enter Domain Name",
    )
    web_page = models.CharField(
        max_length=200,
        blank=True,
        help_text="Enter webpage details",
    )
    description = models.TextField(blank=True, help_text="Add description")
    # history = HistoricalRecords(
    #     table_name="university_history",
    # )
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time ",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.name


# in employment
class KeySkill(models.Model):
    """
    Keyskill Model class is created with fields to add keyskill details
    """

    skill = models.CharField(max_length=100, unique=True, help_text="Enter your Skills")
    verified = models.BooleanField(default=False, help_text="Tick the box")
    # history = HistoricalRecords(table_name="key_skill_history")
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.skill


class Address(models.Model):
    """
    Address Model class is created with fields to add Address details
    """

    address_one = models.CharField(max_length=100, null=True, blank=True, help_text="Enter Address 1")
    address_two = models.CharField(max_length=100, blank=True, null=True, help_text="Enter Address 2")
    address_three = models.CharField(max_length=100, blank=True, null=True, help_text="Enter Address 3")
    pin_code = models.PositiveIntegerField(
        validators=[MaxValueValidator(999999)],
        blank=True,
        null=True,
        help_text="Enter your pincode",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Choose your Country",
    )
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Choose your State",
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Choose your city",
    )
    # history = HistoricalRecords(table_name="address_history")
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def __str__(self):
        return f"{self.address_one} , {self.address_two} , {self.address_three} , {self.city} , \
            {self.state} , {self.country} , {self.pin_code}"


class EducationType(models.Model):
    """
    EducationType Model class is created with fields to add
    EducationType details
    """

    name = models.CharField(
        max_length=150,
        null=False,
        blank=False,
        help_text="Enter type of your Education",
    )
    # history = HistoricalRecords(table_name="education_type_history")
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.name


class Education(models.Model):
    """
    Education Model class is created with fields to add Education details
    """

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="education",
        help_text="Enter your profile details",
    )
    education_type = models.ForeignKey(
        EducationType,
        on_delete=models.CASCADE,
        help_text="Choose your Education type",
    )
    university = models.ForeignKey(
        University,
        related_name="university",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Select your university",
    )
    passing_out_year = models.IntegerField(
        choices=YEAR_CHOICES,
        default=datetime.datetime.now().year,
        help_text="Choose your passing out year",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Choose your Country",
    )
    # history = HistoricalRecords(table_name="education_history")

    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.profile.user.email


class Experience(models.Model):
    """
    Experience Model class is created with fields to add
    Experience details
    """

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="experience",
        help_text="Enter your profile",
    )
    company_name = models.CharField(
        max_length=250,
        null=False,
        blank=False,
        help_text="Enter your Company name",
    )
    role_and_responsibilities = models.TextField(blank=True, help_text="Describe your roles and responsibility")
    title = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Enter job tittle",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        help_text="Choose your Country",
    )
    skill = models.ManyToManyField(KeySkill, blank=True, help_text="Choose your skills and ")
    is_current_company = models.BooleanField(default=False, help_text="Tick mark your prefrence")
    join_date = models.DateField(null=True, blank=True, help_text="Joining Date")
    leave_date = models.DateField(null=True, blank=True, help_text="Leaving date")

    # history = HistoricalRecords(table_name="experience_history")

    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def admin_skill(self):
        return ",".join([str(p) for p in self.skill.all()])


class Industry(models.Model):
    name = models.CharField(max_length=150, null=False, blank=False, help_text="Enter industry name", unique=True)
    # history = HistoricalRecords(table_name="education_type_history")
    created_at = models.DateTimeField(
        null=True,
        blank=True,
        auto_now_add=True,
        help_text="created date and time",
    )
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, help_text="updated date and time")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "industries"
