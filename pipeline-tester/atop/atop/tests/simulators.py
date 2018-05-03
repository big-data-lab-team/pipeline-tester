from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
import queue
import json
import os
from atop.common import calculate_MD5
root_path = os.path.realpath(__file__)





class URLSimulatorState:
    
    SERVER_STATUS_UNREACHABLE = 0
    SERVER_STATUS_NOT_DESCRIPTOR = 1
    SERVER_STATUS_VALID = 2

    def __init__(self, server_status, descriptor_data):
        
        self.server_status = server_status
        self.descriptor_data = descriptor_data

    def get(self):
        
        if (self.server_status == self.SERVER_STATUS_UNREACHABLE):
            # We cannot simulate a truly unreachable server with Django.
            # We have to respond with something, but this a good compromise.
            # It should trigger an exception in the layer that takes cares of HTTP requests.
            return HttpResponseBadRequest()
        
        if (self.server_status == self.SERVER_STATUS_NOT_DESCRIPTOR):
            return HttpResponse("Lorem ipsum dolor sit amet, pri congue labitur mediocritatem cu")
        
        if (self.server_status == self.SERVER_STATUS_VALID):
            if (self.descriptor_data != None):
                return HttpResponse(self.descriptor_data)


class URLSimulatorServer:
    
    def __init__(self, url):
        self.url = url
        self.states = queue.Queue()

    def add_state(self, state):
        self.states.put(state)
    
    def get(self):
        state = self.states.get()
        return state.get()        

class URLSimulator:
    
    def __init__(self):
        self.urls = {}
    
    def create_url(self, url):
        server = URLSimulatorServer(url)
        self.urls[url] = server

    def get(self, url):
        url = self.urls[url]
        return url.get()

    def add_state(self, url, state):
        self.urls[url].add_state(state)   















class CarminSimulatorState:
    
    SERVER_STATUS_UNREACHABLE = 0
    SERVER_STATUS_NOT_CARMIN = 1
    SERVER_STATUS_VALID = 2
    SERVER_STATUS_REFUSE_ALL_APIKEYS = 3

    
    def __init__(self, server_status, executable_pipeline_count=0, descriptor_list=[]):
        
        self.server_status = server_status
        self.executable_pipeline_count = executable_pipeline_count
        
        self.pipelines = {}
        self.descriptors = {}
        self._generatePipelines(descriptor_list)
        

        
    def _generatePipelines(self, descriptor_list):
        
        self.pipelines = [{"identifier": "non-executable pipeline"}]
        for i in range(self.executable_pipeline_count):
            pipeline = {"canExecute": True}
            id = "pipeline_" + str(i)
            pipeline["identifier"] = id
            if (len(descriptor_list) > i):
                self.descriptors[id] = descriptor_list[i]
            self.pipelines.append(pipeline)
                
                
    def get_descriptor(self, id):
        return self.descriptors.get(id)
        
    def get_pipelines(self):
        return self.pipelines
        
    def is_status(self, status):
        if (self.server_status == status):
            return True
        return False
        
        

class CarminSimulatorServer:

    def __init__(self, name, apikeys):
        self.name = name
        self.states = queue.Queue()
        self.current_state = None
        self.apikeys = apikeys
        
    def add_apikey(self, apikey):
        self.apikeys.append(apikey)
        
    def add_state(self, state):
        self.states.put(state)
    
    def _get_state(self, to_pop=False):
        
        if (to_pop):
            state = self.states.get()
            self.current_state = state
        else:
            state = self.current_state
        
        return state
        
        
    def get_platform(self):
       
        state = self._get_state(to_pop=True)
        if (not state):
            return HttpResponse("")


        if (state.is_status(CarminSimulatorState.SERVER_STATUS_UNREACHABLE)):
            # It is not possible for WSGI to ignore a request.
            # In this case, we simply return a bad request.
            # This should trigger a HTTPError from the layer that deals with raw http requests, which is a good compromise.
            #return HttpResponse("")
            return HttpResponseBadRequest()
        
        if (state.is_status(CarminSimulatorState.SERVER_STATUS_NOT_CARMIN)):
            # Send a non-carmin related response
            return HttpResponse("Lorem ipsum dolor sit amet, pri congue labitur mediocritatem cu")
        
        if (state.is_status(CarminSimulatorState.SERVER_STATUS_VALID)):
            return JsonResponse({"platformName": "simulated CARMIN server 1.0"})
        
    
    
    def get_pipelines(self, apikey):

        state = self._get_state()
        if (not state):
            return HttpResponse("")


        if (state.is_status(CarminSimulatorState.SERVER_STATUS_REFUSE_ALL_APIKEYS) or (not (int(apikey) in self.apikeys))):
            #return JsonResponse({"errorCode": 0, "errorMessage": "Wrong APIKEY"}
            return HttpResponseBadRequest()
            
        else:
            pipelines = state.get_pipelines()
            return JsonResponse(pipelines, safe=False)
            
            
    def get_descriptor(self, apikey, pipeline_id):
        
        state = self._get_state()
        if (not state):
            return HttpResponse("")

        descriptor = state.get_descriptor(pipeline_id)
        if (not descriptor):
            return HttpResponseBadRequest()
        
        return HttpResponse(descriptor)    
             
    

        
        
        
        
