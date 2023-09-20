import base64
import json
import os
import time
from datetime import date

import jwt
import requests
from cryptography.hazmat.primitives import serialization as crypto_serialization
from django.conf import settings
from django.core.files import File
from django.http import HttpResponse, HttpResponseRedirect
from docusign_esign import (
    ApiClient,
    CarbonCopy,
    DateSigned,
    Document,
    EnvelopeDefinition,
    EnvelopesApi,
    Recipients,
    RecipientViewRequest,
    Signer,
    SignHere,
    Tabs,
    Text,
)
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from jose import jws
from rest_framework import status as drf_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from app.util import generate_offer_pdf
from company.models import ServiceProviderCreds
from form.models import OfferLetter, OfferLetterTemplate


def docusign_token(docusign_user_id, docusign_account_id, docusign_auth_id, pem):
    iat = time.time()
    exp = iat + (3600 * 24)
    payload = {
        "sub": docusign_user_id,
        "iss": docusign_auth_id,
        "iat": iat,  # session start_time
        "exp": exp,  # session end_time
        "aud": "account-d.docusign.com",
        "scope": "signature",
    }
    private_key = crypto_serialization.load_pem_private_key(pem.encode(), password=None)
    key = private_key.private_bytes(crypto_serialization.Encoding.PEM, crypto_serialization.PrivateFormat.PKCS8, crypto_serialization.NoEncryption())
    jwt_token = jws.sign(payload, key, algorithm="RS256")
    return jwt_token


def create_jwt_grant_token(docusign_user_id, docusign_account_id, docusign_auth_id, pem):
    token = docusign_token(docusign_user_id, docusign_account_id, docusign_auth_id, pem)
    return token


def make_envelope(args, offer_obj):
    """
    Creates envelope
    args -- parameters for the envelope:
    signer_email, signer_name, signer_client_id
    returns an envelope definition
    """
    file_path = "../Offer_{}.pdf".format(offer_obj.id)
    if os.path.exists(file_path):
        with open(file_path, "rb") as fh:
            content_bytes = fh.read()
    base64_file_content = base64.b64encode(content_bytes).decode("ascii")
    # Create the document model
    document = Document(  # create the DocuSign document object
        document_base64=base64_file_content,
        name="Example document",  # can be different from actual file name
        file_extension="pdf",  # many different document types are accepted
        document_id=1,  # a label used to reference the doc
    )

    # Create the signer recipient model
    signer = Signer(  # The signer
        email=args["signer_email"],
        name=args["signer_name"],
        recipient_id="1",
        routing_order="1",
        # Setting the client_user_id marks the signer as embedded
        client_user_id=args["signer_client_id"],
    )

    # Create a sign_here tab (field on the document)
    sign_here = SignHere(anchor_string="/sn1/", anchor_units="pixels", anchor_y_offset="10", anchor_x_offset="20")  # DocuSign SignHere field/tab

    # Add the tabs model (including the sign_here tab) to the signer
    # The Tabs object wants arrays of the different field/tab types
    signer.tabs = Tabs(sign_here_tabs=[sign_here])

    # Next, create the top level envelope definition and populate it.
    envelope_definition = EnvelopeDefinition(
        email_subject="Please sign this document sent from the Python SDK",
        documents=[document],
        # The Recipients object wants arrays for each recipient type
        recipients=Recipients(signers=[signer]),
        status="sent",  # requests that the envelope be created and sent.
    )

    return envelope_definition


