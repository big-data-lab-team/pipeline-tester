# atop/views.py
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate, logout
from django.contrib.auth import login as auth_login
from django.urls import reverse_lazy, reverse
from django.views import generic
from django.shortcuts import render, redirect
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
from django.db.models import Q
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError, ContentTooShortError

import tempfile
#from boutiques.localExec import LocalExecutor
#import boutiques as bosh
import sys
import json

from io import StringIO
import hashlib


from atop.carmin import CarminPlatformCandidate
from atop.descriptor import DescriptorDataCandidate, DescriptorDataCandidateURLContainer, DescriptorDataCandidateLocalFileContainer, DescriptorDataCandidateLocalRawContainer, DescriptorEntry
from atop.wsgi import run_queue

from django.shortcuts import redirect



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
    

    
def validate_register(request):
    
    print(request.body)
    
    try:
        JSON_data = json.loads(request.body)
    except:
        return HttpResponseBadRequest()
    
    response = {}

    if (JSON_data["id"] == "username"):
        username = JSON_data["data"]
        if (User.objects.filter(username=username).exists()):
            response["code"] = VALIDATION_FAILURE
            response["message"] = "Username already exists."
        else:
            response["code"] = VALIDATION_SUCCESS
            response["message"] = ""
        
    return JsonResponse(response) 

    

def get_context_home(request):
        
    # Get descriptors that are both (1) set as public and (2) belong to the logged user (if logged)
    user = request.user
    if (user.is_authenticated):
        print("user is authed")
        user_id = User.objects.get(pk=request.user.id)
        descs = Descriptor.objects.filter(Q(user_id=user_id) | Q(is_public=True)).all()
    else:
        descs = Descriptor.objects.filter(is_public=True).all()

    desc_table = DescriptorTable(descs)
    RequestConfig(request).configure(desc_table)
    
    # Table generation
    form = AddDescriptorForm()
    test_tables = []
    for desc in desc_table.page.object_list.data:
                
        desc.data = desc.descriptortest_set.all()
        for test in desc.data:
            test.data = test.descriptortestassertion_set.all()
            for assertion in test.data:
                assertion.type = get_assertion_typestring(assertion.type)
    
    form_signup = UserCreationForm()
    form_login = AuthenticationForm(auto_id='id_login_%s')
    
    context = {'table': desc_table, 'test_tables': test_tables, 'form': form, 'form_signup': form_signup, 'form_login': form_login}
    add_constant_dict(context)
    return context
   
   
def home_redirect(request, message_content=None):
    
    # Check the original URL. We want to keep the GET values that pertain to the descriptor table (sorting, filtering etc..)
    # To do this, we look into the source URL and try to remove any GET that are not related to the table.
    #source_url = request.META["HTTP_REFERER"]
    context = get_context_home(request)
    
    # Add message
    if (message_content != None):
        context["message"] = message_content
    return render(request, 'home.html', context)
   
    
def home(request, test=None):
    
    print(test)
    
    context = get_context_home(request)
    return render(request, 'home.html', context)



VALIDATION_SUCCESS = 0
VALIDATION_FAILURE = 1
DATA_SELECTOR_FILE = 0
DATA_SELECTOR_URL = 1
DATA_SELECTOR_CARMIN = 2


class SignUp(generic.CreateView):

    
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'signup2.html'

    
def jsonize_validation(data):
    response = {}
    if (data == {}):
        response["code"] = VALIDATION_SUCCESS
    else:
        response["code"] = VALIDATION_FAILURE
        for field in data:
            response[field] = []
            for error in data[field]:
                for sub_error in error.messages:
                    response[field].append(str(sub_error))
    return response
    
    
    
def register(request):
    import time
    time.sleep(2)
    
    if request.method == "POST":
        print(request.POST)
        form = UserCreationForm(request.POST)
        if (form.is_valid()):
            form.save()
            response = {"code": VALIDATION_SUCCESS}
        else:
            print(form.is_valid())
            print(form.errors.as_data())
            print(jsonize_validation(form.errors.as_data()))
            
        print(form.errors.as_data())
        
        response = jsonize_validation(form.errors.as_data())
        
        return JsonResponse(response)
    
    # A GET to the url this function is bound to, is used by javscript to indicate the successfull of the registration
    # This is done so as to have control in the back-end over the redirection after this sucessfull registration.
    elif (request.method == "GET"):
        return home_redirect(request)
    
    return HttpResponseBadRequest()
    
    
    
