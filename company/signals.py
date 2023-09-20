# from django.conf import settings
# from django.core.mail import EmailMultiAlternatives
# from django.db.models.signals import post_save, pre_delete
# from django.dispatch import receiver
# from django.template.loader import render_to_string

# from form import models as form_model
# from role import models as role_model
# from scorecard import models as scorecard_model
# from stage import models as stage_model

# from .models import Company


# @receiver(post_save, sender=Company)
# def create_profile(sender, instance, created, **kwargs):
#     if created:
#         # Send confirmation mail to the the user
#         if instance.company_owner:
#             first_name = instance.company_owner.first_name
#             to_email = instance.company_owner.email
#         else:
#             first_name = " "
#             to_email = "sample@mail.com"
#         context = {"first_name": first_name, "company_name": instance.company_name, "support_email": "rs1837264@gmail.com"}  # hardcoded for now
#         from_email = settings.EMAIL_HOST_USER
#         to_email = to_email
#         body_msg = render_to_string("request-demo-confirmation.html", context)
#         msg = EmailMultiAlternatives("Demo Confirmation<Don't Reply>", body_msg, from_email, [to_email])
#         msg.content_subtype = "html"
#         msg.send()

#         # Send mail to support team
#         context = {"first_name": "Support at Infertalent", "company_name": instance.company_name, "user_email": to_email}
#         from_email = settings.EMAIL_HOST_USER
#         to_email = "rs1837264@gmail.com"
#         body_msg = render_to_string("request-demo-support.html", context)
#         msg = EmailMultiAlternatives("Demo Confirmation<Don't Reply>", body_msg, from_email, [to_email])
#         msg.content_subtype = "html"
#         msg.send()

#         # Create Forms
#         try:
#             form_objs = form_model.Form.objects.filter(company__company_name="Infertalent")
#             for form in form_objs:
#                 form.pk = None
#                 form.company = instance
#                 form.save()
#         except Exception as e:
#             print(e)
#             print("Error creating forms")

#         # Create fields
#         try:
#             field_objs = form_model.Field.objects.filter(
#                 company__company_name="Infertalent",
#                 # field_name__in=[
#                 #     "Position Name",
#                 #     "Job Category",
#                 #     "Hiring Manager",
#                 #     "Job Description",
#                 #     "Level",
#                 #     "Bonus",
#                 #     "Total Target Compensation",
#                 #     "Guarantee Bonus",
#                 #     "Sign on bonus",
#                 #     "Start Date",
#                 #     "Relocation Bonus",
#                 #     "Salary",
#                 #     "Level",
#                 #     "Basic Salary",
#                 #     "Employment Type",
#                 #     "Visa Required",
#                 #     "Currency",
#                 #     "Reporting Manager",
#                 #     "Location",
#                 #     "Recruiter",
#                 #     "Experience Level",
#                 #     "Facebook URL",
#                 #     "Departments",
#                 # ],
#             )
#             for field in field_objs:
#                 try:
#                     if field.field_name in ["Facebook URL", "Favourite Skill", "Experience Level"] and field.form.form_name == "Application Form":
#                         continue
#                     field.pk = None
#                     field.company = instance
#                     field.save()
#                     form_obj = form_model.Form.objects.filter(form_name=field.form.form_name, company=instance).last()
#                     if form_obj:
#                         field.form = form_obj
#                         field.save()
#                     else:
#                         field.delete()
#                     # Create Field Choice if fields are level, employment type, salary and position name
#                     # ["", "Salary", "Level"]
#                     if field.field_name == "Position Name":
#                         form_model.FieldChoice.objects.create(choice_key="Short Text", choice_value=30, field=field)
#                     if field.field_name == "Salary":
#                         form_model.FieldChoice.objects.create(choice_key="Number", choice_value=30, field=field)
#                     if field.field_name == "Employment Type":
#                         form_model.FieldChoice.objects.create(choice_key="Dropdown", choice_value="Full-Time", field=field)
#                         form_model.FieldChoice.objects.create(choice_key="Dropdown", choice_value="Part-Time", field=field)
#                     if field.field_name == "Level":
#                         form_model.FieldChoice.objects.create(choice_key="Dropdown", choice_value="Senior Manager", field=field)
#                         form_model.FieldChoice.objects.create(choice_key="Dropdown", choice_value="Manager", field=field)
#                 except Exception as e:
#                     print(e)
#         except Exception as e:
#             print(e)
#             print("Error creating Fields")

