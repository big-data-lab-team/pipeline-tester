from atop.models import CarminPlatform, Descriptor
from django.contrib.auth.models import User

from atop.common import create_temporary_file, calculate_MD5, HTTPGetter
import boutiques as bosh
import json

import atop.descriptor as desc_utils


class CarminPlatformCandidate:
    
    def __init__(self, url, apikey, user=None, is_public=False):
        self.url = url
        self.apikey = apikey
        self.erroneous = False
        self.validated = False
        self.message = ""
        self.JSON_pipelines = None
        self.raw_descriptors = []
        self.descriptors = []
        self.user = user
        self.is_public = is_public

        self.is_carmin_online = False
        self.descriptor_count = 0

        self.name = None
        self.carmin_headers = {"content-type": "application/json", "apikey": apikey}
       
        self.db_carmin_platform = None
        

    def _get_descriptors(self, executable_pipelines):
        raw_descriptors = []
        for pipeline_id in executable_pipelines:
            path = "pipelines/" + pipeline_id + "/boutiquesdescriptor"
            descriptor_url = self._urlize(self.url, path)
            getter = HTTPGetter(descriptor_url, self.carmin_headers)
            if (not getter.is_erroneous()):
                raw_data = getter.get_data()
                if (raw_data):
                    if (self._loadJSON(raw_data)):
                        raw_descriptors.append(raw_data)
        return raw_descriptors


    def _get_valid_descriptor_count(self, raw_descriptors):
        count = 0        
        for raw_descriptor in raw_descriptors:
            descriptor_file = create_temporary_file(raw_descriptor)
            try:
                bosh.validate(descriptor_file.name)
                count += 1
                descriptor_file.close()
            except:
                descriptor_file.close()
        return count


    def _loadJSON(self, data_raw):
        try:
            JSON_data = json.loads(data_raw)
            return JSON_data
        except:
            return None

    def _get_executable_pipelines(self, JSON_data):
        executable_pipelines = []
        for pipeline in JSON_data:
            if (pipeline.get("canExecute") == True):
                pipeline_id = pipeline.get("identifier")
                if (pipeline_id):
                    executable_pipelines.append(pipeline_id)
        return executable_pipelines
            


    def validate(self):
        
        is_carmin_error = lambda JSON_data: True if (isinstance(JSON_data, dict) and JSON_data.get('code') != None) else False
        get_carmin_error = lambda JSON_data, path: "CARMIN error received when querying " + '\'' + path + '\':\n[' + JSON_data['code'] + '] ' + JSON_data.get('message')

        # (1) Do a GET on /platform.
        platform_url = self._urlize(self.url, "platform")
        getter = HTTPGetter(platform_url)
        if (getter.is_erroneous()):
            # Stop, the error message will be the URL error created by _get()
            self.message = "Host could not be reached. The following error was received when querying " + platform_url + ":\n" + getter.get_error()
            return False
        raw_data = getter.get_data()
        JSON_data = self._loadJSON(raw_data)
        if (not JSON_data):
            self.message = "Host reachable but it is not a valid CARMIN platform ('/platform' does not return a JSON string)"
            return False
        if (is_carmin_error(JSON_data)):
            self.message = get_carmin_error(JSON_data, "/platform")
            return False
        self.name = JSON_data.get("platformName")
        if (self.name == None):
            self.message = "Host responded with a JSON string when querying '/platform', but a required property 'platformName' is absent"
            return False
        
        # (2) Do a GET on /pipelines
        pipelines_url = self._urlize(self.url, "pipelines")
        getter = HTTPGetter(pipelines_url, self.carmin_headers)
        if (getter.is_erroneous()):
            self.message = "Host's '/platform' appeared to be reachable and valid, but '/pipelines' is unreachable (Invalid API key ?):\n" + getter.get_error()
            return False
        raw_data = getter.get_data()
        JSON_data = self._loadJSON(raw_data)
        if (not JSON_data):
            self.message = "Host appears to be a CARMIN server but '/pipelines' does not return a valid JSON string (Invalid API key ?)"
            return False
        if (is_carmin_error(JSON_data)):
            self.message = get_carmin_error(JSON_data, "/pipelines")
            return False
        if (not isinstance(JSON_data, list)):
            self.message = "Host appears to be a CARMIN server but '/pipelines' JSON data content is not to a list of objects as expected"
            return False
        executable_pipelines = self._get_executable_pipelines(JSON_data)
        if (len(executable_pipelines) == 0):
            self.message = "Host does not have any pipeline(s) that the user can execute"
            return False
        
        # From this point, we assume that the CARMIN server is valid and online.
        # This data is necessary to determine if a CARMIN server simply does not have any boutiques descriptors.
        # Q: Does a canExecute pipeline indicate that the pipeline MUST have a reachable boutiquesdescriptor ?
        self.is_carmin_online = True

        # (3) GET each pipeline descriptors
        self.raw_descriptors = self._get_descriptors(executable_pipelines)
        if (len(self.raw_descriptors) == 0):
            self.message = "Host does have " + str(len(executable_pipelines)) + " user executable pipeline(s), but none returned at least one boutiques descriptor"
            return False

        self.message = "Host has " + str(len(self.raw_descriptors)) + " boutiques descriptor(s)."
        self.validated = True
        return True
  
    def _urlize(self, url, path):
        
        base = self.url
        if ((self.url[-1] != '/')):
            base += '/'
        return base + path
    
    def is_valid(self):
        return self.validated
    
    def is_empty(self):
        return (self.is_carmin_online and (len(self.raw_descriptors) == 0))
    
    def get_raw_descriptors(self):
        return self.raw_descriptors
        
    def get_message(self):
        return self.message
        
    def submit(self):
        #print("submission attempt")
        if (not self.validate()):
            return False
                 
        # Add CARMIN entry
        #print("reached SUBMIT stage")
        self.db_carmin_platform = CarminPlatform()
        self.db_carmin_platform.user = self.user
        self.db_carmin_platform.root_url = self.url
        self.db_carmin_platform.api_key = self.apikey
        self.db_carmin_platform.name = self.name
        self.db_carmin_platform.is_public = self.is_public
        self.db_carmin_platform.save()
        
        carmin_platform = CarminPlatformEntry(self.db_carmin_platform)
        carmin_platform.populate(self)
            
        return True

    # This is meant to be used for testing purposes
    def get_db(self):
        return self.db_carmin_platform


