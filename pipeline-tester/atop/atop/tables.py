import django_tables2 as tables
from .models import Descriptor, DescriptorTest
import itertools

class DescriptorTable(tables.Table):

    expand_button = tables.TemplateColumn(template_name='column_expand.html', orderable=False)
    edit = tables.LinkColumn('item_edit', args=[], orderable=False, empty_values=())
    
    class Meta:
        model = Descriptor
        template_name = 'bootstrap.html'
        fields = ('expand_button', 'execution_status', 'tool_name', 'date_added', 'is_public', 'edit')
		
    def render_edit(self):
        return 'Edit'
        
        
class DescriptorTestTable(tables.Table):

    class Meta:
        model = DescriptorTest
        template_name = 'django_tables2/bootstrap.html'