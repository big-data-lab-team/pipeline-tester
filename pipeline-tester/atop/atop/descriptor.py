from atop.common import get_JSON, get_bosh_cmdline, create_temporary_file, calculate_MD5, HTTPGetter
from atop.models import Descriptor, DescriptorTest, DescriptorTestAssertion
from atop.models import EXECUTION_STATUS_UNCHECKED, EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_FAILURE, EXECUTION_STATUS_ERROR, EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_RUNNING
from atop.models import ASSERTION_EXITCODE, ASSERTION_OUTPUT_FILE_EXISTS, ASSERTION_OUTPUT_FILE_MATCHES_MD5
from atop.models import TEST_STATUS_UNCHECKED, TEST_STATUS_SUCCESS, TEST_STATUS_FAILURE

from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError, ContentTooShortError
from django.core.files.base import ContentFile
from contextlib import redirect_stdout
from io import StringIO

import sys
import json
import boutiques as bosh
import datetime
import uuid


DATA_SELECTOR_FILE = 0
DATA_SELECTOR_URL = 1


class DescriptorDataCandidateContainer:
    
    def is_medium_erroneous(self):
        return False




class DescriptorDataCandidateURLContainer(DescriptorDataCandidateContainer):

    def __init__(self, url):
        self.url = url
        http_getter = HTTPGetter(url)
        if (http_getter.is_erroneous()):
            self.erroneous = True
            self.error = http_getter.get_error()
        else:
            self.erroneous = False
            self.error = ""
            self.data = http_getter.get_data()            
        
    def get_url(self):
        return self.url

    def is_medium_erroneous(self):
        return self.erroneous

    def get_error(self):
        return self.error

    def get_data(self):
        return self.data
    
class DescriptorDataCandidateLocalFileContainer(DescriptorDataCandidateContainer):
    
    def __init__(self, file):
        self.file = file
        
    def get_data(self):
        data = self.file.read()
        self.file.seek(0)
        return data
        
    def get_file(self):
        return self.file


class DescriptorDataCandidateLocalRawContainer(DescriptorDataCandidateContainer):

    def __init__(self, raw_data):
        self.raw_data = raw_data
        
    def get_data(self):
        return self.raw_data


class DescriptorDataCandidate:
    
    def __init__(self, container, carmin_platform=None, is_public=False, automatic_updating=False, user=None):

        self.user = user
        self.is_public = is_public
        self.automatic_updating = automatic_updating
    
        self.container = container
        self.carmin_platform = carmin_platform
        self.erroneous = False
        self.validated = False
        self.message = ""
        self.db_desc = None
    
      
    def validate(self):
        
        # This is here in case we have a URL container
        if (self.container.is_medium_erroneous()):
            self.validated = False
            self.message = self.container.get_error()
            return False
        else:
            desc_content = self.container.get_data()

                        
        # Call bosh validate on the data
        file = create_temporary_file(desc_content)
        #backedup = sys.tracebacklimit
        #sys.tracebacklimit = None
        
        try:
            bosh.validate(file.name)
            self.validated = True
        except Exception as exc:
            self.validated = False
            error = str(exc).replace('\n', '<br>')
            
        #sys.tracebacklimit = backedup
        if (self.validated == True):
            desc = json.loads(file.read())
            if (desc.get("tests") == None):
                n_tests = 0
            else:

                n_tests = len(desc["tests"])
            
            self.message = "Associated descriptor is valid.<br><b>" + str(n_tests) + "</b> tests found defined inside descriptor."
        else:
            self.message = "<b> Validation failure.<br>Boutiques returned the following error(s):</b><br>" + error
        
        file.close()
        return self.validated
    
    
    
    def submit(self, allow_invalid=False):
    
        self.db_desc = Descriptor()
        
        self.db_desc.is_public = self.is_public
        self.db_desc.user_id = self.user
        
        file = create_temporary_file(self.container.get_data())
        
        if (isinstance(self.container, DescriptorDataCandidateURLContainer)):
            self.db_desc.data_url = self.container.get_url()
            self.db_desc.automatic_updating = self.automatic_updating
        else:
            self.db_desc.data_url = ""
        
        
        filename = uuid.uuid4().hex
        self.db_desc.data_file.save(filename, ContentFile(self.container.get_data()))

        self.db_desc.md5 = calculate_MD5(self.container.get_data())
        
        if (self.carmin_platform):
            self.db_desc.carmin_platform = self.carmin_platform
                
        # Validation
        try:
            bosh.validate(file.name)
            self.validated = True
        except Exception as exc:
            self.validated = False
            file.close()
            if (not allow_invalid):
            # An invalid descriptor is allowed on submission only if the 'allow_invalid' argument is set
                return False
            # Add error message to desc
            self.db_desc.execution_status = EXECUTION_STATUS_ERROR
            self.db_desc.error_message = str(exc).replace('\n', '<br>')
            self.db_desc.last_updated = datetime.date.today()
            self.db_desc.save()
            return True
        
        self.db_desc.execution_status = EXECUTION_STATUS_UNCHECKED

        desc_JSON = json.loads(file.read())
        
        self.db_desc.tool_name = desc_JSON["name"]
        self.db_desc.version = desc_JSON["tool-version"]
            
        self.db_desc.last_updated = datetime.date.today()
        
        self.db_desc.save()
        
        # Generate all the test profiles.
        desc_entry = DescriptorEntry(self.db_desc)
        desc_entry.generate_tests()

        return True

    def get(self):
        return self.container.get_data()
        
    def get_name(self):
        desc_JSON = json.loads(self.container.get_data())
        return desc_JSON["name"]

    def get_version(self):
        desc_JSON = json.loads(self.container.get_data())
        return desc_JSON["tool-version"]        

    def get_MD5(self):
        if (self.container.is_medium_erroneous()):
            return "0"
        return calculate_MD5(self.container.get_data())
        
    def get_message(self):
        return self.message
        
    def is_valid(self):
        return self.validated

    def get_db(self):
        return self.db_desc


