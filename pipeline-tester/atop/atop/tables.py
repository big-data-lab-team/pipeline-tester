import django_tables2 as tables
from atop.models import Descriptor, DescriptorTest
from atop.models import EXECUTION_STATUS_UNCHECKED, EXECUTION_STATUS_SUCCESS, EXECUTION_STATUS_FAILURE, EXECUTION_STATUS_ERROR, EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_RUNNING
import itertools
from django.utils.html import format_html

class DescriptorTable(tables.Table):

    expand_button = tables.TemplateColumn(verbose_name="", template_name='column_expand.html', orderable=False)
    status_icon = tables.Column(verbose_name="", orderable=False, empty_values=())
    actions = tables.Column(verbose_name="", orderable=False, empty_values=())
    
    class Meta:
        model = Descriptor
        template_name = 'bootstrap.html'
        fields = ('expand_button', 'status_icon', 'execution_status', 'tool_name', 'version', 'carmin_platform', 'last_updated', 'is_public', 'actions')


    def render_carmin_platform(self, value, record):
        if (record.carmin_platform):
            name = record.carmin_platform.name
            return name
    
    def render_is_public(self, value):
        if (value == True):
            return "Public"
        else:
            return "Private"
        
    def render_edit(self):
        return ''
    
    def render_actions(self, record):
        return format_html('<div style="vertical-align: middle;"><a href="#"><center><div class="action-delete"  delete-id="{}"><i class="fas fa-trash fa-lg fa-fw"></i></div></center></a></div>', record.pk)
    
    def get_record_color(self, record):
        
        status = record.execution_status
        if (status == EXECUTION_STATUS_UNCHECKED):
            return "grey"
        if (status == EXECUTION_STATUS_SUCCESS):
            return "#28a745"
        if (status == EXECUTION_STATUS_FAILURE):
            return "#dc3545"
        if (status == EXECUTION_STATUS_ERROR):
            return "#b38400"
        if (status == EXECUTION_STATUS_SCHEDULED):
            return "#99498a"
        if (status == EXECUTION_STATUS_RUNNING):
            return "chocolate"
    
    def render_status_icon(self, record):
        
        status = record.execution_status
        icon = ""
        if (status == EXECUTION_STATUS_UNCHECKED):
            icon = "question"
        if (status == EXECUTION_STATUS_SUCCESS):
            icon = "check"
        if (status == EXECUTION_STATUS_FAILURE):
            icon = "times"
        if (status == EXECUTION_STATUS_ERROR):
            icon = "exclamation-triangle"
        if (status == EXECUTION_STATUS_SCHEDULED):
            icon = "clock"
        if (status == EXECUTION_STATUS_RUNNING):
            icon = "spinner fa-pulse"
        return format_html('<div style="vertical-align: middle;"><center><i class="fas fa-{} fa-lg fa-fw" style="color:{}"></i></center></div>', icon, self.get_record_color(record))
        
    def render_execution_status(self, value, record):
            
        print(record.execution_status)
        
        message = ""        
        if (value == EXECUTION_STATUS_UNCHECKED):
            message = "Unchecked"
        if (value == EXECUTION_STATUS_SUCCESS):
            message = "Successful"
        if (value == EXECUTION_STATUS_FAILURE):
            message = "Unsucessful"
        if (value == EXECUTION_STATUS_ERROR):
            message = "Error"
        if (value == EXECUTION_STATUS_SCHEDULED):
            message = "Scheduled"
        if (value == EXECUTION_STATUS_RUNNING):
            message = "In progress"
        
        return format_html('<div style="color:{}">{}</div>', self.get_record_color(record), message)
        
    def render_tool_name(self, value, record):
        
        return format_html('<div style="color:{}"><b>{}</b></div>', self.get_record_color(record), value)

    def render_version(self, value, record):
        
        return format_html('<div style="color:{}">{}</div>', self.get_record_color(record), value)

class DescriptorTestTable(tables.Table):

    class Meta:
        model = DescriptorTest
        template_name = 'django_tables2/bootstrap.html'
