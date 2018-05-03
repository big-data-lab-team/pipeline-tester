from django import forms

class AddDescriptorForm(forms.Form):

    data_url = forms.CharField(required=False, help_text="Enter a URL pointing to a descriptor", label="Enter URL pointing to descriptor", widget=forms.TextInput(attrs={'class': 'form-control', 'type':'url', 'placeholder':'http://'}))
    data_file = forms.FileField(required=False, help_text="Select a descriptor to upload", widget=forms.FileInput(attrs={'class': 'custom-file-input'}))
    
    is_public = forms.BooleanField(required=False, initial=False,
                                   label="Display the descriptor's tests publicly", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
                                   
    automatic_updating = forms.BooleanField(required=False, initial=False,
                                            help_text="Should the descriptor be fetched from URL everytime?", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
                                            
    data_carmin_platform_url = forms.CharField(required=False, help_text="Enter a URL pointing toward a CARMIN platform", widget=forms.TextInput(attrs={'class': 'form-control', 'type':'url', 'placeholder':'http://'}))
    data_carmin_platform_apikey =  forms.CharField(required=False, help_text="Enter an API key for the associated CARMIN platform", widget=forms.TextInput(attrs={'class': 'form-control'}))                  
    
    
    HIDDEN_SELECTOR_COMPUTER = 0
    HIDDEN_SELECTOR_WEB = 1
    data_selector = forms.CharField()
    #data_file.widget.attrs["class"] = "custom-file-input"

#    def clean_renewal_date(self):
#        # Either URL or File must be set.
#        if data_url and data_file:
#            raise ValidationError(_('Specify a descriptor URL or upload a file, not both'))
#        if not data_url and not data_file:
#            raise ValidationError(_('Specify a descriptor URL or upload a file'))
#        if id == null:
#            raise ValidationError(_('Descriptor ID required'))

    def clean(self):
        data = self.cleaned_data
        if data["data_selector"] == "tab-web":
            if data["data_url"] == "":
                raise forms.ValidationError({"data_url": 'Provide an URL pointing to a descriptor'})
            else:
                return data
                
        if data["data_selector"] == "tab-computer":
            if data["data_file"] == None:
                raise forms.ValidationError({'data_file': 'Provide a file pointing to a descriptor'})
            else:
                return data
                
        if data["data_selector"] == "tab-carmin":
            if data["data_carmin_platform_url"] == None:
                 raise forms.ValidationError({'data_carmin_platform_apikey': 'Provide an URL pointing to a CARMIN platform'})
            if data["data_carmin_platform_apikey"] == None:
                 raise forms.ValidationError({'data_carmin_platform_apikey': 'Provide an API-key'})
            return data
             
               
