# models.py
from django.db import models
from django.contrib.auth.models import User




def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return 'user_data/user_{0}/{1}'.format(instance.user_id.id, filename)

class CarminPlatform(models.Model):
    root_url = models.URLField(default="")
    api_key = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_public = models.BooleanField(default=False, verbose_name="exposure")
    name = models.CharField(max_length=100)

EXECUTION_STATUS_UNCHECKED = 0
EXECUTION_STATUS_SUCCESS = 1
EXECUTION_STATUS_FAILURE = 2
EXECUTION_STATUS_ERROR = 3
EXECUTION_STATUS_SCHEDULED = 4
EXECUTION_STATUS_RUNNING = 5
class Descriptor(models.Model):
    tool_name = models.CharField(max_length=100, verbose_name="tool name")
    version = models.CharField(max_length=100, verbose_name="version")
    execution_status = models.IntegerField(default=EXECUTION_STATUS_UNCHECKED, verbose_name="status")
    is_public = models.BooleanField(default=False, verbose_name="exposure")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="last updated")
    
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    data_url = models.URLField(default="")
    data_file = models.FileField(default="", upload_to=user_directory_path)
    
    automatic_updating = models.BooleanField(default=False, verbose_name="updated automatically")
    
    error_message = models.TextField(default="")
    md5 = models.CharField(max_length=16)
    
    carmin_platform = models.ForeignKey(CarminPlatform, on_delete=models.CASCADE, null=True)

TEST_STATUS_UNCHECKED = 0
TEST_STATUS_SUCCESS = 1
TEST_STATUS_FAILURE = 2
class DescriptorTest(models.Model):
    execution_status = models.IntegerField(default=TEST_STATUS_UNCHECKED, verbose_name="status")
    test_name = models.CharField(max_length=100, verbose_name="test name")
    evaluated_invocation = models.CharField(max_length=500, verbose_name="invocation")
    descriptor = models.ForeignKey(Descriptor, on_delete=models.CASCADE)
    code = models.TextField()
    
ASSERTION_EXITCODE = 0
ASSERTION_OUTPUT_FILE_EXISTS = 1
ASSERTION_OUTPUT_FILE_MATCHES_MD5 = 2
class DescriptorTestAssertion(models.Model):
    type = models.IntegerField()
    operand1 = models.CharField(max_length=100)
    operand2 = models.CharField(max_length=100)
    test = models.ForeignKey(DescriptorTest, on_delete=models.CASCADE)
    
