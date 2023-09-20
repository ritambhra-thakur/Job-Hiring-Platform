import csv
import datetime
import io
import json
import math
import operator
import os
import random
import re
import secrets
import string
from functools import reduce
import fitz
import phonenumbers
import pyotp
import PyPDF2
import requests
from cryptography.fernet import Fernet
from affinda import AffindaAPI, TokenCredential
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.postgres.search import SearchConfig, SearchQuery, SearchVector
from django.db.models import ForeignKey, Q
from django.http import Http404, HttpResponse
from django.template import Context, Template
from msrest import Serializer
from psycopg2.extensions import adapt
from PyPDF2 import PdfFileReader, PdfFileWriter, PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from rest_framework import serializers
from rest_framework.views import exception_handler

from app.response import ResponseBadRequest, ResponseNotFound, ResponseOk
from form.models import AppliedPosition, FormData
from notification.models import Notifications
from resume_parser.models import Affinda
from resume_parser.serializers import AffindaSerializer
from user.models import Team, User
from user.serializers import (
    ActivityLogsSerializer,
    CustomProfileSerializer,
    ProfileSerializer,
)

MIN_PASSWORD_LENGTH = 5


class FormDataSerializer(serializers.ModelSerializer):
    hiring_manager_name = serializers.SerializerMethodField(read_only=True)
    recruiter_name = serializers.SerializerMethodField(read_only=True)
    sposition_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = FormData
        fields = "__all__"

    def get_hiring_manager_name(self, obj):
        try:
            user_obj = User.objects.get(email=obj.hiring_manager)
            return user_obj.get_full_name()
        except:
            return obj.hiring_manager

    def get_recruiter_name(self, obj):
        try:
            user_obj = User.objects.get(email=obj.recruiter)
            return user_obj.get_full_name()
        except:
            return obj.recruiter

    def get_sposition_id(self, obj):
        return obj.show_id


def validate_email(email):
    """
    Function to validate email address
    :param email:
    :return:
    """
    if not email:
        return False
    regex = "^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$"
    if re.search(regex, email):
        return True
    return False


def validate_password(password):
    """
    Function to validate a password
    :param password:
    :return:
    """
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return False
    return True


def validate_phone_number(phone):
    """
    from app.util import validate_phone_number as vpn
    """
    if not phone:
        return False
    if str(phone).startswith("+"):
        ph = phonenumbers.parse(phone)
        return phonenumbers.is_valid_number(ph)
    if len(phone) > 15:
        return False
    regex = r"[123456789]\d{5}$"
    if re.search(regex, phone):
        return True
    return False


def permission_error_handler(exc, context):
    """
    Function to modify the results when the permissions are not sent
    """
    response = exception_handler(exc, context)
    if response.status_code == 403:
        response.data = {
            "success": 0,
            "error": response.data["detail"],
            "status": 403,
        }
    if response.status_code == 401:
        response.data = {
            "success": 0,
            "error": response.data["detail"],
            "status": 401,
        }
    return response


def new_password_matches_old_password(password, password_hash):
    """
    Function to check if the new password matches the currently set password.
    :param password: new raw password
    :param password_hash: current password hash.
    :return: True if new password matches the old one.
    """
    if not password_hash:
        return False
    salt = password_hash.split("$")[-2]
    new_hash = make_password(password, salt)
    return new_hash == password_hash


def is_string_a_number(string):
    """
    Function to check if a String is a number or not
    """
    if None:
        return None
    try:
        return float(string)
    except:
        return False


def get_user_object(company_domain, email):
    """
    Function to get user object from user table
    """
    try:
        return User.objects.get(email=email, user_company__url_domain=company_domain)
    except:
        return None


def generate_otp():
    """
    Function to get otp
    """
    otp = pyotp.random_base32()
    time_otp = pyotp.TOTP(otp, interval=300)

    # TODO: update otp length based on UI
    return time_otp.now()[:5]


def generate_file_name(prefix, extension, suffix=None):
    time_stamp = str(datetime.datetime.now()).split(".")[0].replace(" ", "-")
    if suffix:
        name = "{}-{}-{}.{}".format(prefix, time_stamp, suffix, extension)
    else:
        name = "{}-{}.{}".format(prefix, time_stamp, extension)
    return name


