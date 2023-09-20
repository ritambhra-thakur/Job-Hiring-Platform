import datetime

ROLE_CHOICES = (
    (
        "super_admin",
        "Super Admin",
    ),  # is_staff=True, is_superuser=True = Application Super Admin
    (
        "admin",
        "Admin",
    ),  # is_staff=True, is_superuser=False = Application Admin
    (
        "company_admin",
        "Company Admin",
    ),  # is_staff=False, is_superuser=False = Company Admin
    (
        "agent",
        "Agent",
    ),  # is_staff=False, is_superuser=False = Company Employee
)

TOKEN_TYPE_CHOICES = (
    ("verification", "Email Verification"),
    ("pwd_reset", "Password Reset"),
)

YEAR_CHOICES = [(y, y) for y in range(1970, datetime.date.today().year + 1)]

FIELD_CHOICES = (
    ("string", "string"),
    ("intiger", "intiger"),
    ("boolean", "boolean"),
)

EDUCATION_CHOICES = (
    ("10", "10th"),
    ("12", "12th"),
    ("GD", "Graduation/Diploma"),
    ("MP", "Masters/Post-Graduation"),
    ("DP", "Doctorate/PhD"),
)


POSITION_STATUS = (
    ("draft", "draft"),
    ("active", "active"),
    ("hold", "hold"),
    ("closed", "closed"),
)

APPLICATION_STATUS = (
    ("reject", "reject"),
    ("active", "active"),
    ("hold", "hold"),
    ("hired", "hired"),
    ("kiv", "kiv"),
)
# Some more have been added like "pending-offer" and "approved"
APPROVAL_TYPE = (("All at once", "a-a-o"), ("one to one", "o-t-o"))


EXPERIENCE_TYPE = [("fresher", "fresher"), ("experience", "experience")]

REASON_TYPE = (
    ("Position Rejection", "position_r"),
    ("Offer Rejection", "offer_r"),
    ("Candidate Rejection", "candidate_r"),
    ("Position Hold", "position_h"),
    ("Offer Hold", "offer_h"),
    ("Candidate Hold", "candidate_h"),
    ("Reject", "reject"),
)

MACROS = {
    "{{Position_Name}}": "Position Name",
    "{{Position_No}}": "Position Number/ID",
    "{{Position_Approver}}": "Position Approver Name",
    "{{Reminder}}": "Reminder",
    "{{Candidate_Name}}": "Candidate Name",
    "{{Notification_Email_Template}}": "Notification Email Template",
    "{{Company_Name}}": "Company Name",
    "{{Organization_Name}}": "Organization Name",
    "{{Interviewer_Name}}": "Interviewer Name",
    "{{Company_Website_Link}}": "Company Webiste Link",
    "{{External_Job_Ad_Link}}": "External Job Addd Link",
    "{{Interview_Type}}": "Interview Type",
    "{{Employee_Name}}": "Employee Name",
    "{{Hiring_Manager}}": "Hiring Manager",
    "{{Candidate_Full_Name}}": "Candidate Full Name",
    "{{Candidate_First_Name}}": "Candidate First Name",
    "{{Location}}": "Location",
    "{{Hiring_Managers_Job_Title}}": "Hiring Managers Job Title",
    "{{Start_Date}}": "Start Date",
    "{{Total_Target_Compensation}}": "Total Target Compensation",
    "{{Currency}}": "Currency",
    "{{Bonus_Amount}}": "Bonus Amount",
    "{{Full_Name}}": "Full Name",
    "{{Offer_Approver}}": "Offer Approver Name",
    "{{Time}}": "Time",
    "{{Date}}": "Date",
    "{{Interview_Venue}}": "Interview Venue",
    "{{CompanyLogin_Link}}": "Company Login Link",
    "{{BasicSalary}}": "Basic Salary",
    "{{GuaranteeBonus}}": "Guarantee Bonus",
    "{{SignOnBonus}}": "Sign On Bonus",
    "{{VisaRequired}}": "Visa Required",
    "{{RelocationBonus}}": "Relocation Bonus",
    "{{Timezone}}": "Timezone",
    "{{Candidate_Dashboard_Link}}": "Candidate Dashboard Link",
}

FEATURE_CHOICES = (
    ("google-meet", "Google Meet"),
    ("pdftron", "PDFTron"),
    ("calendly", "Calendly"),
    ("recruiter", "Recruiter")
    # Add more if required
)
