# atop/views.py
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.views import generic
from django.shortcuts import render
from django_tables2 import RequestConfig
from .models import Descriptor, EXECUTION_STATUS_UNCHECKED, EXECUTION_STATUS_ERROR, EXECUTION_STATUS_FAILURE, EXECUTION_STATUS_SUCCESS, DescriptorTest, DescriptorTestAssertion
from .tables import DescriptorTable, DescriptorTestTable
from .forms import AddDescriptorForm
import datetime
from django.http import HttpResponseRedirect, JsonResponse
import urllib
import io
from contextlib import redirect_stdout
from .models import ASSERTION_EXITCODE, ASSERTION_OUTPUT_FILE_EXISTS, ASSERTION_OUTPUT_FILE_MATCHES_MD5
from .models import TEST_STATUS_UNCHECKED, TEST_STATUS_SUCCESS, TEST_STATUS_FAILURE
from django.http import HttpResponse, HttpResponseBadRequest

from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError, ContentTooShortError

import tempfile
from boutiques.localExec import LocalExecutor
import boutiques as bosh
import sys
import json

from io import StringIO
import hashlib

from django.shortcuts import redirect

class SignUp(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'signup.html'


def add_constant_dict(source_dict):
    source_dict['EXECUTION_STATUS_UNCHECKED'] = EXECUTION_STATUS_UNCHECKED
    source_dict['EXECUTION_STATUS_ERROR'] = EXECUTION_STATUS_ERROR
    source_dict['EXECUTION_STATUS_FAILURE'] = EXECUTION_STATUS_FAILURE
    source_dict['EXECUTION_STATUS_SUCCESS'] = EXECUTION_STATUS_SUCCESS

    source_dict['TEST_STATUS_UNCHECKED'] = TEST_STATUS_UNCHECKED
    source_dict['TEST_STATUS_SUCCESS'] = TEST_STATUS_SUCCESS
    source_dict['TEST_STATUS_FAILURE'] = TEST_STATUS_FAILURE

    source_dict['ASSERTION_EXITCODE'] = ASSERTION_EXITCODE
    source_dict['ASSERTION_OUTPUT_FILE_EXISTS'] = ASSERTION_OUTPUT_FILE_EXISTS
    source_dict['ASSERTION_OUTPUT_FILE_MATCHES_MD5'] = ASSERTION_OUTPUT_FILE_MATCHES_MD5
    

    
def home(request):

    if request.method == "GET":
        # We just have to render the page.
        form = AddDescriptorForm()

        descs = Descriptor.objects.all()
        
        desc_table = DescriptorTable(descs)
        RequestConfig(request).configure(desc_table)

        test_tables = []
        for desc in desc_table.page.object_list.data:
            
            #desc_tests = desc.descriptortest_set.all()
            
            desc.data = desc.descriptortest_set.all()
            for test in desc.data:
                test.data = test.descriptortestassertion_set.all()
                for assertion in test.data:
                    assertion.type = get_assertion_typestring(assertion.type)   
            
            #table = DescriptorTestTable(desc_tests)
            #test_tables[desc.id] = table

        dict = {'table': desc_table, 'test_tables': test_tables, 'form': form}
        add_constant_dict(dict)
        print(dict["ASSERTION_EXITCODE"])

        return render(request, 'home.html', dict)


    elif request.method == "POST":

        form = AddDescriptorForm(request.POST, request.FILES)

        # Perform validation on the form data
        if (not form.is_valid()):
            return render(request, '/')

	    # Perform a validation on the data
        type = int(form.cleaned_data["data_selector"])

        print("type is" + str(type))
        
        if type == DATA_SELECTOR_CARMIN:
            
            url = form.cleaned_data["data_carmin_platform_url"]
            apikey = form.cleaned_data["data_carmin_platform_apikey"]
            
            error, pipelines = carmin_get(url, apikey)
            if (error != None):
                return render(request, '/')
             
            #TODO: Ideally, we should just ensure the existance of at least one boutiques descriptor
            executable_pipelines = carmin_get_executable_pipelines(pipelines)
            if (len(executable_pipelines) == 0):
                return render(request, '/')
            
            # Add CARMIN entry
            carmin_platform = CarminPlatform()
            carmin_platform.root_url = url
            carmin_platform.apikey = apikey
            carmin_platform.save()
            
            # For each of the boutiques descriptor:
            for pipeline in executable_pipelines:
                create_desc_entry(type, 
                                          form.cleaned_data["is_public"], 
                                          None,
                                          None,
                                          pipeline,
                                          False,
                                          User.objects.get(pk=request.user.id),
                                          carmin_platform)

                          
            
        if type == DATA_SELECTOR_FILE:
            # Descriptor is inside POST file data
            create_desc_entry(type, 
                                      form.cleaned_data["is_public"], 
                                      form.cleaned_data["data_file"],
                                      None,
                                      None,
                                      False,
                                      User.objects.get(pk=request.user.id),
                                      None)
                     
        if type == DATA_SELECTOR_URL:
             
            # Descriptor is located on the web
            try:
                req = Request(url)
                data = urlopen(req).read()                
            except Exception as e:
                return render(request, '/')
            
            create_desc_entry(type,
                          form.cleaned_data["is_public"], 
                          None,
                          form.cleaned_data["data_url"],
                          data,
                          form.cleaned_data["automatic_updating"],
                          User.objects.get(pk=request.user.id),
                          None)

        print(form.errors)
                 
        return HttpResponseRedirect("/")


VALIDATION_SUCCESS = 0
VALIDATION_FAILURE = 1


# Returns (error, data)
def carmin_get(url, apikey):    
    try:
        req = Request(url)
        req.add_header('content-type', 'application/json')
        req.add_header('apikey', apikey)
        data = urlopen(req).read()
    except HTTPError as e:
        error = "[" + str(e.code) + "] " + e.reason
        return (error, None)
    except URLError as e:
        error = "URL error (" + e.reason + ")"
        return (error, None)
    except ContentTooShortError:
        error = "Content too short"
        return (error, None)
    except ValueError:
        error = "Invalid URL"
        return (error, None)
    
    try:
        data_JSON = json.loads(data)
    except:
        error = "Content is not a JSON string (" + url + ")"
        return (error, None)
        
    # If a code is specified in the JSON string, then this means that we got to reach the CARMIN server
    # But we most likely did not end up with the content we expected.
    if  (isinstance(data_JSON, dict) and data_JSON.get('code') != None):
        error = "[" + data_JSON.get('code') + "]" + data_JSON.get('message')
        return (error, None)
        
    # The content is a valid JSON string that do not refer to an error.
    return (None, data_JSON)
    
    
def carmin_get_executable_pipelines(pipelines):
    
    executable_pipelines = []
    
    for pipeline in pipelines:
        if pipeline['canExecute']:
            executable_pipelines.append(pipeline)
            
    return executable_pipelines
    

def fetch_descriptor(url):

    response = {}        

    if url == None:
        # Somehow the URL is missing.
        # Return an error as a consequence
        response['code'] =  VALIDATION_FAILURE
        response['message'] = "Missing URL"
        return (response, None)
    
    # Now we check if the URL is valid
    try:
        req = Request(url)
        data = urlopen(req).read()
        
    except (URLError, HTTPError) as e:
        response['code'] = VALIDATION_FAILURE
        response['message'] = "Cannot fetch (" + str(e.reason) + ")"        
        return (response, None)
        
    except ContentTooShortError:
        response['code'] = VALIDATION_FAILURE
        response['message'] =  "Content too short"
        return (response, None)
        
    except ValueError:
        response['code'] = VALIDATION_FAILURE
        response['message'] =  "Invalid URL"
        return (response, None)    
    
    return (None, data)


DATA_SELECTOR_FILE = 0
DATA_SELECTOR_URL = 1
DATA_SELECTOR_CARMIN = 2

    
# The data argument refer to either: an URL, the content of a descriptor OR a tuple with the first element being a CARMIN url, and the second element being an api key.
def validate_descriptor(type, data):

    response = {}
    
    if type == DATA_SELECTOR_FILE:    
        desc_content = data
    
    if type == DATA_SELECTOR_URL:
        error, desc_content = fetch_descriptor(data)
        if (error):
            return error
    
    if type == DATA_SELECTOR_CARMIN:
        url = data[0]
        apikey = data[1]
        
        # First, fetch the pipelines
        error, pipelines = carmin_get(url, apikey)
        
        # Check if any errors were triggered
        if (error != None):
            response['code'] = VALIDATION_FAILURE
            response['message'] = error
            return response
        
        # Then, parse the pipelines to see if they have pipelines the user (we) can execute.
        executable_pipelines = carmin_get_executable_pipelines(pipelines)
        
        #TODO: Process those pipelines to see if they have boutiques descriptors
        ep_count = len(executable_pipelines)
        
        if (ep_count == 0):
            response['code'] = VALIDATION_FAILURE
            response['message'] = "CARMIN server do not have any boutiques descriptors to execute"
            return response
        
        response['code'] = VALIDATION_SUCCESS
        response['message'] = "CARMIN server reached. (" + str(ep_count) + ") executable pipeline found."
        return response
       
        
    # Call bosh validate on the data
    file = create_temporay_file(desc_content)
    #backedup = sys.tracebacklimit
    #sys.tracebacklimit = None
    
    try:
        bosh.validate(file.name)
        validated = True
    except Exception as exc:
        validated = False
        error = str(exc).replace('\n', '<br>')

        
    #sys.tracebacklimit = backedup
    
    if (validated == True):
        desc = json.loads(file.read())
        if (desc.get("tests") == None):
            n_tests = 0
        else:

            n_tests = len(desc["tests"])
        
        response['code'] = VALIDATION_SUCCESS
        response['message'] = "Associated descriptor is valid.<br><b>" + str(n_tests) + "</b> tests found defined inside descriptor."
    else:
        response['code'] = VALIDATION_FAILURE
        response['message'] = "<b> Validation failure.<br>Boutiques returned the following error(s):</b><br>" + error
    
    file.close()
    return response



def validate_descriptor_submit(request):

    if (request.method != "POST") and (request.method != "GET"):
        return HttpResponseBadRequest()    

    if request.method == "GET":
        # A GET may refer to two different things: An URL poiting toward a descriptor, or informations about a CARMIN platoform
        # We have to review the 'type' key to make the differentiation
        if (request.GET.get("type") == str(DATA_SELECTOR_URL)):
            return JsonResponse(validate_descriptor(DATA_SELECTOR_URL, request.GET.get("url")))
        if (request.GET.get("type") == str(DATA_SELECTOR_CARMIN)):
            data = [request.GET.get("url"), request.GET.get("apikey")]
            return JsonResponse(validate_descriptor(DATA_SELECTOR_CARMIN, data))
        else:
            return HttpResponseBadRequest()
           
    if (request.method == "POST"):
        # If the request method is a POST, then we know for sure that we are dealing with a file upload
        return JsonResponse(validate_descriptor(DATA_SELECTOR_FILE, request.body))

        
def create_desc_entry(type, is_public, data_file, data_url, data_raw, automated_testing, user_id, carmin_platform):

    desc = Descriptor()

    desc.is_public = is_public
    desc.execution_status = EXECUTION_STATUS_UNCHECKED
    desc.user_id = user_id
    
    if type == DATA_SELECTOR_FILE:
        file = create_temporay_file(data_file.file.read())
        data_file.file.seek(0)
        desc.data_file = data_file
        desc.md5 = calculate_MD5(file.read())
        file.seek(0)
        
    if type == DATA_SELECTOR_URL:
        file = create_temporay_file(data_raw)
        desc.data_url = data_url
        desc.automated_testing = automated_testing
        desc.md5 = calculate_MD5(data_raw)
        #TODO: If automated_testing is set to false, then the descriptor data should be put into a file
        
    if type == DATA_SELECTOR_CARMIN:
        desc.carmin_platform = carmin_platform
        desc.md5 = calculate_MD5(data_raw)
        file = create_temporay_file(data_raw)
        #TODO: Again, the raw data should be put into a file (regardless of automated_testing)
        
    # Validation
    try:
        bosh.validate(file.name)
    except Exception as exc:
        file.close()
        if type != DATA_SELECTOR_CARMIN:
        # An invalid descriptor is allowed on submission only if the descriptor is part of a CARMIN platform
            return False
        # Add error message to desc
        desc.error = str(exc).replace('\n', '<br>')
        desc.last_updated = datetime.date.today()
        desc.save()
        return True
    
    desc_JSON = json.loads(file.read())
    
    desc.tool_name = desc_JSON["name"]
    desc.last_updated = datetime.date.today()
    
    desc.save()
    
    create_test_entries(file.name, desc)
    
    return True
    


    
def run_tests(request):

    user = User.objects.get(pk=request.user.id)
    
    # Fetch users's descriptors.
    descs = Descriptor.objects.all().filter(user_id=user)

    #TODO: Atomically indicate that the user's descriptors are currently being updated.

    # Run run_test function for each of those tests.
    for desc in descs:
        
        run_test(desc, user)
        
    return redirect('/')
    


def create_temporay_file(content):

    temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    temp_file.write(content)
    temp_file.seek(0)
    
    return temp_file

'''

    
def validate_descriptor(descriptor_filepath):
    
    # Attempt to validate descriptor
    # If validation fails, return tuple with first element indicaiting failure.
    try:
        bosh.validate([descriptor_filepath])
    except e:
        return (False, e.message)
    
    return (True, None)
'''

def create_descriptor_entry(descriptor_filepath, descriptor):
    
    # Get descriptor as JSON
    with open(descriptor_filepath, 'r') as fhandle:
        desc_JSON = json.loads(fhandle.read())

    descriptor.name = desc_JSON['name']
    

# Work-around
def get_bosh_cmdline(descriptor_filepath, invocation_filepath):
    
    executor = LocalExecutor(descriptor_filepath,
                             {"forcePathType"       : True,
                              "destroyTempScripts"  : True,
                              "changeUser"          : True,})
    executor.readInput(invocation_filepath)

    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    executor.printCmdLine()

    sys.stdout = old_stdout
    
    return mystdout.getvalue()[19:]

    
def create_test_entries(descriptor_filepath, descriptor):
    
    # Clean up all previous test entries (if any were there before)
    
    # Get descriptor as JSON
    with open(descriptor_filepath, 'r') as fhandle:
        desc_JSON = json.loads(fhandle.read())
    
    # Create new test entries
    test_list = [];
    for test_JSON in desc_JSON['tests']:
        test = DescriptorTest()
        
        test.test_name = test_JSON['name']
        test.descriptor = descriptor
        test_list.append(test_JSON['name'])
                
        # Evaluate the descriptor's command line, using the invocation specified by the test.
        
        # To perform this evaluation, we need to extract the invocation from the test and put it into a temporary file
        invocation_tmp_file = create_temporay_file(json.dumps(test_JSON['invocation']).encode())
        
        # If the invocation is erroneous, we simply mention it in in the entry itself
        # A wrongfull invocation should however not put a halt to the entire evaluation of a descriptor.
        erroneous_invocation = False
        try:
            bosh.invocation(descriptor_filepath, '-i', invocation_tmp_file.name)
        except:
            erroneous_invocation = True
        
        # Rewind
        invocation_tmp_file.seek(0)
        
        if (erroneous_invocation):
            test.evaluated_invocation = "Error: invalid invocation"
            
        else:
            
            #test.evaluated_invocation = bosh.evaluate(descriptor_filepath, invocation_tmp_file.name, "command-line/")
            test.evaluated_invocation = get_bosh_cmdline(descriptor_filepath, invocation_tmp_file.name)      
    
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
            output_files = bosh.evaluate(descriptor_filepath, invocation_tmp_file.name, "output-files/")
        
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


def get_assertion_typestring(type):

    if (type == ASSERTION_EXITCODE): return "Exit-code matches"
    if (type == ASSERTION_OUTPUT_FILE_EXISTS): return "Output file exists"
    if (type == ASSERTION_OUTPUT_FILE_MATCHES_MD5): return "Output file exists and matches MD5"


def get_JSON(filepath):
    with open(filepath, 'r') as fhandle:
        JSON = json.loads(fhandle.read())
    return JSON


# Returns list of tuple [(success status, associated message), ..]
def execute_test(desc_filepath):

    results = []
    desc_JSON = get_JSON(desc_filepath)    

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
        temporary_desc_file = create_temporay_file(json.dumps(desc_JSON).encode())
        
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

def calculate_MD5(content):
    return hashlib.md5(content).hexdigest()



def delete_test_entries(desc_row):
    # Clear up all the content related to the entry (except the descriptor entry itself)
    # First, we start we collect the tests related to the desc entry.
    get_tests_query = DescriptorTest.objects.filter(descriptor=desc_row)
    tests = get_tests_query.all()
    
    # We iterate on each of those tests to delete the associated assertion entries.
    for test in tests:
        assertions = DescriptorTestAssertion.objects.filter(test=test).delete()
    
    # Now we can delete the test entries
    get_tests_query.delete() 


def update_entry(desc_row, new_desc_filepath):
    
    #TODO: Indicate that the desc row is currently being updated.
    #      We want a smooth transition between the old desc entry and the new one
    
    # First part: deletion of the test entries
    delete_test_entries(desc_row)

    # Second part: creation of the test entries
    create_test_entries(desc_row, new_desc)

    # Third part: update name of desc entry
    with open(new_desc_filepath, 'r') as fhandle:
        desc_JSON = json.loads(fhandle.read())
    if (desc_row.tool_name != desc_JSON["name"]):
        desc_row.tool_name = desc_JSON["name"]
        desc_row.save()


def fetch_and_validate(url):
    
    validated, desc_content = fetch_descriptor(url)
    if (validated != None):
        return validated, None
    validated = validate_descriptor(False, desc_content)
    return validated, desc_content



def run_test(desc, user):
    fetch_descriptor
    if (desc.data_url != ""):
        # A url has been specified instead of an uploaded file.
        
        validated, desc_content = fetch_and_validate(desc.data_url)

        # Parse the response
        if (validated['code'] == VALIDATION_FAILURE):
            desc.error_message = validated['message']
            desc.execution_status = EXECUTION_STATUS_ERROR
            # Clear up descriptor data            
            # Dummy MD5            
            desc.md5 = "0"
            desc.tool_name = ""
            delete_test_entries(desc)
            desc.save()
            return

        # Calculate MD5 of the fetched content and compare it with current MD5
        if (calculate_MD5(desc_content) != desc.md5):
            # We have a brand new descriptor:
            # First part: replace descriptor file content
            
            with open(desc.data_file, 'w') as fhandle:
                fhandle.write(desc_content)

            # Second part: We need to update the entry
            update_entry(desc, data.data_file.name)
        
        # The fetched descriptor is the same as the current descriptor.
        # No further validation is necessary
    
    # Run the tests on the descirptor
    results = execute_test(desc.data_file.name)

    
    # Get the list of test entries.
    test_entries = DescriptorTest.objects.filter(descriptor_id=desc).all()
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
        desc.execution_status = EXECUTION_STATUS_SUCCESS
    else:
        desc.execution_status = EXECUTION_STATUS_FAILURE
    desc.save()
    
    # We are done
    return

