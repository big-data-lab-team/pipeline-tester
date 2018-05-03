from django.test import TestCase

from atop.models import Descriptor
from django.contrib.auth.models import User
import atop.tests.tools as tools
import atop.models as db


import atop.descriptor as desc_utils

class TestGenerationTestCase(TestCase):

    def setUp(self):
        self.dummy_user = User.objects.create()

    def test_descriptor_valid_succ_multiple_tests(self):
        data = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateLocalRawContainer(tools.VALID_MULTIPLE_TESTS_DESC.encode()), user=self.dummy_user)
        data.submit()
        
        desc = db.Descriptor.objects.all()
        assert len(desc) == 1
        assert tools.multiple_tests_comparator.compare(desc[0]) == True


    def test_descriptor_valid_succ_C(self):
        data = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateLocalRawContainer(tools.VALID_SUCC_DESC_C.encode()), user=self.dummy_user)
        data.submit()
        
        desc = db.Descriptor.objects.all()
        assert len(desc) == 1
        assert tools.valid_succ_desc_C_details.compare(desc[0]) == True


    def test_descriptor_valid_unsucc_A(self):
        data = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateLocalRawContainer(tools.VALID_UNSUCC_DESC_A.encode()), user=self.dummy_user)
        data.submit()
        
        desc = db.Descriptor.objects.all()
        assert len(desc) == 1
        assert tools.valid_unsucc_desc_A_details.compare(desc[0]) == True

    def test_descriptor_valid_unsucc_B(self):
        data = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateLocalRawContainer(tools.VALID_UNSUCC_DESC_B.encode()), user=self.dummy_user)
        data.submit()
        
        desc = db.Descriptor.objects.all()
        assert len(desc) == 1
        assert tools.valid_unsucc_desc_B_details.compare(desc[0]) == True

    def test_descriptor_valid_unsucc_C(self):
        data = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateLocalRawContainer(tools.VALID_UNSUCC_DESC_C.encode()), user=self.dummy_user)
        data.submit()
        
        desc = db.Descriptor.objects.all()
        assert len(desc) == 1
        assert tools.valid_unsucc_desc_C_details.compare(desc[0]) == True
        
