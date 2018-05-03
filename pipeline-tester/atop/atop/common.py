import json
import hashlib
import tempfile
import sys
from boutiques.localExec import LocalExecutor
from io import StringIO

from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError, ContentTooShortError

def get_JSON(filepath):
    with open(filepath, 'r') as fhandle:
        JSON = json.loads(fhandle.read())
    return JSON

def calculate_MD5(content):
    return hashlib.md5(content).hexdigest()
    
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

def create_temporary_file(content):

    temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    temp_file.write(content)
    temp_file.seek(0)
    
    return temp_file


class HTTPGetter:

    def __init__(self, url, request_headers=[]):
        self.error = ""
        self.erroneous = False
        self.data = None
        try:
            req = Request(url)
            for key in request_headers:
                req.add_header(key, request_headers[key])
            self.data = urlopen(req).read()
        except HTTPError as e:
            self.error = "[" + str(e.code) + "] " + str(e.reason)
            self.erroneous = True
        except URLError as e:
            self.error = "URL error (" + str(e.reason) + ")"
            self.erroneous = True
        except ContentTooShortError:
            self.error = "Content too short"
            self.erroneous = True
        except ValueError:
            self.error = "Invalid URL"
            self.erroneous = True
        except Exception as e:
            self.error = str(e)
            self.erroneous = True

    def is_erroneous(self):
        return self.erroneous

    def get_error(self):
        return self.error

    def get_data(self):
        #print("data: " + str(self.data))
        return self.data
