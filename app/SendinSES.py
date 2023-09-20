import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from json import dumps

import requests
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from rest_framework import status as drf_status

from app import choices
from app.encryption import encrypt
from app.response import ResponseBadRequest
from company.models import Company
from form.models import AppliedPosition, OfferLetter
from main import settings
from role.models import Role
from stage.models import PositionStage
from url_shortener.models import ShortURL
from user.models import Profile, User


def send_email_otp(request, user_email, email_otp, recipient=None, sender=None):
    """
    Send Email OTP
    """

    if user_email and email_otp:
        if recipient is None:
            recipient = ""
        if sender is None:
            sender = "Infertalents"
        else:
            try:
                com_obj = Company.objects.filter(company_name=sender)
                if len(com_obj) > 0:
                    com_obj = com_obj[0]
                    role_obj = Role.objects.get(name="admin", company=com_obj.id)
                    sender = User.objects.get(user_role=role_obj.id).first_name
                else:
                    pass
                    # sender = "Infertalents"
            except:
                pass

        # message = "Dear {},\nWe recently received a request to verify your email address. To verify your email, please enter the following one-time  password \n\n OTP: {} \n This OTP is valid for 24hrs. If you do not enter the OTP, you will need to register again. \n Once you have entered the OTP, your email address will be verified. \n Thank you for your time. \n\n\n Sincerely, \n {} ".format(
        #     recipient, email_otp, sender
        # )
        context = {"recipient": recipient, "email_otp": email_otp, "sender": sender}
        # message = "Your One Time Passcode is {} to activate your account.".format(email_otp)
        from_email = settings.EMAIL_HOST_USER
        to_email = user_email

        body_msg = render_to_string("otp_email.html", context)

        msg = EmailMultiAlternatives("Email Verification<Don't Reply>", body_msg, "Email Verification<Don't Reply>", [to_email])
        msg.content_subtype = "html"

        try:
            msg.send()
            return True
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": drf_status.HTTP_400_BAD_REQUEST,
                    "message": "Something wrong contact admin",
                }
            )
    else:
        return ResponseBadRequest(
            {
                "data": None,
                "code": drf_status.HTTP_400_BAD_REQUEST,
                "message": "Something wrong contact admin",
            }
        )


def email_verification_success(request, user_email):
    """
    Email OTP verification success
    """

    if user_email:
        message = "Your Account is activated"
        from_email = settings.EMAIL_HOST_USER
        to_email = user_email
        try:
            return send_mail(
                "Account activated<Don't Reply>",
                message,
                "Account activated<Don't Reply>",
                [to_email],
                fail_silently=False,
            )
        except:
            return ResponseBadRequest(
                {
                    "data": None,
                    "code": drf_status.HTTP_400_BAD_REQUEST,
                    "message": "Something wrong contact admin",
                }
            )
    else:
        return ResponseBadRequest(
            {
                "data": None,
                "code": drf_status.HTTP_400_BAD_REQUEST,
                "message": "Something wrong contact admin",
            }
        )


def send_reset_password_mail(request, user_email, email_body):
    """
    Send Reset Password Mail
    """

    if user_email and email_body:
        Message = email_body
        from_email = settings.EMAIL_HOST_USER
        to_email = user_email
        try:
            send_mail(
                "Reset your passsword<Don't Reply>",
                Message,
                "Reset your passsword<Don't Reply>",
                [to_email],
                fail_silently=False,
            )
        except Exception as e:
            print(e)
    return None


def send_custom_email(tittle, body, to_email, first_name=None, company_name=None, password=None):
    from_email = settings.EMAIL_HOST_USER

    context = {"link": body, "employee_name": first_name}
    if password:
        context["password"] = password
    if company_name:
        context["company"] = company_name.title()
    context["email"] = to_email
    body_msg = render_to_string("email_send.html", context)

    msg = EmailMultiAlternatives(tittle, body_msg, tittle, [to_email])
    msg.content_subtype = "html"
    msg.send()
    return True


def send_reminder_email(tittle, body, to_email, first_name=None, company_name=None):
    from_email = settings.EMAIL_HOST_USER

    context = {"link": body, "employee_name": first_name}
    if company_name:
        context["company"] = company_name.title()
    context["email"] = to_email
    body_msg = body

    msg = EmailMultiAlternatives(tittle, body_msg, tittle, [to_email])
    msg.content_subtype = "html"
    msg.send()
    return True


