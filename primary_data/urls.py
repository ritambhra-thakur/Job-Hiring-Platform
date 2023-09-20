from django.urls import path

from .views import *

app_name = "primary_data"

urlpatterns = [
    path(
        "key-skill-autocomplete",
        KeySkillAutocomplete.as_view(create_field="skill"),
        name="key-skill-autocomplete",
    ),
    path(
        "university-autocomplete",
        UniversityAutocomplete.as_view(create_field="name"),
        name="university-autocomplete",
    ),
    path(
        "state-autocomplete",
        StateAutocomplete.as_view(),
        name="state-autocomplete",
    ),
    path(
        "city-autocomplete",
        CityAutocomplete.as_view(),
        name="city-autocomplete",
    ),
    # country
    path("country/api/v1/list/", GetAllCountry.as_view()),
    path("country/api/v1/create/", CreateCountry.as_view()),
    path("country/api/v1/get/<int:pk>/", GetCountry.as_view()),
    path("country/api/v1/update/<int:pk>/", UpdateCountry.as_view()),
    path("country/api/v1/delete/<int:pk>/", DeleteCountry.as_view()),
    # State
    path("state/api/v1/list/", GetAllStates.as_view()),
    path("state/api/v1/create/", CreateState.as_view()),
    path("state/api/v1/get/<int:pk>/", GetState.as_view()),
    path("state/api/v1/update/<int:pk>/", UpdateState.as_view()),
    path("state/api/v1/delete/<int:pk>/", DeleteState.as_view()),
    # City
    path("city/api/v1/list/", GetAllCities.as_view()),
    path("city/api/v1/create/", CreateCity.as_view()),
    path("city/api/v1/get/<int:pk>/", GetCity.as_view()),
    path("city/api/v1/update/<int:pk>/", UpdateCity.as_view()),
    path("city/api/v1/delete/<int:pk>/", DeleteCity.as_view()),
    # education
    path("university/api/v1/list/", GetAllUniversities.as_view()),
    path("university/api/v1/create/", CreateUniversity.as_view()),
    path("university/api/v1/get/<int:pk>/", GetUniversity.as_view()),
    path("university/api/v1/update/<int:pk>/", UpdateUniversity.as_view()),
    path("university/api/v1/delete/<int:pk>/", DeleteUniversity.as_view()),
    # in employment
    path("keyskill/api/v1/list/", GetAllKeySkill.as_view()),
    path("keyskill/api/v1/create/", CreateKeySkill.as_view()),
    path("keyskill/api/v1/get/<int:pk>/", GetKeySkill.as_view()),
    path("keyskill/api/v1/update/<int:pk>/", UpdateKeySkill.as_view()),
    path("keyskill/api/v1/delete/<int:pk>/", DeleteKeySkill.as_view()),
    # Address
    path("address/api/v1/list/", GetAllAddress.as_view()),
    path("address/api/v1/create/", CreateAddress.as_view()),
    path("address/api/v1/get/<int:pk>/", GetAddress.as_view()),
    path("address/api/v1/update/<int:pk>/", UpdateAddress.as_view()),
    path("address/api/v1/delete/<int:pk>/", DeleteAddress.as_view()),
    # EducationType
    path("education_type/api/v1/list/", GetAllEducationType.as_view()),
    path("education_type/api/v1/create/", CreateEducationType.as_view()),
    path("education_type/api/v1/get/<int:pk>/", GetEducationType.as_view()),
    path("education_type/api/v1/update/<int:pk>/", UpdateEducationType.as_view()),
    path("education_type/api/v1/delete/<int:pk>/", DeleteEducationType.as_view()),
    # Education
    path("education/api/v1/list/", GetAllEducation.as_view()),
    path("education/api/v1/create/", CreateEducation.as_view()),
    path("education/api/v1/get/<int:pk>/", GetEducation.as_view()),
    path("education/api/v1/update/<int:pk>/", UpdateEducation.as_view()),
    path("education/api/v1/delete/<int:pk>/", DeleteEducation.as_view()),
    # Experience
    path("experience/api/v1/list/", GetAllExperience.as_view()),
    path("experience/api/v1/create/", CreateExperience.as_view()),
    path("experience/api/v1/get/<int:pk>/", GetExperience.as_view()),
    path("experience/api/v1/update/<int:pk>/", UpdateExperience.as_view()),
    path("experience/api/v1/delete/<int:pk>/", DeleteExperience.as_view()),
    path("industries/api/v1/list/", ListIndustried.as_view()),
]
