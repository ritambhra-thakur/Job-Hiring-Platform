from django.test import Client, TestCase

from company.models import Company
from role.models import Role
from user.models import User


class TestAdminPanel(TestCase):
    def create_user(self):
        self.username = "admin_infer"
        self.email = "admin@admin.com"
        self.password = User.objects.make_random_password()

        company_obj = Company.objects.create(company_name="Infertalent", url_domain="infer")
        role_obj = Role.objects.create(name="superuser")

        user_obj = User.objects.create(username=self.username, email=self.email, password=self.password, user_company=company_obj, user_role=role_obj)
        user_obj.is_active = True
        user_obj.is_superuser = True
        user_obj.is_staff = True
        user_obj.set_password(self.password)
        user_obj.first_name = "admin"
        user_obj.middle_name = "admin"
        user_obj.last_name = "admin"
        user_obj.save()

    def test_spider_admin(self):
        self.create_user()
        client = Client()
        client.login(username=self.email, password=self.password)
        admin_pages = [
            # admin
            "/admin/",
            # user
            "/admin/user/user/",
            "/admin/user/profile/",
            "/admin/user/media/",
            # stage
            "/admin/stage/stage/",
            "/admin/stage/positionstage/",
            "/admin/stage/pipeline/",
            # scorecard
            "/admin/scorecard/positionattribute/",
            "/admin/scorecard/competency/",
            "/admin/scorecard/attribute/",
            # role
            "/admin/role/role/",
            "/admin/role/rolepermission/",
            "/admin/role/rolelist/",
            "/admin/role/access/",
        ]

        for page in admin_pages:
            resp = client.get(page)

            assert resp.status_code == 200
            assert "<!DOCTYPE html" in str(resp.content)