def login(request):
    import time
    time.sleep(2)

    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if (form.is_valid()):
        
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            # Fetch the user object associated to the login details.
            user = authenticate(request, username=username, password=password)
            if user is not None:
            
                # Log the user ounto the website
                auth_login(request, user)
                return JsonResponse({"code": VALIDATION_SUCCESS})
            else:
                return JsonResponse({"code": VALIDATION_FAILURE, "__all__": "Validation failure"})
        
        response = jsonize_validation(form.errors.as_data())
        return JsonResponse(response)
    
    # We redirect for the same reason we redirect in the registration process.
    elif (request.method == "GET"):
        return home_redirect(request)
    
    return HttpResponseBadRequest()
            
    
def delete(request):
    
    if request.method == "GET":
        delete_id = data=request.GET.get("id")
        if (not delete_id):
            return HttpResponseBadRequest()

        # See if the user has the clearence to perform this action
        user = request.user
        if (not user.is_authenticated):
            # Whoever requested this deletion is not even logged in.
            return home_redirect(request, "Could not delete descriptor: user must be logged in to perform this operation")
        
        user_id = User.objects.get(pk=request.user.id)
        descriptor = Descriptor.objects.filter(id=delete_id).all()[0]
        if (not descriptor):
            # Descriptor could not be found.
            return home_redirect(request, "Could not delete descriptor: descriptor not found")

        if (not descriptor.user_id == user_id):
            # User is not the owner of this descriptor
            return home_redirect(request, "Could not delete descriptor: user does not own descriptor")
            
        descriptor.delete()
        
        return home_redirect(request)
        
    else:
        return HttpResponseBadRequest()

    
'''
def validate(request):

    if (request.method != "POST") and (request.method != "GET"):
        return HttpResponseBadRequest()    

    response = {}
    set_code = lambda data_candidate: VALIDATION_SUCCESS if data_candidate.is_valid() else VALIDATION_FAILURE
    
    if request.method == "GET":
        # A GET may refer to two different things: An URL poiting toward a descriptor, or informations about a CARMIN platoform
        # We have to review the 'type' key to make the differentiation
        if (request.GET.get("type") == str(DATA_SELECTOR_URL)):
            
            url = request.GET.get("url")
            if (not url):
                return HttpResponseBadRequest()
                
            data = DescriptorDataCandidate(DescriptorDataCandidateURLContainer(url))
            data.validate()
            response["code"] = set_code(data)
            response["message"] = data.get_message()
            return JsonResponse(response)
           
            #return JsonResponse(validate_descriptor(DATA_SELECTOR_URL, request.GET.get("url")))
        if (request.GET.get("type") == str(DATA_SELECTOR_CARMIN)):
            
            url = request.GET.get("url")
            apikey = request.GET.get("apikey")
            if ((not url) or (not apikey)):
                return HttpResponseBadRequest()
            
            data = CarminPlatformCandidate(url, apikey)
            data.validate()
            response["code"] = set_code(data)
            response["message"] = data.get_message()
            return JsonResponse(response)
            #return JsonResponse(validate_descriptor(DATA_SELECTOR_CARMIN, data))
        else:
            return HttpResponseBadRequest()
           
    if (request.method == "POST"):
        # If the request method is a POST, then we know for sure that we are dealing with a file upload
        
        content = request.body
        data = DescriptorDataCandidate(DescriptorDataCandidateLocalRawContainer(content))
        data.validate()
        response["code"] = set_code(data)
        response["message"] = data.get_message()
        print(data.get_message())
        return JsonResponse(response)
        
        #return JsonResponse(validate_descriptor(DATA_SELECTOR_FILE, request.body))
'''



