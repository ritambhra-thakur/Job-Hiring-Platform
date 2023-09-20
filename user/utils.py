from django.db.models import Q

from user.models import Team


def get_members_form_data(obj, form_data, member_form_data):
    for member in obj.members.all():
        form_objs = list(form_data.filter(Q(hiring_manager=member.user.email) | Q(recruiter=member.user.email)).values_list("id", flat=True))
        member_form_data = member_form_data + form_objs
        team_objs = Team.objects.filter(manager=member)
        if team_objs:
            team_obj = team_objs[0]
            member_form_data = member_form_data + form_objs
            member_form_data += get_members_form_data(team_obj, form_data, member_form_data)
    return list(set(member_form_data))


def get_manager(obj):
    for i in Team.objects.all():
        if obj in i.members.all():
            return {"id": i.manager.id, "manager": i.manager.user.first_name}
    else:
        return {}
