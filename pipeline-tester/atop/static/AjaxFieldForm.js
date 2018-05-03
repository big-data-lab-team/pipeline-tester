
const FIELD_VALIDATOR_VALIDATION_SUCESS = 0
const FIELD_VALIDATOR_VALIDATION_FAILURE = 1

const FIELD_VALIDATOR_STATUS_IDLE = 0
const FIELD_VALIDATOR_STATUS_LOADING = 1
const FIELD_VALIDATOR_STATUS_SUCCESS = 2
const FIELD_VALIDATOR_STATUS_FAILURE = 3

const FIELD_VALIDATOR_ICON_LOADING = 0;
const FIELD_VALIDATOR_ICON_SUCCESS = 1;
const FIELD_VALIDATOR_ICON_FAILURE = 2;
const FIELD_VALIDATOR_ICON_IDLE = 3;


function AjaxField(fieldId, msgId, ajaxId) {
    
    this.fieldId = fieldId;
    this.hField = "#" + fieldId;
    this.msgId = msgId;
    this.hMsgId = "#" + msgId;
    this.ajaxId = ajaxId;
    this.valid = false;
    var that = this;
    $(this.hMsgId).hide();
                    
            
    this.setSuccess = function() {
        this.valid = true;
        $(this.hMsgId).hide();
    }

    this.setFailure = function() {
        this.valid = false;
    }
    
    this.reset = function() {
        //$(this.hMsgId).html("");
        
        this.messages = [];
                
        this.valid = false;
    }
            
    
    this.addMessages = function(messages) {
        
        var htmlMessages = "<ul>";
        for (var i = 0; i < messages.length; i++) {
            htmlMessages += "<li>" + messages[i] + "</li>";
        }
        htmlMessages += "</ul>";
        $(this.hMsgId).html(htmlMessages);
        
        if ($(this.hMsgId).is(":visible") == false) {
            $(this.hMsgId).show();
        };
    }
    
    this.isValid = function() {
        return this.valid;
    }
    
    this.getAjaxId = function() {
        return this.ajaxId;
    }
    
    this.getValue = function() {
        return $(this.hField).val();
    }
     
}

function AjaxFieldForm(fields, url, form, statusIcon, redirectionUrl) {

    this.fields = fields;
    this.url = url;
    this.form = form;
    this.hForm = "#" + form;
    this.statusIcon = statusIcon;
    this.hStatusIcon = "#" + statusIcon;
    this.redirectionUrl = redirectionUrl;
    this.FORM_SUCCESS = 0;
    this.FORM_FAILURE = 1;
    var that = this;

    this.csrfSafeMethod = function(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }


    this._reset = function() {
        for (i = 0; i < this.fields.length; i++) {
            this.fields[i].reset();
        }
    }
   
    this._loadingStart = function() {
        /*
        for (i = 0; i < this.fields.length; i++) {
            this.fields[i].setLoading();
        }
        */
        $(this.hStatusIcon).show();
        
        
    }
    
    this._loadingStop = function() {

        $(this.hStatusIcon).hide();
        
    }
    
    this._setSuccessful = function() {
    
        $(this.hStatusIcon).html('<i class="fas fa-check fa-lg fa-fw" style="color: #28a745"></i>');
        window.location.replace(this.redirectionUrl);
        
    }
    
    this._jsonize = function() {
        var jsonData = {};
        for (i = 0; i < this.fields.length; i++) {
            field = this.fields[i];
            jsonData[field.getAjaxId()] = field.getValue();
        }
        return jsonData;
    }
    
    
    this.validate_and_submit = function() {

        this._reset();
        this._loadingStart();
                    
        //var jsonInput = this._jsonize();
                    
        var csrftoken = jQuery("[name=csrfmiddlewaretoken]").val();
        ajaxRequest = {
            beforeSend: function(xhr, settings) {
                if (!that.csrfSafeMethod(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken);
                    //xhr.setRequestHeader("Content-Type", content.type);
                }
            },
            dataType: "text",
            type: "POST",
            data:  $(that.hForm).serialize(),
            url: this.url,
            processData: false,
            success: function (data) {
                jsonData = JSON.parse(data);
                // Parse all the possible error messages.
                for (i = 0; i < that.fields.length; i++) {
                    var field = that.fields[i];
                    var id = field.getAjaxId();
                    if (id in jsonData) {
                        that._loadingStop();
                        var messages = jsonData[id];
                        field.setFailure();
                        field.addMessages(messages);
                    }
                    else {
                        field.setSuccess();
                    }
                }
                    
                if (jsonData['code'] == that.FORM_SUCCESS) {
                    that._setSuccessful();                        
                }
                return;
            },
            error: function (data) {
                that._loadingStop();
                for (i = 0; i < (that.fields.length - 1); i++) {
                    that.fields[i].setSuccess();
                }
                last_field_id = that.fields.length - 1;
                that.fields[last_field_id].setFailure();
                that.fields[last_field_id].addMessages(["A problem occured with our server.<br>Please try again later."]);
            }
        };
        $.ajax(ajaxRequest);         
    }

}