def validate(request):

    if (request.method != "POST") and (request.method != "GET"):
        return HttpResponseBadRequest()    

    response = {}
    set_code = lambda data_candidate: VALIDATION_SUCCESS if data_candidate.is_valid() else VALIDATION_FAILURE
    
    if request.method == "GET":
        # A GET may refer to two different things: An URL poiting toward a descriptor, or informations about a CARMIN platoform
        # We have to review the 'type' key to make the differentiation
        if (request.GET.get("type") == str(DATA_SELECTOR_URL)):
            
            url = request.GET.get("url")
            if (not url):
                return HttpResponseBadRequest()
                
            data = DescriptorDataCandidate(DescriptorDataCandidateURLContainer(url))
            data.validate()
            response["code"] = set_code(data)
            response["message"] = data.get_message()
            return JsonResponse(response)
           
            #return JsonResponse(validate_descriptor(DATA_SELECTOR_URL, request.GET.get("url")))
        if (request.GET.get("type") == str(DATA_SELECTOR_CARMIN)):
            
            url = request.GET.get("url")
            apikey = request.GET.get("apikey")
            if ((not url) or (not apikey)):
                return HttpResponseBadRequest()
            
            data = CarminPlatformCandidate(url, apikey)
            data.validate()
            response["code"] = set_code(data)
            response["message"] = data.get_message()
            return JsonResponse(response)
            #return JsonResponse(validate_descriptor(DATA_SELECTOR_CARMIN, data))
        else:
            return HttpResponseBadRequest()
           
    if (request.method == "POST"):
        # If the request method is a POST, then we know for sure that we are dealing with a file upload
        
        content = request.body
        data = DescriptorDataCandidate(DescriptorDataCandidateLocalRawContainer(content))
        data.validate()
        response["code"] = set_code(data)
        response["message"] = data.get_message()
        print(data.get_message())
        return JsonResponse(response)
        
        #return JsonResponse(validate_descriptor(DATA_SELECTOR_FILE, request.body))

    


def home(request):



    if request.method == "GET":
        
        context = get_context_home(request)

        return render(request, 'home.html', context)


    elif request.method == "POST":

        form = AddDescriptorForm(request.POST, request.FILES)

        # Perform validation on the form data
        if (not form.is_valid()):
            return render(request, '/')

	    # Perform a validation on the data
        type = int(form.cleaned_data["data_selector"])

        user_id = User.objects.get(pk=request.user.id)

        print("type is" + str(type))
        
        if type == DATA_SELECTOR_CARMIN:
            
            url = form.cleaned_data["data_carmin_platform_url"]
            apikey = form.cleaned_data["data_carmin_platform_apikey"]
            
            data = CarminPlatformCandidate(url, apikey, user=user_id)
            if (data.submit() == False):
                return HttpResponseRedirect(request, '/')

                          
            
        if type == DATA_SELECTOR_FILE:

            # Descriptor is inside POST file data
            file = form.cleaned_data["data_file"].file
            is_public = form.cleaned_data["is_public"]
            data = DescriptorDataCandidate(DescriptorDataCandidateLocalFileContainer(file), is_public=is_public, user=user_id)
            if (data.validate() == False):
                print("not working")
                return render(request, '/')
            data.submit()
                     
        if type == DATA_SELECTOR_URL:
             
            url = form.cleaned_data["data_url"]
            is_public = form.cleaned_data["is_public"]
            automatic_updating = form.cleaned_data["automatic_updating"]
            data = DescriptorDataCandidate(DescriptorDataCandidateURLContainer(url), is_public=is_public, automatic_updating=automatic_updating, user=user_id)
            if (data.validate() == False):
                return render(request, '/')
            data.submit()

        print(form.errors)
                 
        return HttpResponseRedirect("/")


    
def run_tests(request):

    user = User.objects.get(pk=request.user.id)

    run_queue.add(user)

    return redirect(request.META['HTTP_REFERER'])



def log_out(request):

    logout(request)
    return redirect(request.META['HTTP_REFERER'])
    
        


'''
    # Fetch users's descriptors.
    db_descs = Descriptor.objects.all().filter(user_id=user)
    descs = []    
    for db_desc in db_descs:
        descs.append(DescriptorEntry(db_desc)) 

    #TODO: Atomically indicate that the user's descriptors are currently being updated.

    # Run run_test function for each of those tests.
    for desc in descs:
        
        desc.test()
        
    return redirect(request.META['HTTP_REFERER'])
'''
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



def get_assertion_typestring(type):

    if (type == ASSERTION_EXITCODE): return "Exit-code matches"
    if (type == ASSERTION_OUTPUT_FILE_EXISTS): return "Output file exists"
    if (type == ASSERTION_OUTPUT_FILE_MATCHES_MD5): return "Output file exists and matches MD5"