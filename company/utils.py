from form.models import UserSelectedField


def get_selected_fields(select_type, profile):
    selected_fields = UserSelectedField.objects.filter(profile=profile, select_type=select_type)
    if selected_fields:
        selected_fields = selected_fields.last().selected_fields
    else:
        selected_fields = ["Department Name", "Description", "Created Date"]
    return selected_fields

department_dict = {
    "Department Name": "department_name",
    "Description": "description",
    "Created Date": "created_at",
}

def get_value(data, target):
    for key, value in data.items():
        if isinstance(value, dict):
            yield from get_value(value, target)
        elif key == target:
            yield value