def custom_get_object(pk, model_name, get_field=None):
    if get_field is None:
        get_field = "id"
    return model_name.objects.get(**{get_field: pk})


def custom_get_pagination(request, model_obj, model_name, model_serializer, search_keys):
    search_type = "or"
    kwargs = []
    data = request.GET
    if data.get("search"):
        search = data.get("search")
    else:
        search = ""

    if data.get("page"):
        page = data.get("page")
    else:
        page = 1

    if data.get("perpage"):
        limit = data.get("perpage")
    else:
        limit = str(settings.PAGE_SIZE)

    pages, skip = 1, 0

    sort_field = data.get("sort_field")

    sort_dir = data.get("sort_dir")
    if page and limit:
        page = int(page)
        limit = int(limit)
        skip = (page - 1) * limit

    no_of_keys = len(search_keys)

    if no_of_keys > 0:
        for keyname in search_keys:
            kwargs.append(Q(**{keyname: search}))

        if search_type == "and":
            model_obj = model_obj.filter(reduce(operator.and_, kwargs))
        else:
            model_obj = model_obj.filter(reduce(operator.or_, kwargs))

    count = model_obj.count()

    if sort_field is not None and sort_dir is not None:
        if sort_dir == "asc":
            try:
                model_obj = model_obj.order_by(sort_field)
            except:
                model_obj = model_obj.order_by("id")

        elif sort_dir == "desc":
            try:
                model_obj = model_obj.order_by("-" + sort_field)
            except:
                model_obj = model_obj.order_by("-id")

    if page and limit:
        model_obj = model_obj[skip : skip + limit]

        pages = math.ceil(count / limit) if limit else 1

    if count:
        serializer = model_serializer(model_obj, many=True, context={"request": request}).data
        data = {
            "data": serializer,
            "meta": {
                "page": page,
                "total_pages": pages,
                "perpage": limit,
                "sort_dir": sort_dir,
                "sort_field": sort_field,
                "total_records": count,
            },
        }

        return data
    else:
        return "Search query has no match"


def custom_search(request, model_obj, search_keys):
    search_type = "or"
    kwargs = []
    data = request.GET
    if data.get("search"):
        search = data.get("search")
    else:
        search = ""

    if data.get("page"):
        page = data.get("page")
    else:
        page = 1

    if data.get("perpage"):
        limit = data.get("perpage")
    else:
        limit = str(settings.PAGE_SIZE)

    pages, skip = 1, 0

    sort_field = data.get("sort_field")

    sort_dir = data.get("sort_dir")
    if page and limit:
        page = int(page)
        limit = int(limit)
        skip = (page - 1) * limit

    no_of_keys = len(search_keys)

    if no_of_keys > 0:
        for keyname in search_keys:
            kwargs.append(Q(**{keyname: search}))

        if search_type == "and":
            model_obj = model_obj.filter(reduce(operator.and_, kwargs))
        else:
            model_obj = model_obj.filter(reduce(operator.or_, kwargs))
    model_obj = model_obj.distinct()
    count = model_obj.count()
    if sort_field is not None and sort_dir is not None:
        if sort_dir == "asc":
            try:
                model_obj = model_obj.order_by(sort_field)
            except:
                model_obj = model_obj.order_by("id")

        elif sort_dir == "desc":
            try:
                model_obj = model_obj.order_by("-" + sort_field)
            except:
                model_obj = model_obj.order_by("-id")

    if page and limit:
        model_obj = model_obj[skip : skip + limit]

        pages = math.ceil(count / limit) if limit else 1
    meta = {
        "page": page,
        "total_pages": pages,
        "perpage": limit,
        "sort_dir": sort_dir,
        "sort_field": sort_field,
        "total_records": count,
    }
    return model_obj, meta


def sort_data(model_obj, sort_field, sort_dir):
    if sort_field is not None and sort_dir is not None:
        if sort_dir == "asc":
            try:
                model_obj = model_obj.order_by(sort_field)
            except:
                model_obj = model_obj.order_by("id")

        elif sort_dir == "desc":
            try:
                model_obj = model_obj.order_by("-" + sort_field)
            except:
                model_obj = model_obj.order_by("-id")

    else:
        model_obj = model_obj.order_by("id")

    return model_obj


