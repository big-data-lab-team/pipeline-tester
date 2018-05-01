from django.test import LiveServerTestCase
import atop.tests.simulators as sims
from atop.tests.simulators import urldesc_server_obj
import atop.tests.tools as tools
from atop.tests.simulators import URLSimulatorState as State

from atop.models import Descriptor, CarminPlatform
from django.contrib.auth.models import User
from django.db.models import Q
from atop.models import EXECUTION_STATUS_UNCHECKED, EXECUTION_STATUS_ERROR, EXECUTION_STATUS_FAILURE, EXECUTION_STATUS_SUCCESS
import atop.descriptor as desc_utils


#TODO: Check that when automatic updating is off, the descriptor data does not change

class URLBasedDescriptorTestCase(LiveServerTestCase):
    
    def setUp(self):
        self.urldesc_sim = self.live_server_url + "/urldesc_simulation/"
        urldesc_server_obj.create_url("url1")
        self.server_url_1 = self.live_server_url + "/urldesc_simulation/url1/"
        self.dummy_user = User.objects.create()

    def tearDown(self):
        tools.delete_user_testing_data()

    # [state 1] Valid descriptor on URL
    # [state 2] Different descriptor on same URL
    # [state 4] Same descriptor on same URL
    def test_descriptor_data_change(self):
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_A))
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_B))
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_B))

        updater = tools.URLBasedDescriptorUpdater(self.server_url_1, self.dummy_user)

        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.VALID_SUCC_DESC_A_MD5]) == True


        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.VALID_SUCC_DESC_B_MD5]) == True

        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.VALID_SUCC_DESC_B_MD5]) == True


  
    # [state 1] Valid descriptor on URL
    # [state 2] Different descriptor on same URL (but descriptor was submitted initially with automatic updating set to off)
    def test_no_automatic_update(self):
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_A))
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_B))    
    
        updater = tools.URLBasedDescriptorUpdater(self.server_url_1, self.dummy_user)        

        updater.update(automatic_updating=False)
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.VALID_SUCC_DESC_A_MD5]) == True


        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.VALID_SUCC_DESC_A_MD5]) == True


    # [state 1] Valid descriptor on URL
    # [state 2] Invalid descriptor on same URL
    # [state 3] Same invalid descriptor on same URL
    # [state 4] New invalid descriptor on same URL
    # [state 5] Same valid descriptor fron state 1 on same URL
    # [state 6] URL sends bad request.
    # [state 7] New invalid descriptor
    # [state 8] Valid descriptor on URL
    def test_errors(self):
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_A))
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.INVALID_DESC_A))            
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.INVALID_DESC_A))
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.INVALID_DESC_B))
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_A))
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_UNREACHABLE, None))
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.INVALID_DESC_C))
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_B))

        updater = tools.URLBasedDescriptorUpdater(self.server_url_1, self.dummy_user)     
       
        # [state 1]
        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.VALID_SUCC_DESC_A_MD5]) == True

        # [state 2]
        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.INVALID_DESC_A_MD5]) == True

        # [state 3]
        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.INVALID_DESC_A_MD5]) == True

        # [state 4]
        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.INVALID_DESC_B_MD5]) == True

        # [state 5]
        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.VALID_SUCC_DESC_A_MD5]) == True

        # [state 6] (As we are facing a server error, the MD5 should be equal to the MD5 of the last fetched descriptor)
        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.VALID_SUCC_DESC_A_MD5]) == True

        # [state 7]
        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.INVALID_DESC_C_MD5]) == True

        # [state 8]
        updater.update()
        descriptors = Descriptor.objects.all()
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 1
        assert tools.md5_compare(Descriptor.objects, [tools.VALID_SUCC_DESC_B_MD5]) == True


    #TODO: Do this in another test?
    # [state 1] Broken URL
    def test_bad_submissions(self):
        
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_UNREACHABLE, None))
        urldesc_server_obj.add_state("url1", State(State.SERVER_STATUS_VALID, tools.INVALID_DESC_A))

        # Getting false for validate() means that submission will not proceed
        data_cand = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateURLContainer(self.server_url_1), user=self.dummy_user)
        assert data_cand.validate() == False
        
        data_cand = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateURLContainer(self.server_url_1), user=self.dummy_user)
        assert data_cand.validate() == False