#         # Create Roles
#         try:
#             field_objs = role_model.Role.objects.filter(company__company_name="Infertalent", name="admin")
#             for field in field_objs:
#                 field.pk = None
#                 field.company = instance
#                 field.save()
#         except Exception as e:
#             print(e)
#             print("Error creating Fields")

#         # Create Pipeline
#         try:
#             pipeline_obj = stage_model.Pipeline.objects.filter(company__company_name="Infertalent")
#             for pipeline in pipeline_obj:
#                 pipeline.pk = None
#                 pipeline.company = instance
#                 pipeline.save()
#         except Exception as e:
#             print("Error creating pipeline: ", str(e))

#         # Create stage
#         try:
#             stage_obj = stage_model.Stage.objects.filter(
#                 company__company_name="Infertalent",
#                 stage_name__in=[
#                     "Resume Review",
#                     "Hiring Manager Review",
#                     "Offer",
#                     "Background Check",
#                     "Document Check",
#                     "Hired",
#                     "2nd interview",
#                     "Panel Discussion",
#                     "HR Discussion",
#                     "Final Interview",
#                 ],
#             )
#             for stage in stage_obj:
#                 stage.pk = None
#                 pipeline_obj = stage_model.Pipeline.objects.filter(company=instance, pipeline_name=stage.pipeline.pipeline_name).last()
#                 print(pipeline_obj)
#                 stage.pipeline = pipeline_obj
#                 stage.company = instance
#                 stage.save()
#         except Exception as e:
#             print("Error creating Fields: ", str(e))

#         # Create Attributes
#         for i in scorecard_model.Competency.objects.filter(
#             company__company_name="Infertalent", competency__in=["Agility", "Results Driven", "Innovating", "Team Building", "Management"]
#         ):
#             att = i.attribute.all()
#             i.pk = None
#             i.company = instance
#             i.save()
#             for a in att:
#                 a.pk = None
#                 a.company = instance
#                 a.save()
#                 i.attribute.add(a)
#             i.save()

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.template.loader import render_to_string

from form import models as form_model
from organization.models import Organization
from role import models as role_model
from scorecard import models as scorecard_model
from stage import models as stage_model

from .models import Company