def search_data(model_obj, model_name, search, search_keys=None):
    search_type = "or"
    kwargs = []
    if search_keys is None:
        a = "__icontains"
        b = "__id__icontains"
        search_keys = [i.name + b if isinstance(i, ForeignKey) else i.name + a for i in model_name._meta.fields]
    no_of_keys = len(search_keys)
    if no_of_keys > 0:
        for keyname in search_keys:
            kwargs.append(Q(**{keyname: search}))
        if search_type == "and":
            model_obj = model_obj.filter(reduce(operator.and_, kwargs))
        else:
            model_obj = model_obj.filter(reduce(operator.or_, kwargs))
    return model_obj


def paginate_data(request, model_obj, model_name):
    data = request.GET
    if data.get("page"):
        page = data.get("page")
    else:
        page = 1

    if data.get("perpage"):
        limit = data.get("perpage")
    else:
        limit = str(settings.PAGE_SIZE)
    pages, skip = 1, 0
    if page and limit:
        page = int(page)
        limit = int(limit)
        skip = (page - 1) * limit
    try:
        count = model_obj.count()
    except:
        count = len(model_obj)
    if page and limit:
        model_obj = model_obj[skip : skip + limit]
        pages = math.ceil(count / limit) if limit else 1
    result = {
        "paginate_data": model_obj,
        "page": page,
        "total_pages": pages,
        "perpage": limit,
        "total_records": count,
    }
    return result


def create_activity_log(data):
    serializer = ActivityLogsSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return True
    else:
        return False


def encryption(data):
    # data=json.loads(request.data.decode('utf-8'))
    data1 = str(data)
    data2 = {
        1: "xp0p",
        2: "uyut1",
        3: "jggb2nvhv",
        4: "gyhn",
        5: "kgikb65",
        6: "uygnb5vjhv",
        7: "vjhffyvf987886",
        8: "jfbvc7000))",
        9: "gza8",
        0: "9yfy",
    }
    res1 = ""
    for i in data1:
        res1 += data2[int(i)] + "K"
    return res1


def decryption(data):
    # data=json.loads(request.data.decode('utf-8'))
    data1 = data
    data3 = data1.split("K")
    data3.pop()
    data2 = {
        1: "xp0p",
        2: "uyut1",
        3: "jggb2nvhv",
        4: "gyhn",
        5: "kgikb65",
        6: "uygnb5vjhv",
        7: "vjhffyvf987886",
        8: "jfbvc7000))",
        9: "gza8",
        0: "9yfy",
    }
    new_dict = dict([(value, key) for key, value in data2.items()])
    res2 = ""
    for i in data3:
        res2 += str(new_dict[i])
    return res2


def next_end_date(a):
    res = a.split("-")
    year = res[0]
    month = res[1]
    day = res[2]
    if int(month) == 12:
        year = int(year) + 1
        month = 1
    elif int(month) < 12:
        month = int(month) + 1
    if day != "01":
        day = "01"
    if month <= 9:
        month = "0" + str(month)
    data = str(year) + "-" + str(month) + "-" + str(day)
    return data


def generate_offer_pdf(file, id, context={}):
    my_Style = ParagraphStyle("My Para style", fontName="Times-Roman", fontSize=10, borderPadding=(20, 20, 20), leading=9, alignment=0)

    pdfReader = PdfFileReader(file)
    # doc = fitz.open(file.url)
    request = requests.get(file.url)
    filestream = io.BytesIO(request.content)
    doc = fitz.open(stream=filestream, filetype="pdf")
    # no_of_pages = pdfReader.numPages
    page_content = []
    for page in doc:
        try:
            # pageObj = pdfReader.getPage(number)
            # string_content = pageObj.extractText()
            # print(string_content)
            # string_content = string_content.replace("  ", " ")
            string_content = page.get_text()
            temp = Template(string_content)
            temp_content = Context(context)
            content = temp.render(temp_content)
            page_content.append(content)
        except Exception as e:
            print(e)
            raise ValueError("Please place the macros in between of {{ and }}. Do not add spaces anywhere between these macros.")
    c = canvas.Canvas("../Offer_{}.pdf".format(id), pagesize=A4)
    width, height = A4
    for page in page_content:
        content = page.replace("\n", "<br /><br />")
        pdf_page = Paragraph(content, style=my_Style)
        w, h = pdf_page.wrap(width - 100, height)
        pdf_page.drawOn(c, 50, height - h - 25)
        c.showPage()
    c.save()