class CarminPlatformEntry:

    def __init__(self, db_car):
        self.db_car = db_car
        self.erroneous = False
        self.error_message = ""
    

    
    def populate(self, carmin_data):
        
        # Create descriptor entries for all the descriptors found associated.
        raw_descriptors = carmin_data.get_raw_descriptors()

        user = self.db_car.user
        is_public = self.db_car.is_public

        # For each of those descriptors, validate and create a db entry
        # In the cases where one of the descriptor is invalid, create a database entry anyway.
        for raw_descriptor in raw_descriptors:
            self._generate_descriptor(raw_descriptor)

            

    def _generate_descriptor(self, descriptor_raw):
        
        user = self.db_car.user
        #user = User.objects.get(pk=self.db_car.user_id)
        is_public = self.db_car.is_public
        data = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateLocalRawContainer(descriptor_raw),
                                                  user=user, 
                                                  carmin_platform=self.db_car, 
                                                  is_public=is_public)
        data.submit(allow_invalid=True)
        return data
    
    def update(self, scheduled=False):
        
        self.unset_erroneous()                            
        user = self.db_car.user
        is_public = self.db_car.is_public
        
        data_getter = CarminPlatformCandidate(self.db_car.root_url, self.db_car.api_key)
        valid = data_getter.validate()
        if (not valid):

            self.set_erroneous(data_getter.get_message())

            # Check if the platform is not valid due to the fact that its absent of any boutiques descriptors
            if (not data_getter.is_empty()):
                # Otherwise its a platform error and we should propagate it to all the descriptor entries pertaining to this platform
                self.propagate_error()

            else:
                
                # Fetch all the descriptors and delete them
                for db_desc in self.get_descriptors().all():
                    desc = desc_utils.DescriptorEntry(db_desc)
                    desc.delete()
            return
        # No problems with the carmin platform, and we know there is at least one boutiques descriptor
        fetched_descriptors = data_getter.get_raw_descriptors()
        fetched_md5 = {}
        for fetched_descriptor in fetched_descriptors:
            md5 = calculate_MD5(fetched_descriptor)
            fetched_md5[md5] = fetched_descriptor
            
        current_md5 = {}
        for db_descriptor in self.get_descriptors():
            current_md5[db_descriptor.md5] = desc_utils.DescriptorEntry(db_descriptor)
        

        # Add the new descriptors to database
        # If the update is performed in the context of testing scheduling, show those newly created descriptors as being scheduled for testing.
        #print(current_md5)
        for fetched in fetched_md5:
            if (not current_md5.get(fetched)):
                data = self._generate_descriptor(fetched_md5[fetched])
                if (scheduled and data.is_valid()):
                    desc = desc_utils.DescriptorEntry(data.get_db())
                    desc.set_scheduled()
            
                
                
        
        # Remove descriptors that are not part of the fetched set
        # Additionaly, for descriptors that do belong, show them as being scheduled for testing.
        for current in current_md5:
            if (not fetched_md5.get(current)):
                current_md5[current].delete()
            else:
                current_md5[current].update(force_static_validation=True, scheduled=scheduled)
                #current_md5[current].set_inprogress()
        
   
    def propagate_error(self):

        for db_desc in self.get_descriptors():
            desc = desc_utils.DescriptorEntry(db_desc)
            desc.set_erroneous(self.error_message)
    
    
    def get_descriptors(self):

        user = self.db_car.user_id        

        return Descriptor.objects.filter(carmin_platform=self.db_car, user_id=user).all()
        
    def set_erroneous(self, error_message):
        
        self.erroneous = True
        self.error_message = error_message
        self.db_car.error_message = error_message
        self.db_car.save()        
        

    def unset_erroneous(self):
        
        self.erroneous = False
        self.error_message = ""       
        self.db_car.error_message = ""
        self.db_car.save()


    def get_descriptors_entries(self):
        
        descriptor_entries = []
        
        for db_desc in self.get_descriptors():
            descriptor_entries.append(desc_utils.DescriptorEntry(db_desc))
            
        return descriptor_entries


    def delete(self):
        
        # The descriptors must be deleted first.
        for desc in self.get_descriptors_entries():
            desc.delete()

        # Delete the carmin platform database entry
        self.db_car.delete()