class DescriptorEntry:
    

    def __init__(self, db_desc):

        self.db_desc = db_desc
        if (db_desc.data_url != ""):
            self.medium_type = DATA_SELECTOR_URL
        else:
            self.medium_type = DATA_SELECTOR_FILE
        
        if (db_desc.carmin_platform != None):
            self.has_carmin_platform = True
        else:
            self.has_carmin_platform = False


    def update(self, scheduled=False, force_static_validation=False):
        
        if (self.db_desc.error_message != ""):
            erroneous_db = True
        else:
            erroneous_db = False

        self.db_desc.last_updated = datetime.date.today()

        # Reset any possible error messages
        self.db_desc.error_message = ""

        if (self.medium_type == DATA_SELECTOR_URL):
            
            if (self.db_desc.automatic_updating == True):
                container_url = DescriptorDataCandidateURLContainer(self.db_desc.data_url)
                if (container_url.is_medium_erroneous()):
                    # Erroneous URL
                    self.db_desc.execution_status = EXECUTION_STATUS_ERROR
                    self.db_desc.error_message = container_url.get_error()
                    self.db_desc.save()
                    # Tests should be deleted ?
                    return False    
                else:
                    # We were able to successfully fetch the data from the URL.
                    data = DescriptorDataCandidate(container_url)
                    md5 = data.get_MD5()
                    if (md5 != self.db_desc.md5 or erroneous_db):
                        # New data
                        
                        with open(self.db_desc.data_file.file.name, 'wb') as fhandle:
                            fhandle.write(data.get())
                        self.db_desc.save()

                        data.validate()
                        if (not data.is_valid()):
                            # Erroneous data
                            # Set the error
                            self.db_desc.execution_status = EXECUTION_STATUS_ERROR
                            self.db_desc.error_message = data.get_message()
                            
                            # Update tool properties.
                            self.db_desc.tool_name = ""
                            self.db_desc.version = ""
                            self.db_desc.md5 = md5

                            # Remove test entries if any were there previously 
                            self.delete_tests()
                            self.db_desc.save()

                            return False
                        else:
                            # URL data is valid, but with different data
                            self.db_desc.md5 = md5

                            self.delete_tests()
                            self.generate_tests()

                            self.db_desc.tool_name = data.get_name()
                            self.db_desc.version = data.get_version()                            

                            if (scheduled):
                                self.db_desc.execution_status = EXECUTION_STATUS_SCHEDULED
                            else:
                                self.db_desc.execution_status = EXECUTION_STATUS_UNCHECKED

                            self.db_desc.save()
                            return True
                    else:
                        # The data has not changed, nor has an error happened during the last fetching
                        # In this case, we have nothing to do but to reset the execution status of the tests
                        if (scheduled):
                            self.db_desc.execution_status = EXECUTION_STATUS_SCHEDULED
                        else:
                            self.db_desc.execution_status = EXECUTION_STATUS_UNCHECKED
                        self.db_desc.save()
                        self.reset_tests()                                  
                        return True  

            else:
                # The descriptor is URL based but automatic updating was set to off
                # This makes the descriptor just like a descriptor that was uploaded locally.
                # This means that the descriptor data or error status will never change.
                if (scheduled):
                    self.db_desc.execution_status = EXECUTION_STATUS_SCHEDULED
                else:
                    self.db_desc.execution_status = EXECUTION_STATUS_UNCHECKED
                self.db_desc.save()
                self.reset_tests()

                return True

        if (self.medium_type == DATA_SELECTOR_FILE):
            
            if (force_static_validation):
                # If force_static_validation has been passed, that means that we are facing a descriptor that was acquired through a CARMIN platform.
                
                # A descriptor fetched from a CARMIN servers registers its data through a file.
                # As the descriptor may be subjected by errors from the CARMIN server that erase previously set execution status and error messages,
                # it is necessary to validate the descriptor another time to restore the possible properties that were set when the CARMIN server was functional.
                
                if (erroneous_db and self.db_desc.tool_name != ""):
                    
                    # A CARMIN platform error was previously set.
                    # We have to validate the data to know the previous original status of the descriptor           
                    # We dont have to regenerate test entries.
                    content = self.db_desc.data_file.read()
                    self.db_desc.data_file.seek(0)
                    data = DescriptorDataCandidate(DescriptorDataCandidateLocalRawContainer(content))
                    data.validate()
                    if (data.is_valid()):
                        # The descriptor is fine.
                        if (scheduled):
                            self.db_desc.execution_status = EXECUTION_STATUS_SCHEDULED
                        else:
                            self.db_desc.execution_status = EXECUTION_STATUS_UNCHECKED
                        self.db_desc.save()
                        # Again, no need to regenerate test cases, they should already been there.
                        # We only have to reset the tests.
                        self.reset_tests()

                        return True
                elif (not erroneous_db):
                    
                    # Otherwise, lets just check if the descriptor is valid and set execution status to scheduled if scheduled is set.
                    if (scheduled):
                        self.db_desc.execution_status = EXECUTION_STATUS_SCHEDULED
                    else:
                        self.db_desc.execution_status = EXECUTION_STATUS_UNCHECKED
                    self.db_desc.save()                    
                    self.reset_tests()

                    return True
            else:
                # This is a file that was uploaded through a file upload
                # We do not have any actions to performs, other than cleaning up tests and setting the execution status.
                if (scheduled):
                    self.db_desc.execution_status = EXECUTION_STATUS_SCHEDULED
                else:
                    self.db_desc.execution_status = EXECUTION_STATUS_UNCHECKED
                self.db_desc.save()                    
                self.reset_tests()

                return True
                        
                        
                    
    def reset_tests(self):
        get_tests_query = DescriptorTest.objects.filter(descriptor=self.db_desc)
        db_tests = get_tests_query.all()
        
        # We check if tests exist.
        if (len(db_tests) == 0):
            return        

        # We iterate on each of those tests to reset their execution status.
        for db_test in db_tests:        
            db_test.execution_status = TEST_STATUS_UNCHECKED
            db_test.save()




        
    
    def generate_tests(self):


        # Get descriptor as JSON

        desc_JSON = json.loads(self.db_desc.data_file.read())
        
        # Create new test entries
        test_list = [];
        for test_JSON in desc_JSON['tests']:
            test = DescriptorTest()
            
            test.test_name = test_JSON['name']
            test.descriptor = self.db_desc
            test_list.append(test_JSON['name'])
                    
            # Evaluate the descriptor's command line, using the invocation specified by the test.
            
            # To perform this evaluation, we need to extract the invocation from the test and put it into a temporary file
            invocation_tmp_file = create_temporary_file(json.dumps(test_JSON['invocation']).encode())
            
            # If the invocation is erroneous, we simply mention it in in the entry itself
            # A wrongfull invocation should however not put a halt to the entire evaluation of a descriptor.
            erroneous_invocation = False
            try:
                bosh.invocation(self.db_desc.data_file.file.name, '-i', invocation_tmp_file.name)
            except:
                erroneous_invocation = True
            
            # Rewind
            invocation_tmp_file.seek(0)
            
            if (erroneous_invocation):
                test.evaluated_invocation = "Error: invalid invocation"
                
            else:
                
                #test.evaluated_invocation = bosh.evaluate(self.db_desc.data_file.file.name, invocation_tmp_file.name, "command-line/")
                test.evaluated_invocation = get_bosh_cmdline(self.db_desc.data_file.file.name, invocation_tmp_file.name)      
        
            test.save()        
            invocation_tmp_file.close()

            # Create assertion entries.
            if test_JSON['assertions'].get('exit-code') != None:
                
                # Create assertion entry with exit-code
                assertion = DescriptorTestAssertion()
                assertion.test = test
                assertion.operand1 = test_JSON['assertions']['exit-code']
                assertion.type = ASSERTION_EXITCODE
                assertion.save()
                
            output_files = None
            if (erroneous_invocation == False):
                output_files = bosh.evaluate(self.db_desc.data_file.file.name, invocation_tmp_file.name, "output-files/")
            
            if test_JSON['assertions'].get('output-files') != None:
                
                for ouput_assertion_JSON in test_JSON['assertions']['output-files']:
                    
                    assertion = DescriptorTestAssertion()
                    assertion.test = test
                    
                    # Id processing
                    id = ouput_assertion_JSON['id']
                    if erroneous_invocation == True:
                        # Skip the evaluation of this entry because the associated invocation is invalid.
                        assertion.operand1 = "Cannot evaluate: invocation invalid"
                    else:
                        assertion.operand1 = output_files[id]
                    
                    # MD5 reference processing
                    if ouput_assertion_JSON.get('md5-reference') != None:
                        assertion.operand2 = ouput_assertion_JSON['md5-reference']
                        assertion.type = ASSERTION_OUTPUT_FILE_MATCHES_MD5                
                    else:
                        assertion.type = ASSERTION_OUTPUT_FILE_EXISTS
                    
                    assertion.save()
            
            # We are done filling up the test entry.

        self.db_desc.data_file.seek(0)

    def delete_tests(self):
        
        # Clear up all the content related to the entry (except the descriptor entry itself)
        # First, we start we collect the tests related to the desc entry.
        get_tests_query = DescriptorTest.objects.filter(descriptor=self.db_desc)
        tests = get_tests_query.all()
        
        # We check if tests exist.
        if (len(tests) == 0):
            return        

        # We iterate on each of those tests to delete the associated assertion entries.
        for test in tests:
            assertions = DescriptorTestAssertion.objects.filter(test=test).delete()
        
        # Now we can delete the test entries
        get_tests_query.delete() 

        
    
    # Returns list of tuple [(success status, associated message), ..]
    def _execute_test(self):

        results = []
        desc_JSON = json.loads(self.db_desc.data_file.read())    

        # This is a work-around: 
        # To individually test each of the descriptors,
        # the source descriptor will be broken into x copies of the descriptor, where x is the amount of tests defined.
        # Each of those clones will be only include each of the tests in the source descriptor.
        # To perform a test on a single defined test-case, we only need to supply the descriptor which includes it.
        # - The output of bosh should indicate the successfullness of the test. 
        # - The stdout procuced by the command will represent the console logs we need to capture.
        
        tests = desc_JSON["tests"]

        # We remove the test entries in the JSON descriptor.
        desc_JSON["tests"] = [] 

        for test in tests:
            # We remove all the test entries in the JSON descriptor and only the current test entry
            desc_JSON["tests"] = [test]
            temporary_desc_file = create_temporary_file(json.dumps(desc_JSON).encode())
            
            # Preparation of the bosh test call
            # Capture of the stdout
            old_stdout = sys.stdout
            sys.stdout = mystdout = StringIO()

            if (bosh.bosh(["test", temporary_desc_file.name]) == 0):
                # Bosh test (pytest) returned 0, this means that the test was successful.
                status = TEST_STATUS_SUCCESS
            else:
                # Otherwise, any other exit-code indicates failure.
                status = TEST_STATUS_FAILURE
            
            temporary_desc_file.close()
            sys.stdout = old_stdout

            console = mystdout.getvalue().replace('\\n', '<br>')

            results.append((status, console))

        return results
    
    def delete(self):

        # Remove the tests before
        self.delete_tests()
        # Remove the entry itself
        self.db_desc.delete()


    
    # TODO: Prevent the desc from being deleted.
    def test(self):
        
        # A descriptor is supposed to be updated before being tested.
        # We skip testing in the case where the update led to the descriptor being detected as erroneous.
        if (self.db_desc.execution_status == EXECUTION_STATUS_ERROR):
            return    

        self.db_desc.execution_status = EXECUTION_STATUS_RUNNING        
        self.db_desc.save()
        
        # Run the tests on the descirptor
        results = self._execute_test()

        # Get the list of test entries.
        test_entries = DescriptorTest.objects.filter(descriptor_id=self.db_desc).all()
        
        # Update test entries
        i = 0
        no_failure = True
        for test in results:
            test_entry = test_entries[i]
            if (test[0] == TEST_STATUS_SUCCESS):
                test_entry.execution_status = TEST_STATUS_SUCCESS
            else:
                test_entry.execution_status = TEST_STATUS_FAILURE
                no_failure = False
            test_entry.code = test[1]
            test_entry.save()
            i += 1

        # Indicate if the descriptor has failing tests, or if all of them have been successfully executed
        if no_failure:    
            self.db_desc.execution_status = EXECUTION_STATUS_SUCCESS
        else:
            self.db_desc.execution_status = EXECUTION_STATUS_FAILURE

        self.db_desc.last_updated = datetime.date.today()
        self.db_desc.save()
        
        # We are done
        return

    def set_scheduled(self):
        self.db_desc.execution_status = EXECUTION_STATUS_SCHEDULED
        self.db_desc.save()

    def set_erroneous(self, error_message):
        self.db_desc.execution_status = EXECUTION_STATUS_ERROR
        self.db_desc.error_message = error_message
        self.db_desc.save()