def generate_offer_id():
    letters = string.ascii_uppercase + string.digits
    offer_id = "".join(secrets.choice(letters) for i in range(6))
    return offer_id


def generate_password():
    letters = string.ascii_uppercase + string.digits
    password = "".join(secrets.choice(letters) for i in range(12))
    return password


def get_team_member(obj):
    members = []
    for member in obj.members.all():
        temp_member = CustomProfileSerializer(member)
        member_data = temp_member.data
        members.append(member_data)
    return members


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


def get_hiring_managers_form_data(obj, form_data, member_form_data):
    for member in obj.members.all():
        form_objs = list(form_data.filter(hiring_manager=member.user.email).values_list("id", flat=True))
        member_form_data = member_form_data + form_objs
        team_objs = Team.objects.filter(manager=member)
        if team_objs:
            team_obj = team_objs[0]
            member_form_data = member_form_data + form_objs
            member_form_data += get_hiring_managers_form_data(team_obj, form_data, member_form_data)
    return list(set(member_form_data))


def send_instant_notification(message, user, slug=None, applied_position=None, form_data=None, event_type=None):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("user-{}".format(user.profile.id), {"type": "chat.message", "msg": message})
    additional_info = {}
    if applied_position is not None:
        additional_info["form_data"] = FormDataSerializer(applied_position.form_data).data
        additional_info["applied_position"] = applied_position.id
        additional_info["applied_profile_id"] = applied_position.applied_profile.id
        additional_info["candidate_name"] = applied_position.applied_profile.user.get_full_name()
        additional_info["position_title"] = applied_position.form_data.form_data.get("job_title")
    if form_data is not None:
        additional_info["form_data"] = FormDataSerializer(form_data).data
    Notifications.objects.create(user=user, title=message, redirect_slug=slug, additional_info=additional_info, event_type=event_type)
    return True


def send_reminder(message, user, slug=None, applied_position=None, form_data=None):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("user-{}".format(user.profile.id), {"type": "chat.message", "msg": message})
    additional_info = {}
    if applied_position is not None:
        additional_info["form_data"] = FormDataSerializer(applied_position.form_data).data
        additional_info["applied_position"] = applied_position.id
        additional_info["applied_profile_id"] = applied_position.applied_profile.id
        additional_info["candidate_name"] = applied_position.applied_profile.user.get_full_name()
        additional_info["position_title"] = applied_position.form_data.form_data.get("job_title")
    if form_data is not None:
        additional_info["form_data"] = FormDataSerializer(form_data).data
    Notifications.objects.create(user=user, title=message, redirect_slug=slug, additional_info=additional_info)
    return True


def verify_device(message, user_id):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("user-verify-{}".format(user_id), {"type": "chat.message", "msg": message})
    return True


def get_all_members_email(team, members_email):
    for member in team.members.all():
        members_email.append(member.user.email)
        team_objs = Team.objects.filter(manager=member)
        if team_objs:
            team_obj = team_objs[0]
            get_all_members_email(team_obj, members_email)
    return list(set(members_email))


def get_all_applied_position(profile):
    try:
        team = Team.objects.filter(manager=profile)
        if team:
            team_obj = team[0]
            emails = get_all_members_email(team_obj, [profile.user.email])
            return list(
                AppliedPosition.objects.filter(Q(form_data__hiring_manager__in=emails) | Q(form_data__recruiter__in=emails)).values_list(
                    "id", flat=True
                )
            )
        else:
            return list(
                AppliedPosition.objects.filter(
                    Q(form_data__hiring_manager=profile.user.email) | Q(form_data__recruiter=profile.user.email)
                ).values_list("id", flat=True)
            )
    except Exception as e:
        print(e)
        return []


