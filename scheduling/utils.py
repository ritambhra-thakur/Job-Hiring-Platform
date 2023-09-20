import requests

from company.models import Company, ServiceProviderCreds


def get_calendly_pat(company):
    try:
        creds = ServiceProviderCreds.objects.get(company=company)
        if creds.calendly:
            pat = creds.calendly.get("pat")
            return pat, creds
        else:
            return None
    except Exception as e:
        return None


def get_calendly_link(data):
    print(data)
    if "domain" in data:
        company = Company.objects.get(url_domain=data.get("domain"))
        pat, creds = get_calendly_pat(company)
        if pat:
            pass
        else:
            return False, "no access token found. add one"
    else:
        return False, "Creds not found!"

    try:
        url = "https://api.calendly.com/organization_memberships"

        querystring = {"email": data.get("email"), "organization": creds.calendly.get("organization")}

        headers = {"Content-Type": "application/json", "Authorization": "Bearer {}".format(pat)}

        resp = requests.request("GET", url, headers=headers, params=querystring)
        resp_data = resp.json()
        users_data = resp_data.get("collection")
        if users_data:
            user = users_data[0]["user"]
            scheduling_url = user["scheduling_url"]
            return True, scheduling_url
        else:
            return False, "This interviewer is not in you calendly organization. Please invite him."
    except Exception as e:
        return False, str(e)
