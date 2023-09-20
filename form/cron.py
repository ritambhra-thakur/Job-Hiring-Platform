import datetime

from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string

from app.encryption import decrypt, encrypt
from form.models import OfferLetter
from main import settings


def my_cron_job():
    from_email = settings.EMAIL_HOST_USER

    today_offer_letter = OfferLetter.objects.filter(start_date=datetime.date.today())
    if today_offer_letter.count() == 0:
        body_msg = render_to_string("join_candidate_email.html")

        msg = EmailMultiAlternatives("No Candidate!!!!", body_msg, "No Candidate!!!!", ["gaurav321@yopmail.com"])
        msg.content_subtype = "html"
        msg.send()
    else:
        for offer in today_offer_letter:
            try:
                to_email = offer.offered_by_profile.user.email
            except:
                to_email = "testing7654@yopmail.com"
            encoded_offer_id = encrypt(offer.id)

            decline_link = "https://{}.{}/hiring-manager/dashboard#newHiRes".format(offer.offered_to.company.url_domain, settings.DOMAIN_NAME)
            accept_link = "https://api.{}/form/accept-candidate-joining/?encoded_id={}".format(settings.DOMAIN_NAME, encoded_offer_id)
            # accept_link = "http://127.0.0.1:8000/form/accept-candidate-joining/?encoded_id={}".format(encoded_offer_id)

            # context = {"link": body}
            context = {"decline_link": decline_link, "accept_link": accept_link, "hiring_manage_name": offer.offered_by_profile.user.first_name}
            body_msg = render_to_string("join_candidate_email.html", context=context)

            msg = EmailMultiAlternatives("tittle", body_msg, "tittle", [to_email])
            msg.content_subtype = "html"
            msg.send()
            break
    return True