def download_csv(request, queryset, field_names=None):
    model = queryset.model
    model_fields = model._meta.fields + model._meta.many_to_many
    if field_names:
        pass
    else:
        field_names = [field.name for field in model_fields]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="export.csv"'

    writer = csv.writer(response, delimiter=",")
    writer.writerow(field_names)
    for row in queryset:
        values = []
        for field in field_names:
            value = getattr(row, field)
            if callable(value):
                try:
                    value = value() or ""
                except:
                    value = "Error retrieving value"
            if value is None:
                value = ""
            values.append(value)
        writer.writerow(values)
    return response


def add_quotes(s):
    return re.sub(r"((?=\S)(?:\s*(?!(?:AND|OR|NOT)\b)\b\w+){2,}\b)", r'"\1"', s)
    # new  = ''
    # new_list = []
    # splited = s.split()
    # for i in range(0, len(splited)):
    #     word = splited[i]
    #     if word in ['AND', 'OR', 'NOT']:
    #         if len(new_list) > 1:
    #             pharase = ' '.join(x for x in new_list)
    #             if pharase.endswith(")"):
    #                 pharase = pharase.replace(")", '"')
    #                 new += '"{})'.format(pharase)
    #             elif pharase.startswith("("):
    #                 pharase = pharase.replace("(", '"')
    #                 new += '({}"'.format(pharase)
    #             else:
    #                 new += '"{}"'.format(pharase)
    #             new += " {} ".format(word)
    #         else:
    #             pharase = ' '.join(x for x in new_list)
    #             new += '{}'.format(pharase)
    #             new += " {} ".format(word)
    #         new_list = []
    #     elif i==len(splited)-1:
    #         new_list.append(word)
    #         pharase = ' '.join(x for x in new_list)
    #         if len(new_list) > 1:
    #             if pharase.endswith(")"):
    #                 pharase = pharase.replace(")", '"')
    #                 new += '"{})'.format(pharase)
    #             elif pharase.startswith("("):
    #                 pharase = pharase.replace("(", '"')
    #                 new += '({}"'.format(pharase)
    #             else:
    #                 new += '"{}"'.format(pharase)
    #         else:
    #             new += '{}'.format(pharase)
    #     else:
    #         new_list.append(word)
    # return new


from django.db.models import Value


class PrefixedPhraseQuery(SearchQuery):
    """
    Alter the tsquery executed by SearchQuery
    """

    def __init__(self, value, output_field=None, *, config=None, invert=False, search_type="websearch"):
        self.value = value
        self.function = self.SEARCH_TYPES.get(search_type)
        if self.function is None:
            raise ValueError("Unknown search_type argument '%s'." % search_type)
        if not hasattr(value, "resolve_expression"):
            value = Value(value)
        expressions = (value,)
        self.config = SearchConfig.from_parameter(config)
        if self.config is not None:
            expressions = (self.config,) + expressions
        self.invert = invert
        super().__init__(*expressions, output_field=output_field)

    def as_sql(self, compiler, connection):
        print(self.value)
        # Or <-> available in Postgres 9.6
        value = adapt("%s:*" % " & ".join(self.value.split()))

        if self.config:
            config_sql, config_params = compiler.compile(self.config)
            template = "to_tsquery({}::regconfig, {})".format(config_sql, value)
            params = config_params

        else:
            template = "to_tsquery({})".format(value)
            params = []

        if self.invert:
            template = "!!({})".format(template)

        return template, params