@receiver(post_save, sender=Company)
def create_profile(sender, instance, created, **kwargs):
    if created:
        # Create Forms
        try:
            form_objs = form_model.Form.objects.filter(company__company_name="Infertalent")
            for form in form_objs:
                form.pk = None
                form.company = instance
                form.save()
        except Exception as e:
            print(e)
            print("Error creating forms")

        # Create fields
        try:
            field_objs = form_model.Field.objects.filter(company__company_name="Infertalent").order_by("id")
            for field in field_objs:
                old_field_id = field.id
                try:
                    field.pk = None
                    field.company = instance
                    field.save()
                    form_obj = form_model.Form.objects.filter(form_name=field.form.form_name, company=instance).last()
                    if form_obj:
                        field.form = form_obj
                        field.save()
                    else:
                        field.delete()
                    # Create Field Choice if fields are level, employment type, salary and position name
                    # ["", "Salary", "Level"]
                    # if field.field_name == "Position Name":
                    #     form_model.FieldChoice.objects.create(choice_key="Short Text", choice_value=30, field=field)
                    # elif field.field_name == "Salary":
                    #     form_model.FieldChoice.objects.create(choice_key="Number", choice_value=30, field=field)
                    # elif field.field_name == "Employment Type":
                    #     form_model.FieldChoice.objects.create(choice_key="Dropdown", choice_value="Full-Time", field=field)
                    #     form_model.FieldChoice.objects.create(choice_key="Dropdown", choice_value="Part-Time", field=field)
                    # elif field.field_name == "Level":
                    #     form_model.FieldChoice.objects.create(choice_key="Dropdown", choice_value="Senior Manager", field=field)
                    #     form_model.FieldChoice.objects.create(choice_key="Dropdown", choice_value="Manager", field=field)
                    # else:
                    try:
                        if field.field_name not in ["Departments", "Hiring Manager", "Recruiter", "Location"]:
                            field_choice = form_model.FieldChoice.objects.filter(field__id=old_field_id)
                            for fc in field_choice:
                                fc.pk = None
                                fc.field = field
                                fc.save()
                    except:
                        pass
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)
            print("Error creating Fields")

        # Create Roles
        try:
            role_objs = role_model.Role.objects.filter(
                company__company_name="Infertalent",
                name__in=[
                    "interviewer",
                    "admin",
                    "position approver",
                    "offer approver",
                    "hiring manager",
                    "recruiter",
                    "position admin",
                    "employee",
                ],
            )
            for role in role_objs:
                role_permissions = role_model.RolePermission.objects.filter(role=role)
                role.pk = None
                role.company = instance
                role.save()
                for role_permission in role_permissions:
                    role_permission.pk = None
                    role_permission.role = role
                    role_permission.save()
        except Exception as e:
            print(e)
            print("Error creating role")

        # Create Pipeline
        try:
            pipeline_obj = stage_model.Pipeline.objects.filter(company__company_name="Infertalent")
            for pipeline in pipeline_obj:
                pipeline.pk = None
                pipeline.company = instance
                pipeline.save()
        except Exception as e:
            print("Error creating pipeline: ", str(e))

        # Create stage
        try:
            stage_list = [
                "Resume Review",
                "Hiring Manager Review",
                "Offer",
                "Hired",
                "Background Check",
                "Document Check",
            ]
            order = 0
            for stage in stage_list:
                stage_model.Stage.objects.create(
                    stage_name=stage,
                    company=instance,
                    pipeline=stage_model.Pipeline.objects.filter(company=instance, pipeline_name="Hiring Stage").last(),
                    sort_order=order,
                    is_mandatory=True,
                    is_active=True,
                )
                order += 1
            stage_list = [
                "2nd interview",
                "Panel Discussion",
                "HR Discussion",
                "Final Interview",
            ]
            order = 0

            for stage in stage_list:
                # if stage == "HR Discussion":
                #     is_interview = False
                # else:
                #     is_interview = True
                is_interview = True
                stage_model.Stage.objects.create(
                    stage_name=stage,
                    company=instance,
                    pipeline=stage_model.Pipeline.objects.filter(company=instance, pipeline_name="Other Stage").last(),
                    sort_order=order,
                    is_mandatory=True,
                    is_active=True,
                    is_interview=is_interview,
                )
                order += 1
            # stage_obj = stage_model.Stage.objects.filter(
            #     company__company_name="Infertalent",
            #     stage_name__in=[
            #         "Resume Review",
            #         "Hiring Manager Review",
            #         "Offer",
            #         "Background Check",
            #         "Document Check",
            #         "Hired",
            #         "2nd interview",
            #         "Panel Discussion",
            #         "HR Discussion",
            #         "Final Interview",
            #     ],
            # )
            # for stage in stage_obj:
            #     stage.pk = None
            #     pipeline_obj = stage_model.Pipeline.objects.filter(company=instance, pipeline_name=stage.pipeline.pipeline_name).last()
            #     stage.pipeline = pipeline_obj
            #     stage.company = instance
            #     stage.save()
        except Exception as e:
            print("Error creating Fields: ", str(e))

        # Create Attributes
        try:
            for a in scorecard_model.Attribute.objects.filter(company__company_name="Infertalent").exclude(
                attribute_name__in=["Sole Leadership", "Sole Performer", "Benchmarks"]
            ):
                a.pk = None
                a.company = instance
                a.save()
        except:
            print("Error creating attributes")
        # Add reasons
        try:
            for type in form_model.ReasonType.objects.filter(company__company_name="Infertalent"):
                reasons = form_model.Reason.objects.filter(type=type)
                type.pk = None
                type.company = instance
                type.save()
                for reason in reasons:
                    reason.pk = None
                    reason.type = type
                    reason.company = instance
                    reason.save()
        except:
            print("error creating reasons")
