from ast import For
from cmath import e

from company.models import Company
from form.models import Field, FieldType, Form


def save_master_data(company_id):
    company_obj = Company.objects.get(id=company_id)
    # try:
    form_name = ["position form", "Offer Form", "Application Form"]
    for i in range(3):
        form_obj = Form()
        form_obj.form_name = form_name[i]
        form_obj.description = form_name[i]
        # form_obj.form_type = i
        form_obj.company = company_obj
        form_obj.save()
        if form_name[i] == "Application Form":
            application_form_obj = form_obj

    field_name = [
        "First Name",
        "Last Name",
        "Email Address",
        "Mobile Number",
        "Country",
        "State",
        "City",
        "Experience Level",
        "Degree",
        "University",
        "Year of Completion",
        "Cover Letter",
        "Upload Document",
        "My Skills",
        "Linkedin URL",
        "Github URL",
        "Personal URL",
        "Type Message",
    ]
    field_block = [
        "Personal Information",
        "Personal Information",
        "Personal Information",
        "Personal Information",
        "Personal Information",
        "Personal Information",
        "Personal Information",
        "Personal Information",
        "Education Details",
        "Education Details",
        "Education Details",
        "Cover Letter",
        "Cover Letter",
        "Cover Letter",
        "Cover Letter",
        "Cover Letter",
        "Cover Letter",
        "Cover Letter",
    ]
    mandotory_field = [
        False,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        False,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    ]
    field_type = [
        2,
        2,
        3,
        2,
        3,
        3,
        2,
        4,
        3,
        3,
        7,
        4,
        8,
        1,
        3,
        3,
        3,
        9,
    ]

    for i in range(17):
        form_obj = Field()
        form_obj.field_name = field_name[i]
        form_obj.company = company_obj
        form_obj.form = application_form_obj
        form_obj.field_type = FieldType.objects.get(id=field_type[i])
        form_obj.field_block = field_block[i]
        form_obj.sort_order = i + 1
        form_obj.description = field_name[i]
        form_obj.is_mandatory = mandotory_field[i]

        form_obj.save()

    return True

    # except Exception as e:
    #     print(e)
    #     print("------------------------------------------------------>>>")
    #     return False
