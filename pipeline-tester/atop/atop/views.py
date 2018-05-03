# atop/views.py
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate, logout
from django.contrib.auth import login as auth_login
from django.shortcuts import render, redirect
from django_tables2 import RequestConfig
from atop.models import Descriptor, CarminPlatform, EXECUTION_STATUS_UNCHECKED, DescriptorTest, DescriptorTestAssertion
from atop.tables import DescriptorTable, DescriptorTestTable
from atop.forms import AddDescriptorForm
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse, HttpResponseBadRequest
from atop.models import ASSERTION_EXITCODE, ASSERTION_OUTPUT_FILE_EXISTS, ASSERTION_OUTPUT_FILE_MATCHES_MD5
from django.db.models import Q


from atop.carmin import CarminPlatformCandidate, CarminPlatformEntry
from atop.descriptor import DescriptorDataCandidate, DescriptorDataCandidateURLContainer, DescriptorDataCandidateLocalFileContainer, DescriptorDataCandidateLocalRawContainer, DescriptorEntry
from atop.wsgi import run_queue

import json

    
def validate_register(request):
    
    
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
        #print("user is authed")
        user_id = User.objects.get(pk=request.user.id)
        descs = Descriptor.objects.filter(Q(user_id=user_id) | Q(is_public=True)).all()
        db_carminpfs = CarminPlatform.objects.filter(user=user).all()
    else:
        descs = Descriptor.objects.filter(is_public=True).all()
        db_carminpfs = None

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
    
    context = {'table': desc_table, 'test_tables': test_tables, 'form': form, 'form_signup': form_signup, 'form_login': form_login, 'carmin_servers': db_carminpfs}
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
 

VALIDATION_SUCCESS = 0
VALIDATION_FAILURE = 1
DATA_SELECTOR_FILE = 0
DATA_SELECTOR_URL = 1
DATA_SELECTOR_CARMIN = 2


    
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
    
    if request.method == "POST":
        #print(request.POST)
        form = UserCreationForm(request.POST)
        if (form.is_valid()):
            form.save()
            response = {"code": VALIDATION_SUCCESS}
        #else:
            #print(form.is_valid())
            #print(form.errors.as_data())
            #print(jsonize_validation(form.errors.as_data()))
            
        #print(form.errors.as_data())
        
        response = jsonize_validation(form.errors.as_data())
        
        return JsonResponse(response)
    
    # A GET to the url this function is bound to, is used by javscript to indicate the successfull of the registration
    # This is done so as to have control in the back-end over the redirection after this sucessfull registration.
    elif (request.method == "GET"):
        return redirect("/")
    
    messages.add_message(request, messages.INFO, 'Could not register: malformed request')
    return redirect("/")

    
    
    
def login(request):

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
        return redirect("/")
    
    messages.add_message(request, messages.INFO, 'Could not login: malformed request')
    return redirect("/")

            
DELETE_TYPE_DESCRIPTOR = 0
DELETE_TYPE_CARMIN_PLATFORM = 1
from django.contrib import messages
def delete(request):

    if request.method == "GET":

        raw_delete_id = request.GET.get("id")
        if (not raw_delete_id):
            messages.add_message(request, messages.INFO, 'Cannot delete: id not specified')
            return redirect("/")

        
        raw_delete_type = request.GET.get("type")
        if (not raw_delete_type):
            messages.add_message(request, messages.INFO, 'Cannot delete: type not specified')
            return redirect("/")            

        try:
            delete_id = int(raw_delete_id)
        except:
            messages.add_message(request, messages.INFO, 'Cannot delete: expected integer as id')
            return redirect("/")

        try:
            delete_type = int(raw_delete_type)
        except:
            messages.add_message(request, messages.INFO, 'Cannot delete: expected integer as type')
            return redirect("/")
            

        # See if the user has the clearence to perform this action
        user = request.user
        if (not user.is_authenticated):
            # Whoever requested this deletion is not even logged in.
            #return home_redirect(request, "Could not delete object: user must be logged in to perform this operation")
            messages.add_message(request, messages.INFO, 'Could not delete object: user must be logged in to perform this operation')
            return redirect("/")
        
        user_id = User.objects.get(pk=request.user.id)
        if (delete_type == DELETE_TYPE_DESCRIPTOR):


            descriptor_queryset = Descriptor.objects.filter(id=delete_id)
            if (len(descriptor_queryset) == 0):
                # Descriptor could not be found.
                messages.add_message(request, messages.INFO, 'Could not delete descriptor: descriptor not found')
                return redirect("/")

            db_desc = descriptor_queryset.all()[0]

            if (not db_desc.user_id == user_id):
                # User is not the owner of this descriptor
                #return home_redirect(request, "Could not delete descriptor: user does not own descriptor")
                messages.add_message(request, messages.INFO, 'Could not delete descriptor: user does not own descriptor')
                return redirect("/")
    
            db_desc.delete()
            
            return redirect("/")

        if (delete_type == DELETE_TYPE_CARMIN_PLATFORM):
            
            carmin_queryset = CarminPlatform.objects.filter(id=delete_id)
            if (len(carmin_queryset) == 0):
                # Carmin platform could not be found.
                messages.add_message(request, messages.INFO, 'Could not delete carmin platform: carmin platform not found')
                return redirect("/")

            db_car = carmin_queryset.all()[0]

            if (not db_car.user == user_id):
                # User is not the owner of this carmin platform entry
                messages.add_message(request, messages.INFO, 'Could not delete carmin platform: user does not own carmin platform entry')
                return redirect("/")
            
            carmin = CarminPlatformEntry(db_car)
            carmin.delete()

            return redirect("/")
        
        messages.add_message(request, messages.INFO, 'Cannot delete: uknown object type')
        return redirect("/")

    else:
        messages.add_message(request, messages.INFO, 'Cannot delete: malformed request')
        return redirect("/")

 

