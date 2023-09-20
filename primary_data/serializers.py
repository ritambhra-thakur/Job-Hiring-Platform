from rest_framework import serializers

from .models import (
    Address,
    City,
    Country,
    Education,
    EducationType,
    Experience,
    KeySkill,
    State,
    University,
)


class CountrySerializer(serializers.ModelSerializer):
    """
    CounrtySerializer class is created with Country Model and added all
    Country Model Field
    """

    class Meta:
        model = Country
        fields = "__all__"


class GetCountrySerializer(serializers.ModelSerializer):
    """
    GetCountrySerializer class is created with Country Model and added id,name
    Field from Country Model
    """

    class Meta:
        model = Country
        fields = ["id", "name", "phone_code"]


class StateSerializer(serializers.ModelSerializer):
    """
    StateSerializer class is created with State Model and added all
    Field from State Model
    """

    class Meta:
        model = State
        fields = "__all__"


class GetStateSerializer(serializers.ModelSerializer):
    """
    GetStateSerializer class is created with State Model and added id,
    name field from State Model
    """

    class Meta:
        model = State
        fields = ["id", "name", "country"]


class CitySerializer(serializers.ModelSerializer):
    """
    CitySerializer class is created with City Model and added
    all field from city Model
    """

    class Meta:
        model = City
        fields = "__all__"


class GetCitySerializer(serializers.ModelSerializer):
    """
    GetCitySerializer class is created with City Model and added
    id, name field from city Model
    """

    class Meta:
        model = City
        fields = ["id", "name", "state", "country"]


class UniversitySerializer(serializers.ModelSerializer):
    """
    UniversitySerializer class is created with University Model and added
    all field from UniversitySerializer Model
    """

    class Meta:
        model = University
        fields = "__all__"


class GetUniversitySerializer(serializers.ModelSerializer):
    """
    GetUniversitySerializer class is created with University Model and added
    id,name field from GetUniversitySerializer Model
    """

    class Meta:
        model = University
        fields = ["id", "name"]


class KeySkillSerializer(serializers.ModelSerializer):
    """
    KeySkillSerializer class is created with KeySkill Model and added
    all field from KeySkillSerializer Model
    """

    class Meta:
        model = KeySkill
        fields = "__all__"


class KeySkillListSerializer(serializers.ModelSerializer):
    """
    KeySkillListSerializer class is created with KeySkill Model and added
    all field from KeySkillListSerializer Model
    """

    class Meta:
        model = KeySkill
        read_only_fields = ("skill",)

        fields = (
            "id",
            "skill",
        )


# TODO: Code cleanup Pending
class AddressSerializer(serializers.ModelSerializer):
    """
    AddressSerializer class is created with Address Model and added
    all field from AddressSerializer Model
    """

    # country = CountrySerializer()
    # state = StateSerializer()
    # city = CitySerializer()

    class Meta:
        model = Address
        fields = "__all__"
        # fields = ("address_one", "address_two", "address_three", "pin_code")


class GetAddressSerializer(serializers.ModelSerializer):
    """
    GetAddressSerializer class is created with Address Model and added
    all field from GetAddressSerializer Model
    """

    country = GetCountrySerializer()
    state = GetStateSerializer()
    city = GetCitySerializer()

    class Meta:
        model = Address
        fields = "__all__"


class EducationTypeSerializer(serializers.ModelSerializer):
    """
    EducationTypeSerializer class is created with EducationType Model and added
    all field from EducationTypeSerializer Model
    """

    class Meta:
        model = EducationType
        fields = "__all__"


class EducationSerializer(serializers.ModelSerializer):
    """
    EducationSerializer class is created with Education Model and added
    all field from EducationSerializer Model
    """

    id = serializers.IntegerField(required=False)

    class Meta:
        model = Education
        fields = "__all__"


class GetEducationSerializer(serializers.ModelSerializer):
    """
    GetEducationSerializer class is created with Education Model and added
    all field from GetEducationSerializer Model
    """

    id = serializers.IntegerField(required=False)
    university = UniversitySerializer(read_only=True)
    country = CountrySerializer(read_only=True)
    education_type = EducationTypeSerializer(read_only=True)

    class Meta:
        model = Education
        fields = "__all__"


class GetExperienceSerializer(serializers.ModelSerializer):
    """
    GetExperienceSerializer class is created with Experience Model and added
    all field from GetExperienceSerializer Model
    """

    country = CountrySerializer()

    class Meta:
        model = Experience
        fields = "__all__"


class ExperienceSerializer(serializers.ModelSerializer):
    """
    ExperienceSerializer class is created with Experience Model and added
    all field from ExperienceSerializer Model
    """

    class Meta:
        model = Experience
        fields = "__all__"


class EducationTypeSerializer(serializers.ModelSerializer):
    """
    EducationTypeSerializer class is created with EducationType Model and added
    all field from EducationTypeSerializer Model
    """

    class Meta:
        model = EducationType
        fields = "__all__"
