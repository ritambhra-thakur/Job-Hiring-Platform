from django.urls import path

from form import views as form_view
from role import views

from .views import *

app_name = "form"

urlpatterns = [
    path("api/v1/list/", form_view.GetAllForm.as_view()),
    path("api/v1/get/<int:pk>/", form_view.GetForm.as_view()),
    path("api/v1/create/", form_view.CreateForm.as_view()),
    path("api/v1/update/<int:pk>/", form_view.UpdateForm.as_view()),
    path("api/v1/delete/<int:pk>/", form_view.DeleteForm.as_view()),
    path("field/api/v1/list/", form_view.GetAllField.as_view()),
    path("field/api/v1/get/<int:pk>/", form_view.GetField.as_view()),
    path("field/api/v1/create/", form_view.CreateField.as_view()),
    path("field/api/v1/update/<int:pk>/", form_view.UpdateField.as_view()),
    path("field/api/v1/delete/<int:pk>/", form_view.DeleteField.as_view()),
    # Field_Type
    path("field_type/api/v1/list/", form_view.GetAllFieldType.as_view()),
    path("field_type/api/v1/get/<int:pk>/", form_view.GetFieldType.as_view()),
    path("field_type/api/v1/create/", form_view.CreateFieldType.as_view()),
    path(
        "field_type/api/v1/update/<int:pk>/",
        form_view.UpdateFieldType.as_view(),
    ),
    path(
        "field_type/api/v1/delete/<int:pk>/",
        form_view.DeleteFieldType.as_view(),
    ),
    # Field_choice
    path("field_choices/api/v1/list/", form_view.GetAllFieldChoice.as_view()),
    path(
        "field_choices/api/v1/get/<int:pk>/",
        form_view.GetFieldChoice.as_view(),
    ),
    path("field_choices/api/v1/create/", form_view.CreateFieldChoice.as_view()),
    path(
        "field_choices/api/v1/update/<int:pk>/",
        form_view.UpdateFieldChoice.as_view(),
    ),
    path(
        "field_choices/api/v1/delete/<int:pk>/",
        form_view.DeleteFieldChoice.as_view(),
    ),
    # Form_data
    path("form_data/api/v1/list/", form_view.GetAllFormData.as_view()),
    path("form_data/api/v1/op-list-left/", form_view.GetAllOpFormDataLeft.as_view()),
    path("form_data/api/v1/op-list/", form_view.GetAllOpFormData.as_view()),
    path("form_data/api/v1/op-pending-list/", form_view.GetAllOpPendingFormData.as_view()),
    path("form_data/api/v1/job-boards/", form_view.GetAllJobBoard.as_view()),
    path("form_data/api/v1/op-job-posting-list/", form_view.GetAllOpJobPosting.as_view()),
    path("form_data/api/v1/list/clone-position", form_view.GetAllFormDataClone.as_view()),
    path("form_data/api/v1/advertisement/list/", form_view.GetAdvertisementFormData.as_view()),
    path("form_data/api/v1/guest/list/", form_view.GetAllFormDataGuest.as_view()),
    path(
        "form_data/api/v1/get/<int:pk>/",
        form_view.GetFormData.as_view(),
    ),
    path("form_data/api/v1/create/", form_view.CreateFormData.as_view()),
    path(
        "form_data/api/v1/update/<int:pk>/",
        form_view.UpdateFormData.as_view(),
    ),
    path(
        "form_data/api/v1/add-jd/<int:pk>/",
        form_view.AddJDFormData.as_view(),
    ),
    path(
        "form_data/api/v1/delete/<int:pk>/",
        form_view.DeleteFormData.as_view(),
    ),
    # position approval
    path(
        "position_approval/api/v1/list/",
        form_view.GetAllPositionApproval.as_view(),
    ),
    path(
        "position_approval/api/v1/op-list/",
        form_view.GetAllOpPositionApproval.as_view(),
    ),
    path(
        "position_approval/api/v1/get/<int:pk>/",
        form_view.GetPositionApproval.as_view(),
    ),
    path(
        "position_approval/api/v1/create/",
        form_view.CreatePositionApproval.as_view(),
    ),
    path(
        "position_approval/api/v1/update/<int:pk>/",
        form_view.UpdatePositionApproval.as_view(),
    ),
    path(
        "position_approval/api/v1/delete/<int:pk>/",
        form_view.DeletePositionApproval.as_view(),
    ),
    # offer approval
    path(
        "offer_approval/api/v1/list/",
        form_view.GetAllOfferApproval.as_view(),
    ),
    path(
        "offer_approval/api/v1/op-list/",
        form_view.GetAllOpOfferApproval.as_view(),
    ),
    path(
        "offer_approval/api/v1/get/<int:pk>/",
        form_view.GetOfferApproval.as_view(),
    ),
    path(
        "offer_approval/api/v1/create/",
        form_view.CreateOfferApproval.as_view(),
    ),
    path(
        "offer_approval/api/v1/update/<int:pk>/",
        form_view.UpdateOfferApproval.as_view(),
    ),
    path(
        "offer_approval/api/v1/delete/<int:pk>/",
        form_view.DeleteOfferApproval.as_view(),
    ),
    # Offer Letter
    path(
        "offer_letter/api/v1/create/",
        form_view.OfferLetterView.as_view(),
    ),
    path(
        "offer_letter/api/v1/get/<str:profile_id>",
        form_view.GetOfferLetters.as_view(),
    ),
    path(
        "offer_letter/api/v1/offered_to/<str:profile_id>",
        form_view.GetOfferedToList.as_view(),
    ),
    path(
        "offer_letter/api/v1/single-offer/<int:offer_id>",
        form_view.GetSingleOffer.as_view(),
    ),
    path(
        "offer_letter/api/v1/download/<int:id>",
        form_view.GetOfferLetterPdf.as_view(),
    ),
    # Offer Letter Template
    path(
        "offer_letter/api/v1/template/",
        form_view.OfferLetterTemplateView.as_view(),
    ),
    path(
        "offer_letter/api/v1/template/list/",
        form_view.GetAllOfferLetterTempalte.as_view(),
    ),
    path(
        "offer_letter/api/v1/upload-singed-letter/<int:id>/",
        form_view.UploadedSignedOfferLetter.as_view(),
    ),
    path(
        "hires/api/v1/new-hires/",
        form_view.GetNewHires.as_view(),
    ),
    path(
        "hires/api/v1/op-new-hires/",
        form_view.GetOpNewHires.as_view(),
    ),
    path(
        "hires/api/v1/admin-new-hires/",
        form_view.AdminGetNewHires.as_view(),
    ),
    path(
        "hires/api/v1/send-hire-mail/<int:pk>",
        form_view.SendHireEmail.as_view(),
    ),
    # JobCategory
    path(
        "job_category/api/v1/list/",
        form_view.GetAllJobCategory.as_view(),
    ),
    path(
        "job_category/api/v1/op-list/",
        form_view.GetAllOpJobCategory.as_view(),
    ),
    path(
        "job_category/api/v1/guest/list/",
        form_view.GetAllJobCategoryGuest.as_view(),
    ),
    path(
        "job_category/api/v1/get/<int:pk>/",
        form_view.GetJobCategory.as_view(),
    ),
    path(
        "job_category/api/v1/create/",
        form_view.CreateJobCategory.as_view(),
    ),
    path(
        "job_category/api/v1/update/<int:pk>/",
        form_view.UpdateJobCategory.as_view(),
    ),
    path(
        "job_category/api/v1/delete/<int:pk>/",
        form_view.DeleteJobCategory.as_view(),
    ),
    path(
        "job_category/api/v1/export/csv/<int:company_id>/",
        form_view.JobCategoryCSVExport.as_view(),
    ),
    # JobLocation
    path(
        "job_location/api/v1/list/",
        form_view.GetAllJobLocation.as_view(),
    ),
    path(
        "job_location/api/v1/op-list/",
        form_view.GetAllOpJobLocation.as_view(),
    ),
    path(
        "job_location/api/v1/guest/list/",
        form_view.GetAllJobLocationGuest.as_view(),
    ),
    path(
        "job_location/api/v1/get/<int:pk>/",
        form_view.GetJobLocation.as_view(),
    ),
    path(
        "job_location/api/v1/create/",
        form_view.CreateJobLocation.as_view(),
    ),
    path(
        "job_location/api/v1/update/<int:pk>/",
        form_view.UpdateJobLocation.as_view(),
    ),
    path(
        "job_location/api/v1/delete/<int:pk>/",
        form_view.DeleteJobLocation.as_view(),
    ),
    path(
        "job_location/api/v1/export/csv/<int:company_id>/",
        form_view.JobLocationCSVExport.as_view(),
    ),
    # RecentViewJob
    path(
        "recent_view_job/api/v1/list/",
        form_view.GetAllRecentViewJob.as_view(),
    ),
    path(
        "recent_view_job/api/v1/get/<int:pk>/",
        form_view.GetRecentViewJob.as_view(),
    ),
    path(
        "recent_view_job/api/v1/create/",
        form_view.CreateRecentViewJob.as_view(),
    ),
    path(
        "recent_view_job/api/v1/update/<int:pk>/",
        form_view.UpdateRecentViewJob.as_view(),
    ),
    path(
        "recent_view_job/api/v1/delete/<int:pk>/",
        form_view.DeleteRecentViewJob.as_view(),
    ),
    path(
        "saved_position/api/v1/list/",
        form_view.GetAllSavedPosition.as_view(),
    ),
    path(
        "saved_position/api/v1/get/<int:pk>/",
        form_view.GetSavedPosition.as_view(),
    ),
    path(
        "saved_position/api/v1/create/",
        form_view.CreateSavedPosition.as_view(),
    ),
    path(
        "saved_position/api/v1/update/<int:pk>/",
        form_view.UpdateSavedPosition.as_view(),
    ),
    path(
        "saved_position/api/v1/delete/<int:pk>/",
        form_view.DeleteSavedPosition.as_view(),
    ),
    path(
        "position_alert/api/v1/list/",
        form_view.GetAllPositionAlert.as_view(),
    ),
    path(
        "position_alert/api/v1/get/<int:pk>/",
        form_view.GetPositionAlert.as_view(),
    ),
    path(
        "position_alert/api/v1/create/",
        form_view.CreatePositionAlert.as_view(),
    ),
    path(
        "position_alert/api/v1/update/<int:pk>/",
        form_view.UpdatePositionAlert.as_view(),
    ),
    path(
        "position_alert/api/v1/delete/<int:pk>/",
        form_view.DeletePositionAlert.as_view(),
    ),
    # AppliedPosition
    path(
        "applied_position/api/v1/list/",
        form_view.GetAllAppliedPosition.as_view(),
    ),
    path(
        "op-applied_position/api/v1/list/",
        form_view.OpGetAllAppliedPosition.as_view(),
    ),
    path(
        "my-applications/api/v1/op-list/",
        form_view.GetOpMyApplications.as_view(),
    ),
    path(
        "internal-applicant/api/v1/list/",
        form_view.GetInternalApplicants.as_view(),
    ),
    path(
        "internal-applicant/api/v1/op-list/",
        form_view.GetOpInternalApplicants.as_view(),
    ),
    path(
        "applied_position/api/v1/get/<int:pk>/",
        form_view.GetAppliedPosition.as_view(),
    ),
    path(
        "applied_position/api/v1/create/",
        form_view.CreateAppliedPosition.as_view(),
    ),
    path(
        "applied_position/api/v1/share/",
        form_view.ShareAppliedPosition.as_view(),
    ),
    path(
        "applied_position/api/v1/update/<int:pk>/",
        form_view.UpdateAppliedPosition.as_view(),
    ),
    path(
        "applied_position/api/v1/reject-candidate/<int:pk>/",
        form_view.RejectCandidateApplication.as_view(),
    ),
    path(
        "applied_position/api/v1/delete/<int:pk>/",
        form_view.DeleteAppliedPosition.as_view(),
    ),
    path(
        "applied_position/api/v1/withdrawn-list/",
        form_view.GetAllWithdrawnPosition.as_view(),
    ),
    path(
        "applied_position/api/v1/withdraw/<int:pk>/",
        form_view.WithdrawAppliedPosition.as_view(),
    ),
    # Reason
    path("reason/api/v1/list/", form_view.GetAllReason.as_view()),
    path("reason/api/v1/op-list/", form_view.GetAllOpReason.as_view()),
    path("reason/api/v1/create/", form_view.CreateReason.as_view()),
    path("reason/api/v1/get/<int:pk>/", form_view.GetReason.as_view()),
    path("reason/api/v1/update/<int:pk>/", form_view.UpdateReason.as_view()),
    path("reason/api/v1/delete/<int:pk>/", form_view.DeleteReason.as_view()),
    # ReasonType
    path("reasontype/api/v1/list/", form_view.GetAllReasonType.as_view()),
    path("reasontype/api/v1/create/", form_view.CreateReasonType.as_view()),
    path("reasontype/api/v1/get/<int:pk>/", form_view.GetReasonType.as_view()),
    path("reasontype/api/v1/update/<int:pk>/", form_view.UpdateReasonType.as_view()),
    path("reasontype/api/v1/delete/<int:pk>/", form_view.DeleteReasonType.as_view()),
    # Reminder
    path("reminder/api/v1/list/", form_view.GetAllReminder.as_view()),
    path("reminder/api/v1/create/", form_view.CreateReminder.as_view()),
    path("reminder/api/v1/get-reminders/", form_view.GetRemindersList.as_view()),
    # Interview Listing
    path("interviews/api/v1/list/", form_view.GetAllInterviews.as_view()),
    path("interviews/api/v1/op-list/", form_view.GetAllOpInterviews.as_view()),
    path("interviews/api/v1/filtered/list/", form_view.GetFilteredInterviews.as_view()),
    # CandidateToRatingReview
    path("candidate/api/v1/list/", form_view.GetCandidateRatingReview.as_view()),
    path("candidate/api/v1/op-list/", form_view.GetOpCandidateRatingReview.as_view()),
    # OfferList
    # path("offer_list/api/v1/list/", form_view.GetOfferList.as_view()),
    # #Dashboard
    path("dashboard/api/v1/list/", form_view.GetDashboard.as_view()),
    # ActivityCount
    # path("activity/api/v1/list/", form_view.ActivityCount.as_view()),
    # JobBoardTemplate
    path("job_board_template/api/v1/list/", form_view.GetJobBoardTemplate.as_view()),
    # InternalAndExternalJobListing
    path("Internal/api/v1/list/", form_view.GetInternalJobListing.as_view()),
    path("external/api/v1/list/", form_view.GetExternalJobListing.as_view()),
    path("applied_position/api/v1/next_candidate/", form_view.GetDataForNextCandidate.as_view()),
    # JobDescriptionImage
    path("job_description_image/api/v1/create/", form_view.CreateJobDescriptionImage.as_view()),
    # OfferList
    path("resume_review_list/api/v1/list/", form_view.GetResumeReviewList.as_view()),
    # Candidate_Activity_List
    path("candidate_activity_list/api/v1/list/", form_view.GetCandidateActivityList.as_view()),
    # SendMail_For_Interview
    path("sendmail/api/v1/send_interview_schedule_mail/", form_view.SendInterviewSchedulewMail.as_view()),
    # Position_Gragh
    path("graph/api/v1/position_graph/", form_view.PositionGraph.as_view()),
    # AllPositionApprovalList
    # path(
    #     "position_approval/api/v1/list/",
    #     form_view.GetAllPositionApprovalListing.as_view(),
    # ),
    # ApplicantDocument
    path("document/api/v1/list/", form_view.GetAllApplicantDocuments.as_view()),
    path("document/api/v1/create/", form_view.CreateApplicationDocument.as_view()),
    path("applicant/api/v1/send_mail/", form_view.SendEmailView.as_view()),
    # Send_Email
    path("approval/api/v1/send-mail-to-candidate/<int:applied_position_id>/", SendEmailToCandidateView.as_view()),
    path("reminder/api/v1/send-reminder-mail/<int:applied_position_id>/", SendReminderEmail.as_view()),
    path("applied-position/change-status/<int:applied_position_id>/", UpdateAppliedPositionStatusView.as_view()),
    # Career Template View
    path("career-template/api/v1/list/", GetAllCareerTemplateView.as_view()),
    path("career-template/api/v1/career-template/", CareerTemplateView.as_view()),
    # MMacros
    path("macros/api/v1/get-macros/", GetMacros.as_view()),
    # Insights
    path("insights/api/v1/get-insights/", GetInsights.as_view()),
    path("insights/api/v1/get-review-interview-insights/", GetReviewToInterviewInsights.as_view()),
    path("insights/api/v1/get-avg-time-insights/", GetAvgFileTime.as_view()),
    path("insights/api/v1/get-avg-time-in-stage/", GetAvgTimeInStage.as_view()),
    path("insights/api/v1/get-reject-after-review/", GetCompaniesRejectedAfterReview.as_view()),
    path("insights/api/v1/get-pipeline/", GetPipeLine.as_view()),
    path("insights/api/v1/get-avg-time-to-hire/", GetAvgTimeToHire.as_view()),
    path("insights/api/v1/get-reviews-to-reject/", GetReviewToReject.as_view()),
    # User selected fields
    path("filter/api/v1/selected-fields/", UserSelectedFieldsAPI.as_view()),
    path(
        "unapproved_applied_position/api/v1/create/",
        form_view.UAAPView.as_view(),
    ),
    path(
        "applied_position/api/v1/get-candidate-active/<str:pk>",
        form_view.GetCandidateActiveApplication.as_view(),
    ),
    path(
        "applied_position/api/v1/get-next-candidate",
        form_view.GetNextInternalCandidate.as_view(),
    ),
    path(
        "resume-reviews/api/v1/get-next-candidate",
        form_view.GetReviewReNextCandidate.as_view(),
    ),
    path(
        "new-hires/api/v1/get-next-candidate",
        form_view.GetNextNewHire.as_view(),
    ),
    path(
        "applied_position/api/v1/undo-reject/<int:applied_position>",
        form_view.UndoCandidateStage.as_view(),
    ),
    path(
        "applied_position/api/v1/get-op-interviews",
        form_view.GetOpAllInterviews.as_view(),
    ),
    path(
        "hires/api/v1/confirm-joining/<int:pk>/",
        form_view.GetConfirmJoining.as_view(),
    ),
    path(
        "accept-candidate-joining/",
        form_view.AcceptCandidateJoiningonMail.as_view(),
    ),
    path(
        "accept-offer-approval-mail/<str:offer_approval_id>/<str:applied_postion_id>/",
        form_view.AcceptOfferApprovalEmail.as_view(),
    ),
    path(
        "accept-position-approval-mail/<str:position_approval_id>/",
        form_view.AcceptPositionApprovalEmail.as_view(),
    ),
]