def get_pdf_file(offer_obj):
    offer_letter = offer_obj
    # get location, offer template and all other details
    try:
        offer_template_obj = OfferLetterTemplate.objects.get(
            country__name=offer_letter.offered_to.form_data.form_data["country"]["name"], company=offer_letter.offered_to.form_data.company
        )
    except:
        try:
            offer_template_obj = OfferLetterTemplate.objects.get(
                offer_type__in=["Default", "Default Offer"], company=offer_letter.offered_to.form_data.company
            )
        except:
            return Response(
                {
                    "message": "Admin needs to create an offer letter template from the offer template tab in the admin panel",
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
    file = offer_template_obj.attached_letter
    pdf_context = {}
    pdf_context["CandidateFullName"] = offer_letter.offered_to.applied_profile.user.get_full_name()
    pdf_context["CandidateFirstName"] = offer_letter.offered_to.applied_profile.user.first_name
    pdf_context["JobTitle"] = "{} (Business Title)".format(offer_letter.offered_to.form_data.form_data["job_title"])
    pdf_context["Location"] = offer_letter.offered_to.form_data.form_data["country"]["name"]
    pdf_context["HiringManagersTitle"] = offer_letter.reporting_manager
    pdf_context["StartDate"] = str(offer_letter.start_date)
    pdf_context["TotalTargetCompensation"] = str(offer_letter.target_compensation)
    pdf_context["Currency"] = str(offer_letter.currency)
    pdf_context["BonusAmount"] = str(offer_letter.bonus)
    pdf_context["ReportingManager"] = str(offer_letter.reporting_manager)
    pdf_context["OrganizationName"] = offer_letter.offered_to.form_data.company.company_name
    pdf_context["BasicSalary"] = offer_letter.basic_salary
    pdf_context["GuaranteeBonus"] = offer_letter.guarantee_bonus
    pdf_context["SignOnBonus"] = offer_letter.sign_on_bonus
    pdf_context["VisaRequired"] = offer_letter.visa_required
    pdf_context["RelocationBonus"] = offer_letter.relocation_bonus
    return file, pdf_context


class GetDocuSignURL(APIView):

    """
        This API sends the sign url of the document on docusign. It returns a URL onn visiting which user can sign the offer letter.
    Args:
        None
    Body:
        domain - domain of the company
        email - email of the candidate
        name - name of the candidate
        applied_id - id of the applied position
    Returns:
        -success message and docusign URL(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @swagger_auto_schema(
        operation_description="Get Docusign URL API",
        operation_summary="Get Docusign URL API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "domain": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "name": openapi.Schema(type=openapi.TYPE_STRING),
                "applied_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
    )
    def post(self, request):
        try:
            try:
                creds_obj = ServiceProviderCreds.objects.get(company__url_domain=request.data.get("domain"))
                docusign_user_id = creds_obj.docusign["user_id"]
                docusign_account_id = creds_obj.docusign["account_id"]
                docusign_auth_id = creds_obj.docusign["auth_id"]
                pem = creds_obj.docusign["pem"]
                print(creds_obj.docusign)
            except:
                return Response({"msg": "Docusign not enabled", "error": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)
            user_id = creds_obj
            data = {
                "signer_email": request.data.get("email"),
                "signer_name": request.data.get("name"),
                "signer_client_id": docusign_user_id,
            }
            applied_id = request.data.get("applied_id")
            queryset = OfferLetter.objects.filter(offered_to__id=applied_id)
            if queryset:
                offer_obj = queryset.last()
                file, pdf_context = get_pdf_file(offer_obj)
                generate_offer_pdf(file, offer_obj.id, pdf_context)
            else:
                return Response({"msg": "offer not found!"}, status=drf_status.HTTP_400_BAD_REQUEST)
            envelope_definition = make_envelope(data, offer_obj)
            # get access token
            token = create_jwt_grant_token(docusign_user_id, docusign_account_id, docusign_auth_id, pem)
            print(token)
            url = "https://account-d.docusign.com/oauth/token"
            payload = "grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=" + token
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }
            resp = requests.request("POST", url, headers=headers, data=payload)
            resp_data = resp.json()
            access_token = resp_data.get("access_token")
            if access_token:
                api_client = ApiClient()
                api_client.host = "https://demo.docusign.net/restapi"
                api_client.set_default_header(header_name="Authorization", header_value=f"Bearer {access_token}")
                envelope_api = EnvelopesApi(api_client)
                results = envelope_api.create_envelope(account_id=docusign_account_id, envelope_definition=envelope_definition)
                envelope_id = results.envelope_id
                print(envelope_id)
                offer_obj.docusign_envelope_id = envelope_id
                offer_obj.save()
                # Create the Recipient View request object
                recipient_view_request = RecipientViewRequest(
                    authentication_method="email",
                    client_user_id=docusign_user_id,
                    recipient_id="1",
                    return_url="https://{}/docusign/callback/success?domain={}&offer_id={}".format(
                        settings.BE_DOMAIN_NAME, request.data.get("domain"), offer_obj.id
                    ),
                    user_name=request.data.get("name"),
                    email=request.data.get("email"),
                )
                recipient_res = envelope_api.create_recipient_view(docusign_account_id, envelope_id, recipient_view_request=recipient_view_request)
                return Response({"url": recipient_res.url}, status=drf_status.HTTP_200_OK)
            else:
                return Response(
                    {
                        "msg": "error generating access token",
                        "data": resp_data,
                    },
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response({"msg": "error occured!", "error": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)


def get_envelope_status(envelope_id, offer_obj, docusign_user_id, docusign_account_id, docusign_auth_id, pem):
    try:
        token = create_jwt_grant_token(docusign_user_id, docusign_account_id, docusign_auth_id, pem)
        url = "https://account-d.docusign.com/oauth/token"
        payload = "grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=" + token
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = requests.request("POST", url, headers=headers, data=payload)
        resp_data = resp.json()
        access_token = resp_data.get("access_token")
        api_client = ApiClient()
        api_client.host = "https://demo.docusign.net/restapi"
        api_client.set_default_header(header_name="Authorization", header_value=f"Bearer {access_token}")
        envelope_api = EnvelopesApi(api_client)
        document_id = "1"
        # Call the envelope get method
        temp_file = envelope_api.get_document(account_id=docusign_account_id, document_id=document_id, envelope_id=envelope_id)
        with open(temp_file, "rb") as file:
            offer_obj.signed_file = File(file=file, name="my_offer.pdf")
            offer_obj.save()
        os.remove(temp_file)
        return True
    except Exception as e:
        return False


class DosuSignSuccess(APIView):

    """
    API handles the docusign success to store the signed pdf to our tables and marks signing status done.
    Args:
        domain
        offer_id
    Body:
        None
    Returns:
        -HTTP Response with message(HTTP_200_OK)
        -Error and Message(HTTP_400_BAD_REQUEST)
    Authentication:
        JWT
    Raises:
        None
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    domain = openapi.Parameter(
        "domain",
        in_=openapi.IN_QUERY,
        description="domain",
        type=openapi.TYPE_STRING,
    )
    offer_id = openapi.Parameter(
        "offer_id",
        in_=openapi.IN_QUERY,
        description="offer_id of the offer assigned to candidate",
        type=openapi.TYPE_STRING,
    )

    @swagger_auto_schema(
        operation_description="Handles Docusign Success",
        operation_summary="Handles Docusign Success",
        manual_parameters=[domain, offer_id],
    )
    def get(self, request):
        try:
            data = request.GET
            domain = data.get("domain")
            try:
                creds_obj = ServiceProviderCreds.objects.get(company__url_domain=request.data.get("domain"))
                docusign_user_id = creds_obj.docusign["user_id"]
                docusign_account_id = creds_obj.docusign["account_id"]
                docusign_auth_id = creds_obj.docusign["auth_id"]
                pem = creds_obj.docusign["pem"]
            except:
                return Response({"msg": "Docusign not enabled", "error": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)
            domain = data.get("domain")
            offer_id = data.get("offer_id")
            queryset = OfferLetter.objects.filter(id=offer_id)
            if queryset:
                offer_obj = queryset.last()
                result = get_envelope_status(offer_obj.docusign_envelope_id, offer_obj, docusign_user_id, docusign_account_id, docusign_auth_id, pem)
                if result:
                    return HttpResponseRedirect("https://{}.{}".format(domain, settings.DOMAIN_NAME))
                else:
                    return HttpResponse("Documen signed successfully!")
            else:
                return HttpResponse("Offer letter not found")
        except Exception as e:
            return HttpResponse("Something went wrong! Error: ", str(e))
