from atop.common import get_JSON, get_bosh_cmdline, create_temporary_file, calculate_MD5
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


class DescriptorDataCandidateURLContainer:

    def __init__(self, url):
        self.url = url
        self.data_buffer = None
        
    def get_url(self):
        return self.url
    
    # Buffer data respone when the URL is valid
    # The second call to this method will deliver what has been buffered
    def get_data(self):
        
        if (self.data_buffer):
            return self.data_buffer
        
        try:
            req = Request(self.url)
            data = urlopen(req).read()
            self.data_buffer = data
            return data
        except HTTPError as e:
            raise Exception("[" + str(e.code) + "] " + e.reason + "(" + self.url + ")")
        except URLError as e:
            raise Exception("URL error (" + e.reason + ") (" + self.url + ")")
        except ContentTooShortError:
            raise Exception("Content too short (" + self.url + ")")
        except ValueError:
            raise Exception("Invalid URL (" + self.url + ")")
    
class DescriptorDataCandidateLocalFileContainer:
    
    def __init__(self, file):
        self.file = file
        
    def get_data(self):
        data = self.file.read()
        self.file.seek(0)
        return data
        
    def get_file(self):
        return self.file


class DescriptorDataCandidateLocalRawContainer:

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
        
        # The try - except is only set in case we have a URL container
        try:
            desc_content = self.container.get_data()
        except Exception as e:
            self.validated = False
            self.message = str(e)
            return False
                        
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
        self.db_desc.execution_status = EXECUTION_STATUS_UNCHECKED
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
        
                
        # Validation
        try:
            bosh.validate(file.name)
        except Exception as exc:
            file.close()
            if (not allow_invalid):
            # An invalid descriptor is allowed on submission only if the 'allow_invalid' argument is set
                return False
            # Add error message to desc
            self.db_desc.error = str(exc).replace('\n', '<br>')
            self.db_desc.last_updated = datetime.date.today()
            self.db_desc.save()
            return True
        
        desc_JSON = json.loads(file.read())
        
        self.db_desc.tool_name = desc_JSON["name"]
        self.db_desc.version = desc_JSON["tool-version"]
            
        self.db_desc.last_updated = datetime.date.today()
        
        if (self.carmin_platform):
            self.db_desc.carmin_platform = self.carmin_platform
        
        self.db_desc.save()
        
        #create_test_entries(file.name, desc)
        
        desc_entry = DescriptorEntry(self.db_desc)
        desc_entry.generate_tests()

        return True

    def get(self):
        return self.container.get_data()
        
        
    def get_MD5(self):
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
    
    
    # Create the test entries of the descriptor
    def update(self, scheduled=False):
        print("update triggered")

        # Reset possibly previously set error message.
        self.db_desc.error_message = ""

        if (self.medium_type != DATA_SELECTOR_URL):

            if (scheduled):
                self.db_desc.execution_status = EXECUTION_STATUS_SCHEDULED
                self.db_desc.save()

            self.delete_tests()
            self.generate_tests()

            return True
        print("DATA TYPE")
        print(self.db_desc.data_url == None)

        # Get the data
        new_data = DescriptorDataCandidate(DescriptorDataCandidateURLContainer(self.db_desc.data_url))
        
        # Check if MD5 matches the MD5 of current descriptor.
        new_data.get_MD5()
        
        new_data.validate()
        if (not new_data.is_valid()):
        
            self.db_desc.error_message = new_data.get_message()
            self.db_desc.execution_status = EXECUTION_STATUS_ERROR
            self.db_desc.tool_name = ""
            # Dummy MD5            
            self.db_desc.md5 = "0"
            self.delete_tests()
            self.db_desc.save()
            
            return False
        
        new_md5 = new_data.get_MD5()

        if (scheduled):
            self.db_desc.execution_status = EXECUTION_STATUS_SCHEDULED
        
        self.db_desc.save()

        # The new and current descriptors are the same
        if (new_md5 == self.db_desc.md5):
            return True
        
        # This is a new descriptor
        JSON_data = get_JSON(new_data.get())
        
        # See if the name and version of the descriptor have changed
        if (self.db_desc.tool_name != JSON_data["name"]):
            self.db_desc.tool_name = JSON_data["name"]
            self.db_desc.save()
        
        # Replace descriptor file
        with open(self.db_desc.data_file.file.name, 'w') as fhandle:
            fhandle.write(new_data.get())
       
        # Delete old test entries
        self.delete_tests()
        
        # Generate new ones
        self.generate_tests()
        
        return True        
        
    
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

    def delete_tests(self):
        
        # Clear up all the content related to the entry (except the descriptor entry itself)
        # First, we start we collect the tests related to the desc entry.
        get_tests_query = DescriptorTest.objects.filter(descriptor=self.db_desc)
        tests = get_tests_query.all()
        
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

    def set_inprogress():
        self.db_desc.execution_status = EXECUTION_STATUS_IN_PROGRESS
        self.db_desc.save()