def send_add_candidate_email(to_email, tittle, body):
    from_email = settings.EMAIL_HOST_USER

    context = {"body": body}
    body_msg = render_to_string("add_candidate_email.html", context)

    msg = EmailMultiAlternatives(tittle, body_msg, tittle, [to_email])
    msg.content_subtype = "html"
    msg.send()
    return True


def send_scorecard_email(to_email, tittle, body):
    from_email = settings.EMAIL_HOST_USER

    context = {"link": body}
    body_msg = render_to_string("scorecard_email.html", context)

    msg = EmailMultiAlternatives(tittle, body_msg, tittle, [to_email])
    msg.content_subtype = "html"
    msg.send()
    return True


def send_postion_approval_mail(
    approval_obj,
):
    from_email = settings.EMAIL_HOST_USER
    to_email = approval_obj.profile.user.email
    approval_id = encrypt(approval_obj.id)
    decline_link = "https://{}.{}/hiring-manager/dashboard#newHiRes".format(approval_obj.profile.user.user_company.url_domain, settings.DOMAIN_NAME)
    accept_link = "https://{}.{}/form/accept-position-approval-mail/{}/".format(
        approval_obj.profile.user.user_company.url_domain, settings.DOMAIN_NAME, approval_id
    )
    context = {"decline_link": decline_link, "accept_link": accept_link}
    body_msg = render_to_string("position_approval_email.html", context)
    title = "Position Approval Confirmation"
    msg = EmailMultiAlternatives(title, body_msg, title, [to_email])
    msg.content_subtype = "html"
    msg.send()
    return True


def send_offer_approval_mail(approval_obj):
    from_email = settings.EMAIL_HOST_USER
    to_email = approval_obj.profile.user.email
    decline_link = "https://{}.{}/hiring-manager/dashboard#newHiRes".format(approval_obj.profile.user.user_company.url_domain, settings.DOMAIN_NAME)
    try:
        applied_position_obj = AppliedPosition.objects.get(applied_profile=approval_obj.candidate.id, form_data=approval_obj.position.id)
        applied_position_id = applied_position_obj.id
    except:
        return False
    approval_id = encrypt(approval_obj.id)
    applied_position_id = encrypt(applied_position_id)
    accept_link = "https://{}.{}/form/accept-offer-approval-mail/{}/{}/".format(
        approval_obj.profile.user.user_company.url_domain, settings.DOMAIN_NAME, approval_id, applied_position_id
    )
    context = {"decline_link": decline_link, "accept_link": accept_link}
    body_msg = render_to_string("offer_approval_email.html", context)
    title = "Offer Approval Confirmation"
    msg = EmailMultiAlternatives(title, body_msg, title, [to_email])
    msg.content_subtype = "html"
    msg.send()
    return True


def get_candidate_visibility_link(obj):
    if obj.candidate_visibility:
        domain_name = settings.DOMAIN_NAME
        if obj.company.url_domain == "localhost":
            complete_url = "http://localhost:3000/guest/search-job-description/{}/".format(obj.id)
        else:
            complete_url = "https://{}.{}/guest/search-job-description/{}/".format(obj.company.url_domain, domain_name, obj.id)
        try:
            short_url_obj = ShortURL.objects.filter(long_url=complete_url, internal=False).last()
            return short_url_obj.short_url
        except Exception as e:
            print(e)
            return "No Url. Create first"
    else:
        return None


