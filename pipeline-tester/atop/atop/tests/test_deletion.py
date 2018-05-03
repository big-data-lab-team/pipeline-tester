from django.test import LiveServerTestCase
from django.test import TestCase
from django.test import Client
from atop.models import Descriptor
from django.contrib.auth.models import User
import atop.tests.tools as tools
import atop.descriptor as desc_utils
import atop.models as db
from atop.views import DELETE_TYPE_DESCRIPTOR, DELETE_TYPE_CARMIN_PLATFORM


class TestDeletion(TestCase):


    # Logged in user deleting a descriptor that belongs to him
    def test_valid_deletion(self):
        
        dummy_user = User.objects.create_user(username="xxxx", password="zzzz")

        data = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateLocalRawContainer(tools.VALID_SUCC_DESC_C.encode()), user=dummy_user)
        data.submit()

        desc = db.Descriptor.objects.all()
        desc_data_file_path = str(desc[0].data_file)
        assert tools.file_exists(desc_data_file_path) == True
        assert len(desc) == 1

        client = Client()
        response = client.login(username="xxxx", password="zzzz")
        response = client.get("/delete/", {"id": "1", "type": str(DELETE_TYPE_DESCRIPTOR)})

        desc = db.Descriptor.objects.all()
        assert len(desc) == 0
        assert tools.file_exists(desc_data_file_path) == False

    def tearDown(self):
        tools.delete_user_testing_data()


    # Logged in user deleting a descriptor that does not belong to him
    def test_invalid_deletion1(self):
        
        dummy_user_1 = User.objects.create_user(username="xxxx", password="zzzz")
        dummy_user_2 = User.objects.create_user(username="ffff", password="zzzz")        

        data = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateLocalRawContainer(tools.VALID_SUCC_DESC_C.encode()), user=dummy_user_1)
        data.submit()

        desc = db.Descriptor.objects.all()
        assert len(desc) == 1

        client = Client()
        response = client.login(username="ffff", password="zzzz")
        response = client.get("/delete/", {"id": "1", "type": str(DELETE_TYPE_DESCRIPTOR)})

        desc = db.Descriptor.objects.all()
        assert len(desc) == 1


    # Non-loged in user deleting a descriptor
    def test_invalid_deletion2(self):
        
        dummy_user = User.objects.create_user(username="xxxx", password="zzzz")

        data = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateLocalRawContainer(tools.VALID_SUCC_DESC_C.encode()), user=dummy_user)
        data.submit()

        desc = db.Descriptor.objects.all()
        assert len(desc) == 1

        client = Client()
        response = client.get("/delete/", {"id": "1", "type": str(DELETE_TYPE_DESCRIPTOR)})

        desc = db.Descriptor.objects.all()
        assert len(desc) == 1



