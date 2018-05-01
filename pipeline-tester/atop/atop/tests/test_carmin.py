from django.test import TestCase
from atop.common import HTTPGetter
from django.test import LiveServerTestCase



from atop.tests.simulators import carmin_server_obj
from atop.tests.simulators import CarminSimulatorState as State
import atop.carmin as carmin

from atop.models import Descriptor, CarminPlatform
from django.contrib.auth.models import User
from django.db.models import Q
from atop.models import EXECUTION_STATUS_UNCHECKED, EXECUTION_STATUS_ERROR, EXECUTION_STATUS_FAILURE, EXECUTION_STATUS_SUCCESS
from atop.runqueue import RunQueue
import atop.tests.tools as tools



class CarminTestCase(LiveServerTestCase):
    
    APIKEYS = [123]

    def setUp(self):
        self.carmin_url = self.live_server_url + "/carmin_simulation/"
        carmin_server_obj.create_server("carmin_serv", self.APIKEYS)
        self.carmin_server_url = self.live_server_url + "/carmin_simulation/carmin_serv"
        self.cached_db_carmin = None
        self.dummy_user = User.objects.create()


    def tearDown(self):
        tools.delete_user_testing_data()
        


    def request_carmin(self, apikey, to_schedule=False):
        if (not self.cached_db_carmin):
            carmin_data = carmin.CarminPlatformCandidate(self.carmin_server_url, apikey, self.dummy_user)
            carmin_data.submit()
            #if (carmin_data.is_valid()):
                #print(carmin_data.get_message())            
            self.cached_db_carmin = carmin_data.get_db()
        else:
            carmin_entry = carmin.CarminPlatformEntry(self.cached_db_carmin)
            carmin_entry.update(scheduled=to_schedule)

    def get_descriptors(self, db_carmin):
        descriptors = Descriptor.objects.filter(carmin_platform=db_carmin).filter(user_id=self.dummy_user)
        return descriptors

    def get_carmin_platform(self):
        carmin_server = CarminPlatform.objects.filter(user=self.dummy_user).all()[0]
        return carmin_server        

    def md5_compare(self, query_set, expected_md5_list):
        target_md5_list = []
        for descriptor in query_set.all():
            target_md5_list.append(descriptor.md5)
        for expected_md5 in expected_md5_list:
            if (not (expected_md5 in target_md5_list)):
                return False
        return True

    def check_status(self, descriptor_md5, expected_status):
        desc = Descriptor.objects.filter(md5=descriptor_md5).all()[0]
        if (desc):
            if (desc.execution_status == expected_status):
                return True
        return False
        
    #TODO: Try with different CARMIN server at the same time.

    def test_run(self):
        
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_A, tools.VALID_UNSUCC_DESC_A, tools.INVALID_DESC_C]))            
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_A, tools.VALID_UNSUCC_DESC_A, tools.INVALID_DESC_C]))            
        
        # prepare the descriptors
        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        
        run_queue = RunQueue()
        run_queue.add(self.dummy_user)
        run_queue.serve()
        #assert len(descriptors) == 2
        assert self.check_status(tools.VALID_SUCC_DESC_A_MD5, EXECUTION_STATUS_SUCCESS) == True
        assert self.check_status(tools.VALID_UNSUCC_DESC_A_MD5, EXECUTION_STATUS_FAILURE) == True


    # [state 1] Valid CARMIN platform with 3 valid descriptors
    # [state 2] Valid CARMIN platform with 3 invalid descriptors and the same 3 valid descriptors 
    # [state 3] Valid CARMIN platform with the same 3 invalid descriptors and 1 new valid descriptor
    # [state 4] Valid CARMIN platform with the same valid descriptor and 1 invalid descriptor from the previous state 
    def test_error_valid_to_invalid(self):
        
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_A, tools.VALID_SUCC_DESC_B, tools.VALID_SUCC_DESC_C]))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 6, [tools.VALID_SUCC_DESC_A, 
                                                                                        tools.VALID_SUCC_DESC_B,
                                                                                        tools.VALID_SUCC_DESC_C,
                                                                                        tools.INVALID_DESC_A,
                                                                                        tools.INVALID_DESC_B, 
                                                                                        tools.INVALID_DESC_C,]))

        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 4, [tools.INVALID_DESC_A, tools.INVALID_DESC_B, tools.INVALID_DESC_C, tools.VALID_SUCC_DESC_D]))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 2, [tools.INVALID_DESC_B, tools.VALID_SUCC_DESC_D]))


        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        assert len(descriptors) == 3
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 3
        assert True == self.md5_compare(descriptors, [tools.VALID_SUCC_DESC_A_MD5, tools.VALID_SUCC_DESC_B_MD5, tools.VALID_SUCC_DESC_C_MD5])


        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        #for descriptor in descriptors.all():
            #print(descriptor.tool_name)
        assert len(descriptors) == 6
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 3
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 3
        assert True == self.md5_compare(descriptors,  [tools.VALID_SUCC_DESC_A_MD5, 
                                                       tools.VALID_SUCC_DESC_B_MD5,
                                                       tools.VALID_SUCC_DESC_C_MD5,
                                                       tools.INVALID_DESC_A_MD5,
                                                       tools.INVALID_DESC_B_MD5, 
                                                       tools.INVALID_DESC_C_MD5,])



        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        #print(len(descriptors))        
        assert len(descriptors) == 4
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 3
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 1
        assert True == self.md5_compare(descriptors, [tools.INVALID_DESC_A_MD5, tools.INVALID_DESC_B_MD5, tools.INVALID_DESC_C_MD5, tools.VALID_SUCC_DESC_D_MD5])

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        assert len(descriptors) == 2
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 1
        assert True == self.md5_compare(descriptors, [tools.INVALID_DESC_B_MD5, tools.VALID_SUCC_DESC_D_MD5])


    # [state 1] Valid CARMIN platform with 3 valid descriptors
    # [state 2] Valid CARMIN platform with 3 executabe pipelines but 0 descriptors
    # [state 3] Valid CARMIN platform with 3 executabe pipelines but 0 descriptors
    # [state 4] Unreachable CARMIN platform
    # [state 5] Valid CARMIN platform with 0 executabe pipelines and 0 descriptors
    # [state 6] Valid CARMIN platform with 1 executabe pipeline and 1 valid descriptor
    def test_error_emptiness(self):
        
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_A, tools.VALID_SUCC_DESC_B, tools.VALID_SUCC_DESC_C]))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 3, []))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 3, []))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_UNREACHABLE, 0, []))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 0, []))             
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 1, [tools.VALID_SUCC_DESC_A]))

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        # We must have populated the db with 3 valid descriptor entries
        assert len(descriptors) == 3
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 3

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        # The descriptors have all been removed, this should cause the all the descriptors pertaining to the carmin server to be removed from the database.
        assert len(descriptors) == 0

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        # Again here, we should have no descriptors.
        assert len(descriptors) == 0

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        # The server is unreachable. We should have no descriptors again.
        assert len(descriptors) == 0

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        # The server is back-up. We should have no descriptors again.
        assert len(descriptors) == 0

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        # We should have one descriptor now
        assert len(descriptors) == 1
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 1



    # [state 1] Valid CARMIN paltform with 2 valid descriptors and 1 invalid descriptor
    # [state 2] Valid CARMIN paltform but all API keys are rejected
    # [state 3] Valid CARMIN platform with 3 descriptors that are identical to all the ones from state 1
    # [state 4] Unreachable CARMIN platform
    # [state 5] Valid CARMIN platform with 3 descriptors that are identical to all the ones from state 1
    # [state 6] Invalid CARMIN platform
    # [state 7] Valid CARMIN platform with 3 descriptors that are identical to all the ones from state 1

    def test_error_carmin_behavior_recovery(self):
    
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_A, tools.VALID_SUCC_DESC_B, tools.INVALID_DESC_C]))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_REFUSE_ALL_APIKEYS, 0, []))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_A, tools.VALID_SUCC_DESC_B, tools.INVALID_DESC_C]))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_UNREACHABLE, 0, []))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_A, tools.VALID_SUCC_DESC_B, tools.INVALID_DESC_C]))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_NOT_CARMIN, 0, []))
        carmin_server_obj.add_state("carmin_serv", State(State.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_A, tools.VALID_SUCC_DESC_B, tools.INVALID_DESC_C]))

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        # We populate the db with 2 valid and 1 invalid descriptors
        assert len(descriptors) == 3
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 2
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 1


        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        assert len(descriptors) == 3
        # Impossible to communicate properly with the CARMIN server as he rejects /pipelines requests
        # Still, the descriptors added previously should remain, but with an error message for each, to indicate the situation with the CARMIN server
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 3

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        # We should get the same descriptors from state 1. Also, the error messages from the previous state should be cleared up.
        assert len(descriptors) == 3
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 2
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 1

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        assert len(descriptors) == 3
        # Server is down.
        # Still, the descriptors added previously should remain, but with an error message for each, to indicate the situation with the CARMIN server
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 3

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        # We should get the same descriptors from state 1. Also, the error messages from the previous state should be cleared up.
        assert len(descriptors) == 3
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 2
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 1

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        assert len(descriptors) == 3
        # Server does not respond with expected JSON data.
        # Still, the descriptors added previously should remain, but with an error message for each, to indicate the situation with the CARMIN server
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 3

        self.request_carmin(self.APIKEYS[0])
        carmin = self.get_carmin_platform()
        descriptors = self.get_descriptors(carmin)
        # We should get the same descriptors from state 1. Also, the error messages from the previous state should be cleared up.
        assert len(descriptors) == 3
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_UNCHECKED) & Q(error_message=""))) == 2
        assert len(descriptors.filter(Q(execution_status=EXECUTION_STATUS_ERROR) & ~Q(error_message=""))) == 1