def fetch_dynamic_email_template(
    content, to_email, applied_position_id=None, subject=None, interviewers=None, company_name=None, employee_name=None, position_name=None
):
    try:
        sender_obj = Profile.objects.filter(user__email=to_email[0]).last()
    except Profile.DoesNotExist:
        return None

    from_email = settings.EMAIL_HOST_USER
    value_map = choices.MACROS
    for key in value_map:
        value_map[key] = " "
    value_map["{{Company_Name}}"] = str(company_name)
    if employee_name:
        value_map["{{Employee_Name}}"] = employee_name
    if position_name:
        value_map["{{Position_Name}}"] = position_name
    if applied_position_id:
        applied_position_obj = AppliedPosition.objects.get(id=applied_position_id)
        candidate_dashboard_link = "https://{}.{}/viewcandidate/?applied_profile={}&user_applied_id={}&positionNo={}".format(
            applied_position_obj.company.url_domain,
            settings.DOMAIN_NAME,
            applied_position_obj.id,
            applied_position_obj.applied_profile.id,
            applied_position_obj.form_data.id,
        )
        value_map["{{Candidate_Dashboard_Link}}"] = "<a href='{}' style='color:blue;text-decoration:underline'>LINK</a>".format(
            candidate_dashboard_link
        )
        value_map["{{Position_Name}}"] = applied_position_obj.form_data.form_data["job_title"]
        value_map["{{Position_No}}"] = str(applied_position_obj.form_data.id)
        value_map["{{Candidate_Name}}"] = str(applied_position_obj.applied_profile.user.first_name)
        value_map["{{Company_Name}}"] = str(applied_position_obj.company.company_name)
        company_link = "https://{}.{}".format(applied_position_obj.company.url_domain, settings.DOMAIN_NAME)
        value_map["{{Company_Website_Link}}"] = "<a href='{}' style='color:blue;text-decoration:underline'>{}</a>".format(company_link, company_link)
        value_map["{{CompanyLogin_Link}}"] = "<a href='{}' style='color:blue;text-decoration:underline'>{}</a>".format(company_link, company_link)
        external_link = get_candidate_visibility_link(applied_position_obj.form_data)
        value_map["{{External_Job_Ad_Link}}"] = "<a href='{}' style='color:blue;text-decoration:underline'>{}</a>".format(
            external_link, external_link
        )
        try:
            value_map["{{Interview_Type}}"] = PositionStage.objects.get(id=applied_position_obj.data["position_stage_id"]).stage.stage_name
        except:
            value_map["{{Interview_Type}}"] = ""
        value_map["{{Hiring_Manager}}"] = (
            applied_position_obj.form_data.created_by_profile.user.first_name + " " + applied_position_obj.form_data.created_by_profile.user.last_name
        )

        # Try to update start_date if offer letter is created
        try:
            offer_obj = OfferLetter.objects.get(offered_to__id=applied_position_obj.id)
            value_map["{{Start_Date}}"] = str(offer_obj.start_date)
            value_map["{{BasicSalary}}"] = str(offer_obj.basic_salary)
            value_map["{{GuaranteeBonus}}"] = str(offer_obj.guarantee_bonus)
            value_map["{{SignOnBonus}}"] = str(offer_obj.sign_on_bonus)
            value_map["{{VisaRequired}}"] = str(offer_obj.visa_required)
            value_map["{{RelocationBonus}}"] = str(offer_obj.relocation_bonus)
        except:
            pass

        # Add interview data
        if "interview_schedule_data" in applied_position_obj.data:
            try:
                schedule_data = applied_position_obj.data["interview_schedule_data"]
                value_map["{{Date}}"] = schedule_data["date"]
                value_map["{{Time}}"] = "{} to {}".format(schedule_data["start_time"], schedule_data["end_time"])
                try:
                    value_map["{{Timezone}}"] = applied_position_obj.data["interview_schedule_data"]["timezone"]
                except:
                    value_map["{{Timezone}}"] = ""
                if "Interview_venue" in schedule_data:
                    value_map["{{Interview_Venue}}"] = schedule_data["Interview_venue"]
                if interviewers is None:
                    interviewers = ""
                    for interviewer in schedule_data["Interviewer"]:
                        interviewers += "{}, ".format(interviewer["label"])
                    value_map["{{Interviewer_Name}}"] = interviewers
            except Exception as e:
                print(e)
    dyanamic_template = replace_variables(content, value_map)

    if subject:
        pass
    else:
        subject = "title"
    msg = EmailMultiAlternatives(subject, dyanamic_template, subject, to_email)
    msg.content_subtype = "html"
    msg.send()
    return True


def replace_variables(content, value_map):
    while True:
        try:
            idx1 = content.index("{{")
            idx2 = content.index("}}")
        except:
            break
        sub_string = content[idx1 + len("{{") : idx2]
        content = content.replace("{{" + sub_string + "}}", str(value_map["{{" + sub_string + "}}"]))
    return content


def send(sender_email, password, smtp_host, port, subject, html_content, content_type, recipient_list, reply_to, sender_name, filename_event=None):
    recipients = ", ".join(recipient_list)
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["To"] = recipients
    message["From"] = formataddr(("{} - Infertalent Notification".format(sender_name), sender_email))
    message["Reply-To"] = reply_to
    message.add_header("X-Priority", "1 (High)")
    if content_type == "html":
        message.attach(MIMEText(html_content, "html"))
    else:
        message.attach(MIMEText(html_content))
    if filename_event:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(open("/path/todirectory/" + "invite.ics", "rb").read())
        part.add_header("Content-Disposition", 'attachment; filename="invite.ics"')
        message.attach(part)
    server = smtplib.SMTP_SSL(smtp_host, port)
    server.login(sender_email, password)
    server.sendmail(sender_email, recipient_list, message.as_string())
    server.quit()