def boolean_search(search, company):
    # search = search.replace('AND', '&')
    # search = search.replace('OR', '|')
    # search = search.replace('NOT', '!')
    search = add_quotes(search)
    search = search.replace("NOT ", "-")
    # search = search.replace('e ', ' ')
    new_search = search

    # Get resume data
    resume_data = None

    # new_search = ''
    # last_char = None
    # count = 1
    # length = len(search)
    # for char in search:
    #     if char == ' ':
    #         if last_char:
    #             new_search += ":*"
    #     if count == length:
    #         if char.isalpha:
    #             new_search += char
    #             new_search += ":*"
    #             break
    #     new_search += char
    #     last_char = char.isalpha()
    #     count += 1
    try:
        queryset = User.objects.annotate(
            search=SearchVector(
                "first_name",
                "last_name",
                "profile__address__country__name",
                "profile__address__state__name",
                "profile__address__city__name",
                "profile__department__department_name",
                "profile__skill__skill",
                "profile__experience__title",
                "profile__media_text__text",
            )
        ).filter(search=SearchQuery(new_search, search_type="websearch"))
        queryset = queryset.filter(user_company=company).filter(user_role__name="candidate").distinct("id")
        return queryset
    except Exception as e:
        print(e)
    # operations = []
    # splited = None
    # while search:
    #     sub_search = search
    #     splited = None
    #     for char in sub_search:
    #         if char in ['A', 'O', '(']:
    #             print(char)
    #             splited = search.split(' '+char)
    #             print(splited)
    #             temp_dict = {}
    #             temp_dict['term'] = splited[0]
    #             temp_dict['opperation'] = char
    #             operations.append(temp_dict)
    #             if char == 'A':
    #                 idx = sub_search.find('A')
    #                 search = sub_search[idx+4:]
    #             if char == 'O':
    #                 idx = sub_search.find('O')
    #                 search = sub_search[idx+3:]
    #             if char == '(':
    #                 idxe = sub_search.find(')')
    #                 search = sub_search[idxe+1:]
    #             print(search)
    #         else:
    #             continue
    #     if splited:
    #         pass
    #     else:
    #         break

    # and_op = search.find(' AND ')
    # or_op = search.find(' OR ')
    # beackets_op = search.find('(')
    # if beackets_op:
    #     pass
    # else:
    #     pass
    # for idx, char in enumerate(search):
    #     if char in ['A', 'O', '(', ')']:


# s = 'rajan OR (ramesh AND rahul)'
# new  = ''
# new_list = []
# splited = s.split()
# for i in range(0, len(splited)):
#     word = splited[i]
#     if word in ['AND', 'OR', 'NOT']:
#         if len(new_list) > 1:
#             pharase = ' '.join(x for x in new_list)
#             if pharase.endswith(")"):
#                 pharase = pharase.replace(")", '"')
#                 new += '"{})'.format(pharase)
#             elif pharase.startswith("("):
#                 pharase = pharase.replace("(", '"')
#                 new += '({}"'.format(pharase)
#             else:
#                 new += '"{}"'.format(pharase)
#             new += " {} ".format(word)
#         else:
#             pharase = ' '.join(x for x in new_list)
#             new += '{}'.format(pharase)
#             new += " {} ".format(word)
#         new_list = []
#     elif i==len(splited)-1:
#         new_list.append(word)
#         pharase = ' '.join(x for x in new_list)
#         if len(new_list) > 1:
#             if pharase.endswith(")"):
#                 pharase = pharase.replace(")", '"')
#                 new += '"{})'.format(pharase)
#             elif pharase.startswith("("):
#                 pharase = pharase.replace("(", '"')
#                 new += '({}"'.format(pharase)
#             else:
#                 new += '"{}"'.format(pharase)
#         else:
#             new += '{}'.format(pharase)
#     else:
#         new_list.append(word)


def read_pdf(file):
    reader = PyPDF2.PdfReader(file)
    content = ""
    for page in reader.pages:
        content += " " + page.extract_text()
    return content


def read_doc(file):
    data = {"file": file}
    token = settings.AFFINDA_KEY
    credential = TokenCredential(token=token)
    client = AffindaAPI(credential=credential)
    serializer = AffindaSerializer(
        data=data,
    )
    if serializer.is_valid():
        data = serializer.save()
        file_path = Affinda.objects.get(id=int(data.id)).file
        url = "https://" + settings.AWS_S3_CUSTOM_DOMAIN + "/media/" + str(file_path)
        resume = client.create_resume(url=url)
        data = resume.as_dict()
    return str(data)


def send_meeting_link(link, state):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("state-{}".format(state), {"type": "chat.message", "msg": link})
    return True


def send_login_approval(email, response):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("email-{}".format(email), {"type": "chat.message", "msg": response})
    return True
