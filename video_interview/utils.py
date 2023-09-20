import json
import random
import secrets
import string
from base64 import b64encode
from time import time

import jwt
import requests
from django.conf import settings

from company.models import ServiceProviderCreds


def generateToken():
    print(settings.ZOOM_CLIENT_ID)
    token = jwt.encode({"iss": settings.ZOOM_CLIENT_ID, "exp": time() + 5000}, settings.ZOOM_CLIENT_SK, algorithm="HS256")
    return token.decode()


meetingdetails = {
    "topic": "The title of your zoom meeting",
    "type": 2,
    "start_time": "2022-04-26T9: 7: 00",
    "duration": "30",
    "timezone": "Asia/Kolkata",
    "agenda": "test",
    "recurrence": {"type": 1, "repeat_interval": 1},
    "host_email": "rkswcud2@gmail.com",
    "settings": {
        "host_video": "False",
        "participant_video": "true",
        "join_before_host": "False",
        "mute_upon_entry": "False",
        "watermark": "true",
        "audio": "voip",
        "auto_recording": "cloud",
    },
}


def createMeeting(topic, start_data, start_time):
    headers = {"authorization": "Bearer " + generateToken(), "content-type": "application/json"}
    meetingdetails["start_time"] = "{}T{}".format(start_data, start_time)
    meetingdetails["topic"] = topic
    r = requests.post(f"https://api.zoom.us/v2/users/me/meetings", headers=headers, data=json.dumps(meetingdetails))

    print("\n creating zoom meeting ... \n")
    y = json.loads(r.text)
    print(y)
    join_URL = y["join_url"]
    meetingPassword = y["password"]
    return join_URL


def get_zoom_access_token(company):
    try:
        creds = ServiceProviderCreds.objects.get(company=company)
        if creds.zoom:
            # Get Creds
            account_id = creds.zoom.get("account_id")
            client_id = creds.zoom.get("client_id")
            client_secret = creds.zoom.get("client_secret")
            url = "https://zoom.us/oauth/token"
            # Generate auth token
            string_token = "{}:{}".format(client_id, client_secret).encode()
            auth_token = b64encode(string_token).decode()
            # get access token
            url = "https://zoom.us/oauth/token"
            payload = "grant_type=account_credentials&account_id={}".format(account_id)
            headers = {
                "Host": "zoom.us",
                "Authorization": "Basic {}".format(auth_token),
                "Content-Type": "application/x-www-form-urlencoded",
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            resp_data = response.json()
            if "access_token" in resp_data:
                return resp_data["access_token"], None
            else:
                return None, {"msg": "access_token not generated", "data": resp_data}
        else:
            return None, {"msg": "zoom creds not found", "data": creds.zoom}
    except Exception as e:
        return None, {"msg": "some error occured", "data": str(e)}


def get_zoom_user_id(htm):
    try:
        url = "https://api.zoom.us/v2/users/"
        access_token, data = get_zoom_access_token(htm.user_company)
        if access_token is None:
            return data
        payload = {}
        headers = {
            "Authorization": "Bearer {}".format(access_token),
        }
        response = requests.request("GET", url, headers=headers, data=payload)
        resp_data = response.json()
        if "users" in resp_data:
            user = next((item for item in resp_data["users"] if item["email"] == htm.email), None)
            if user:
                return user["id"], None
            else:
                return None, {"msg": "user not found in zoom account", "data": None}
        else:
            return None, {"msg": "user list not fetched from zoom", "data": resp_data}
    except Exception as e:
        return None, {"msg": "some error occured", "data": str(e)}


def create_zoom_meeting(htm, title, start_time, invitees):
    try:
        user_id, data = get_zoom_user_id(htm)
        if user_id is None:
            return data
        url = "https://api.zoom.us/v2/users/{}/meetings".format(user_id)
        payload = {
            "agenda": title,
            "default_password": False,
            "duration": 60,
            "password": "".join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(6)),
            "pre_schedule": False,
            "settings": {
                "allow_multiple_devices": True,
                "calendar_type": 1,
                "contact_email": htm.email,
                "contact_name": htm.get_full_name(),
                "encryption_type": "enhanced_encryption",
                "global_dial_in_countries": ["US"],
                "jbh_time": 0,
                "meeting_invitees": invitees,
                # "meeting_invitees": [{"email": "jchill@yopmail.com"}],
                "participant_video": False,
                "registrants_confirmation_email": True,
                "registrants_email_notification": True,
                "registration_type": 1,
            },
            # "start_time": "2023-02-17T07:32:55Z",
            "start_time": start_time,
            "timezone": "Aisa/Kolkata",
            "topic": title,
            "type": 2,
        }
        access_token, data = get_zoom_access_token(htm.user_company)
        if access_token is None:
            return data
        headers = {
            "Authorization": "Bearer {}".format(access_token),
            "Content-Type": "application/json",
        }
        response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
        resp_data = response.json()
        if "join_url" in resp_data:
            return resp_data
        else:
            return {"msg": "user list not fetched from zoom", "data": str(e)}
    except Exception as e:
        return {"msg": "user list not fetched from zoom", "data": str(e)}
