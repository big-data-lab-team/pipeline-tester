$(document).ready(function(){

    const DATA_FILE = 0;
    const DATA_URL = 1;
    const DATA_CARMIN = 2;
    const POST = 0;
    const GET = 1;
    const VALIDATION_SUCCESS = 0;
    const VALIDATION_FAILURE = 1;
    const MSG_STATUS_IDLE = 0;
    const MSG_STATUS_SUCCESS = 1;
    const MSG_STATUS_FAILURE = 2;

    function DataSelector(tab, fieldId, fieldId_bis, msgId, type) {
        this.that = this;
        this.tab = tab;
        this.fieldId = fieldId;
        this.hFieldId = "#" + fieldId;
        this.fieldId_bis = fieldId_bis;
        this.hFieldId_bis = "#" + fieldId_bis;
        this.msgId = msgId;
        this.hMsgId = "#" + msgId;
        this.type = type;
        this.erroneous = false;
        this.valid = false;
        var that = this;
        
        if (type == DATA_FILE) {
        
            submit = POST;

        }
        
        else {
            submit = GET;              
        }
        
        
        // Hide the message box
        $(this.hMsgId).hide();
        

        this.processData = function() {
        
            that.validate();                
            
        }
        
     
        //preprocess
        
        this.csrfSafeMethod = function(method) {
            // these HTTP methods do not require CSRF protection
            return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }


        this.validate = function() {
                    
            this.displayMessage(MSG_STATUS_IDLE, "Loading..");

            var csrftoken = jQuery("[name=csrfmiddlewaretoken]").val();

            ajaxRequest = {
                beforeSend: function(xhr, settings) {
                    if (!that.csrfSafeMethod(settings.type) && !this.crossDomain) {
                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
                        //xhr.setRequestHeader("Content-Type", content.type);
                    }
                },
                url: "/validate_descriptor/",
                success: function (jsonData) {
                                 
                    if (jsonData['code'] == VALIDATION_SUCCESS) {
                        that.erroneous = false;
                        that.valid = true;
                        that.displayMessage(MSG_STATUS_SUCCESS, jsonData["message"]);
                    }
                    if (jsonData['code'] == VALIDATION_FAILURE) {
                        that.erroneous = true;
                        that.valid = false;
                        that.displayMessage(MSG_STATUS_FAILURE, jsonData["message"]);
                    }
                },
                error: function (data) {
                    //alert(data);
                    that.displayMessage(MSG_STATUS_FAILURE, "A problem occured with our server.<br>Please try again later.");
                }
            };
            
            switch(this.type) {
                
                case DATA_FILE:
                    var input  = document.getElementById(this.fieldId);
                    var file = input.files[0];
                    ajaxRequest["type"] = "POST";
                    ajaxRequest["data"] = file;
                    ajaxRequest["processData"] = false;
                    ajaxRequest["contentType"] = false;
                    break;
                
                case DATA_URL:
                    var url = $(this.hFieldId).val();
                    ajaxRequest["type"] = "GET";
                    ajaxRequest["data"] = {'type': DATA_URL, 'url': url};
                    ajaxRequest["processData"] = true;
                    //ajaxRequest["contentType"] = false;
                    break;
                
                case DATA_CARMIN:
                    var url  = $(this.hFieldId).val();
                    var apikey  = $(this.hFieldId_bis).val();
                    ajaxRequest["type"] = "GET";
                    ajaxRequest["data"] = {'type': DATA_CARMIN,'url': url, 'apikey': apikey};
                    ajaxRequest["processData"] = true;
                    break;
            
            }

            $.ajax(ajaxRequest);         
        }
        
        this.submit = function() {
            
            if (this.type == DATA_CARMIN) {
                
                var url = document.getElementById(this.fieldId);
                var apikey = document.getElementById(this.fieldId_bis);
                
                if (!(url && url.value)) {
                    this.displayMessage(MSG_STATUS_FAILURE, "Please provide an URL ponting to a CARMIN platform");
                    return false;
                }
                
                if (!(apikey && apikey.value)) {
                    this.displayMessage(MSG_STATUS_FAILURE, "Please provide an API key to authenticate on the associated CARMIN platform");
                    return false;
                }
            
            }
            
            else {
            
                // Check if the field has data in it.
                var myInput = document.getElementById(this.fieldId);
                if (!(myInput && myInput.value)) {
                    this.displayMessage(MSG_STATUS_FAILURE, "Please provide a descriptor");
                    return false;
                }
                
            }
            
            // Check that we do not have any errors associated with the data.
            if (this.erroneous || !this.valid) {
                //alert(this.valid);
                return false;
            }
            
            // Submission can proceed.
            // Indicate that this tab should be the one to process
            $('<input />').attr('type', 'hidden')
               .attr('name', "data_selector")
               .attr('value', type)
               .attr('id', "id_data_selector")
               .appendTo('#form1');
            
            return true;
            
        };
                
        
        this.reset = function() {
            
            this.erroneous = false;
            this.valid = false;
            $(this.hMsgId).hide();

        }

        this.displayMessage = function(status, message) {
            
            var msg = document.getElementById(this.msgId);

            switch(status) {
                case MSG_STATUS_IDLE:
                    msg.className = "alert alert-secondary";
                    break;
                    
                 case MSG_STATUS_SUCCESS:
                     msg.className = "alert alert-success";
                     break;
                     
                 case MSG_STATUS_FAILURE:
                    msg.className = "alert alert-danger";
                    break;
            }

            $(this.hMsgId).html(message);

            if ($(this.hMsgId).is(":visible") == false) {
                $(this.hMsgId).show();
            };

        }
        
    }

    
    var dataFile = new DataSelector("tabs-1", "id_data_file", null, "msg_file", DATA_FILE);
    var dataURL = new DataSelector("tabs-2", "id_data_url", null, "msg_url", DATA_URL);
    var dataCarmin = new DataSelector("tabs-3", "id_data_carmin_platform_url", "id_data_carmin_platform_apikey", "msg_carmin", DATA_CARMIN);

     // Process URL once the user is done typing
    var typingTimer;
    var doneTypingInterval = 3000;
    var $input = $('#id_data_url');
    $('#id_data_url').keyup(function(){
        clearTimeout(typingTimer);
        dataURL.reset();
        if ($('#id_data_url').val()) {
            typingTimer = setTimeout(dataURL.processData, doneTypingInterval);
        }
        
    });
    $('#id_data_url').blur(function(){
        clearTimeout(typingTimer);
        if ($('#id_data_url').val()) {
            dataURL.processData();
        }
    });
            
    // Process file upon selection
    $(id_data_file).change(function() {
        dataFile.processData();
        let fileName = $(this).val().split('\\').pop(); 
        $(this).next('.custom-file-control').addClass("selected").html(fileName);         
    });
    
    // Process CARMIN url when:
        // (1) The user is done typing after X amount of time in the currently selected field
        // (2) The other field has data in it
    function isCarminInputReady() {
        if ($('#id_data_carmin_platform_url').val() && $('#id_data_carmin_platform_apikey').val()) {
            return true;
        }
        return false;
    }
    var typingTimer_carmin;
    $('#id_data_carmin_platform_url').keyup(function(){
        clearTimeout(typingTimer_carmin);
        dataCarmin.reset();
        if (isCarminInputReady()) {
            typingTimer_carmin = setTimeout(dataCarmin.processData, doneTypingInterval);
        }
    });
    $('#id_data_carmin_platform_apikey').keyup(function(){
        clearTimeout(typingTimer_carmin);
        dataCarmin.reset();
        if (isCarminInputReady()) {
            typingTimer_carmin = setTimeout(dataCarmin.processData, doneTypingInterval);
        }
    });
        // (1) The current field has been defocused and has data in it
        // (2) The other field has data in it
    $('#id_data_carmin_platform_url').blur(function(){
        clearTimeout(typingTimer_carmin);
        if (isCarminInputReady()) {
            dataCarmin.processData();
        }
    });
    $('#id_data_carmin_platform_apikey').blur(function(){
        clearTimeout(typingTimer_carmin);
        if (isCarminInputReady()) {
            dataCarmin.processData();
        }
    });



    
    function getActiveTab() {
        var ul = document.getElementById("tabs");
        var items = ul.getElementsByTagName("a")
        for (var i = 0; i < items.length; ++i) {
            if (items[i].className.includes("active")) {
                return items[i].id;
            }
        }
    }

    $("#form1").submit( function(eventObj) {
        
        var activeTab = getActiveTab();
        if (activeTab == "tab-web") {
        
            return dataURL.submit();
        }
        if (activeTab == "tab-computer") {
            return dataFile.submit();
        }
        if (activeTab == "tab-carmin") {
            return dataCarmin.submit();
        }

        
    });
    
    
    $('#tabs a').click(function (e) {
      e.preventDefault()
      $(this).tab('show')
    });
    
    $('#tabs a').click(function (e) {
      e.preventDefault()
      $(this).tab('show')
    });
});