class CarminSimulator:
    
    def __init__(self):
        self.servers = {}
        
    def create_server(self, server_name, apikeys):
        self.servers[server_name] = CarminSimulatorServer(server_name, apikeys)
        
    def _get_server(self, server_name):
        return self.servers.get(server_name)
        
    def add_state(self, server_name, state):
        server = self._get_server(server_name)
        server.add_state(state)
        
        
    def get_platform(self, server_name):
  
        server = self._get_server(server_name)
        if (not server):
            return HttpResponseBadRequest()

        return server.get_platform()
        
    def get_pipelines(self, server_name, apikey):
        
        server = self._get_server(server_name)
        if (not server):
            return HttpResponseBadRequest()
        
        return server.get_pipelines(apikey)
        
    def get_descriptor(self, server_name, apikey, pipeline_id):
        
        server = self._get_server(server_name)
        if (not server):
            return HttpResponseBadRequest()

        return server.get_descriptor(apikey, pipeline_id)
        
        

        
        
carmin_server_obj = CarminSimulator()
urldesc_server_obj = URLSimulator()


def urldesc_simulation_dispatcher(request, url):

    
    return urldesc_server_obj.get(url)


        
def carmin_simulation_dispatcher(request, carmin_server, method=None, pipeline_id=None):

    #carmin_server = captured["carmin_server"]    


    if (method):
        if (method == "platform"):
            return carmin_server_obj.get_platform(carmin_server)
        elif (method == "pipelines"):
            user_api_key = request.META.get("HTTP_APIKEY")
            return carmin_server_obj.get_pipelines(carmin_server, user_api_key)
    else:
        user_api_key = request.META.get("HTTP_APIKEY")
        return carmin_server_obj.get_descriptor(carmin_server, user_api_key, pipeline_id)
        
    return HttpResponseBadRequest()
        
        

#from atop.common import HTTPGetter


import atop.carmin as carmin
def test(request):

    carmin_server_obj.create_server("carmin_serv", ["123"])
    carmin_server_obj.add_state("carmin_serv", None, CarminSimulatorState(CarminSimulatorState.SERVER_STATUS_VALID, 1, [VALID_SUCC_DESC_A]))
    carmin_server_obj.add_state("carmin_serv", None, CarminSimulatorState(CarminSimulatorState.SERVER_STATUS_UNREACHABLE, 1, [VALID_SUCC_DESC_A]))
    carmin_server_obj.add_state("carmin_serv", None, CarminSimulatorState(CarminSimulatorState.SERVER_STATUS_NOT_CARMIN, 1, [VALID_SUCC_DESC_A]))


    prefix = "http://127.0.0.1:8000/carmin_simulation/" + "carmin_serv"

    carmin_data = carmin.CarminPlatformCandidate(prefix, "123")
    carmin_data.submit()
    db = carmin_data.get_db() 

    #print("validated:" + str(carmin_data.is_valid()))

    #my_getter(prefix + "/platform")
    #my_getter(prefix + "/pipelines", "123")
    #my_getter(prefix + "/pipelines/pipeline_0/boutiquesdescriptor", "123")
    
    #my_getter(prefix + "/platform")

    #my_getter(prefix + "/platform")
    return HttpResponse("")

    
        
        
