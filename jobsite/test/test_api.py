import abc
import unittest

from django.test import TestCase

from jobsite.models import JobSites


# class SimpleTestCase(TestCase):
#     def test_view(self):
#         if self.assertEqual(1,1):
#            print("yes")
#         elif self.assertEqual(1,2):
#             print("No")
class WidgetTestCase(TestCase):

    def test_default_widget_size(self):
    
        obj=JobSites()
        obj.job_site = 'test'
        obj.company = None
        obj.save()
        obj_1=JobSites.objects.all()
        data=self.client.get("http://127.0.0.1:8000/jobsite/api/v1/list/",{"domain":""})
        if data.status_code != 200:
            print(data.data)
            self.assertEqual(10,100)
        else:
            print(data.data)
            self.assertEqual(10,10)
        # if len(obj_1)>1:
        #     self.client.get()
        #     self.assertEqual(50,50)
        # else:
        #     self.assertEqual(10,100)


        # except:
        #     self.assertEqual(50,10)


        # try:
        #     JobSites.objects.create(job_site="naukri.com")
        #     JobSites.objects.create(company=None)
        #     self.assertEqual(50,50)
        # except:
        #     self.assertEqual(50,150)
        
        # if len(obj)>0:
        #     self.assertEqual(50,50)
        # else:
        #     self.assertEqual(50,12)


  