def validate(request):

    user = request.user
    if (not user.is_authenticated):
        # Whoever requested this deletion is not even logged in.
        return HttpResponseBadRequest()


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
        #print(data.get_message())
        return JsonResponse(response)
        
        #return JsonResponse(validate_descriptor(DATA_SELECTOR_FILE, request.body))

    


def home(request):

    if request.method == "GET":
        
        context = get_context_home(request)

        return render(request, 'home.html', context)


    elif request.method == "POST":

        user = request.user
        if (not user.is_authenticated):
            messages.add_message(request, messages.INFO, 'Could not add descriptor/platform: user not logged in')
            return redirect("/")

        form = AddDescriptorForm(request.POST, request.FILES)

        # Perform validation on the form data
        if (not form.is_valid()):
            messages.add_message(request, messages.INFO, 'Could not add descriptor/platform: invalid form')
            return redirect("/")

	    # Perform a validation on the data
        type = int(form.cleaned_data["data_selector"])

        user_id = User.objects.get(pk=request.user.id)

        #print("type is" + str(type))
        
        if type == DATA_SELECTOR_CARMIN:
            
            url = form.cleaned_data["data_carmin_platform_url"]
            apikey = form.cleaned_data["data_carmin_platform_apikey"]
            is_public = form.cleaned_data["is_public"]            

            data = CarminPlatformCandidate(url, apikey, user=user_id, is_public=is_public)
            if (data.submit() == False):
                messages.add_message(request, messages.INFO, 'Could not add descriptor/platform: ' + str(data.get_message()))
                return redirect("/")


                          
            
        if type == DATA_SELECTOR_FILE:

            # Descriptor is inside POST file data
            file = form.cleaned_data["data_file"].file
            is_public = form.cleaned_data["is_public"]
            data = DescriptorDataCandidate(DescriptorDataCandidateLocalFileContainer(file), is_public=is_public, user=user_id)
            if (data.validate() == False):
                messages.add_message(request, messages.INFO, 'Could not add descriptor/platform: ' + str(data.get_message()))
                return redirect("/")

            data.submit()
                     
        if type == DATA_SELECTOR_URL:
             
            url = form.cleaned_data["data_url"]
            is_public = form.cleaned_data["is_public"]
            automatic_updating = form.cleaned_data["automatic_updating"]
            data = DescriptorDataCandidate(DescriptorDataCandidateURLContainer(url), is_public=is_public, automatic_updating=automatic_updating, user=user_id)
            if (data.validate() == False):
                messages.add_message(request, messages.INFO, 'Could not add descriptor/platform: ' + str(data.get_message()))
                return redirect("/")

            data.submit()

        #print(form.errors)
                 
        return HttpResponseRedirect("/")


    
def run_tests(request):

    user = request.user
    if (not user.is_authenticated):
        messages.add_message(request, messages.INFO, 'Could not add to run queue: user not logged in')
        return redirect("/")

    valid, error_message = run_queue.add(user)

    if (not valid):
        messages.add_message(request, messages.INFO, 'Could not add to run queue: ' + error_message)
        return redirect("/")
    else:
        return redirect("/")



def log_out(request):

    logout(request)
    return redirect("/")
    

def get_assertion_typestring(type):

    if (type == ASSERTION_EXITCODE): return "Exit-code matches"
    if (type == ASSERTION_OUTPUT_FILE_EXISTS): return "Output file exists"
    if (type == ASSERTION_OUTPUT_FILE_MATCHES_MD5): return "Output file exists and matches MD5"
