from django.test import LiveServerTestCase
from django.test import Client
from atop.models import Descriptor
from django.contrib.auth.models import User
from atop.runqueue import RunQueue
from atop.views import DATA_SELECTOR_CARMIN, DATA_SELECTOR_FILE, DATA_SELECTOR_URL
from atop.tests.simulators import carmin_server_obj
from atop.tests.simulators import urldesc_server_obj
from atop.tests.simulators import CarminSimulatorState as CARState
from atop.tests.simulators import URLSimulatorState as URLState
import atop.tests.tools as tools
from django.core.files.base import ContentFile
from atop.models import EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_FAILURE, EXECUTION_STATUS_SCHEDULED
from django.db.models import Q

class RunTestCase(LiveServerTestCase):
    
    APIKEYS = [123]

    def setUp(self):
        self.carmin_url = self.live_server_url + "/carmin_simulation/"
        carmin_server_obj.create_server("carmin_serv1", self.APIKEYS)
        carmin_server_obj.create_server("carmin_serv2", self.APIKEYS)
        carmin_server_obj.create_server("carmin_serv3", self.APIKEYS)
        self.carmin_server_1_url = self.carmin_url + "carmin_serv1" + "/"
        self.carmin_server_2_url = self.carmin_url + "carmin_serv2" + "/"
        self.carmin_server_3_url = self.carmin_url + "carmin_serv3" + "/"

        self.url_server_url = self.live_server_url + "/urldesc_simulation/"
        urldesc_server_obj.create_url("url1")
        urldesc_server_obj.create_url("url2")
        urldesc_server_obj.create_url("url3")
        self.url_server_1_url = self.url_server_url + "url1" + "/" 
        self.url_server_2_url = self.url_server_url + "url2" + "/"
        self.url_server_3_url = self.url_server_url + "url3" + "/"


    def tearDown(self):
        tools.delete_user_testing_data() 

    # tools.VALID_SUCC_DESC_A VALID_SUCC_DESC_B VALID_SUCC_DESC_C
    def test_run(self):

        dummy_user_1 = User.objects.create_user(username="xxxx", password="zzzz")

        run_queue = RunQueue()

        scheduled, error_message = run_queue.add(dummy_user_1)
        assert scheduled == False        

        carmin_server_obj.add_state("carmin_serv1", CARState(CARState.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_A, tools.VALID_SUCC_DESC_B, tools.VALID_SUCC_DESC_C]))            
        carmin_server_obj.add_state("carmin_serv1", CARState(CARState.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_A, tools.INVALID_DESC_C]))            

        carmin_server_obj.add_state("carmin_serv2", CARState(CARState.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_B]))            
        carmin_server_obj.add_state("carmin_serv2", CARState(CARState.SERVER_STATUS_VALID, 3, [tools.VALID_SUCC_DESC_C, tools.INVALID_DESC_A]))

        carmin_server_obj.add_state("carmin_serv3", CARState(CARState.SERVER_STATUS_VALID, 1, [tools.INVALID_DESC_B]))
        carmin_server_obj.add_state("carmin_serv3", CARState(CARState.SERVER_STATUS_VALID, 3, [tools.VALID_UNSUCC_DESC_B]))                     

        urldesc_server_obj.add_state("url1", URLState(URLState.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_A))
        urldesc_server_obj.add_state("url1", URLState(URLState.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_B))

        urldesc_server_obj.add_state("url2", URLState(URLState.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_A))
        urldesc_server_obj.add_state("url2", URLState(URLState.SERVER_STATUS_UNREACHABLE, tools.VALID_UNSUCC_DESC_B))


        urldesc_server_obj.add_state("url3", URLState(URLState.SERVER_STATUS_VALID, tools.VALID_SUCC_DESC_D))
        urldesc_server_obj.add_state("url3", URLState(URLState.SERVER_STATUS_VALID, tools.INVALID_DESC_B))

        client = Client()
        client.login(username="xxxx", password="zzzz")

        client.post("/", {"data_selector": DATA_SELECTOR_CARMIN, "data_carmin_platform_url": self.carmin_server_1_url, "data_carmin_platform_apikey": self.APIKEYS[0], "is_public": False})
        client.post("/", {"data_selector": DATA_SELECTOR_CARMIN, "data_carmin_platform_url": self.carmin_server_2_url, "data_carmin_platform_apikey": self.APIKEYS[0], "is_public": False})
        client.post("/", {"data_selector": DATA_SELECTOR_CARMIN, "data_carmin_platform_url": self.carmin_server_3_url, "data_carmin_platform_apikey": self.APIKEYS[0], "is_public": False})
        client.post("/", {"data_selector": DATA_SELECTOR_URL, "data_url": self.url_server_1_url, "is_public": False, "automatic_updating": True})
        client.post("/", {"data_selector": DATA_SELECTOR_URL, "data_url": self.url_server_2_url, "is_public": False, "automatic_updating": True})
        # URL based descriptor but automatic updating is set to off
        client.post("/", {"data_selector": DATA_SELECTOR_URL, "data_url": self.url_server_3_url, "is_public": False, "automatic_updating": False})
        # Local file post
        data_file_1 = ContentFile(tools.VALID_UNSUCC_DESC_C)
        data_file_2 = ContentFile(tools.VALID_UNSUCC_DESC_A)

        client.post("/", {"data_selector": DATA_SELECTOR_FILE, "data_file": data_file_1, "is_public": False})
        client.post("/", {"data_selector": DATA_SELECTOR_FILE, "data_file": data_file_2, "is_public": False})
        assert len(Descriptor.objects.all()) == 10     

        
        scheduled, error_message = run_queue.add(dummy_user_1)
        assert scheduled == True
        scheduled, error_message = run_queue.add(dummy_user_1)
        assert scheduled == False        

        run_queue.serve()

        descs = Descriptor.objects.filter(Q(execution_status=EXECUTION_STATUS_SUCCESS) | Q(execution_status=EXECUTION_STATUS_FAILURE)).all()
        assert len(descs) == 7

        assert tools.check_status(tools.VALID_SUCC_DESC_A_MD5, EXECUTION_STATUS_SUCCESS) == True
        assert tools.check_status(tools.VALID_SUCC_DESC_B_MD5, EXECUTION_STATUS_SUCCESS) == True
        assert tools.check_status(tools.VALID_SUCC_DESC_C_MD5, EXECUTION_STATUS_SUCCESS) == True
        assert tools.check_status(tools.VALID_SUCC_DESC_D_MD5, EXECUTION_STATUS_SUCCESS) == True
        assert tools.check_status(tools.VALID_UNSUCC_DESC_A_MD5, EXECUTION_STATUS_FAILURE) == True
        assert tools.check_status(tools.VALID_UNSUCC_DESC_B_MD5, EXECUTION_STATUS_FAILURE) == True
        assert tools.check_status(tools.VALID_UNSUCC_DESC_C_MD5, EXECUTION_STATUS_FAILURE) == True
