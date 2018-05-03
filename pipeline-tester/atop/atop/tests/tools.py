import atop.descriptor as desc_utils
import atop.carmin as carmin
import os
import json
from atop.common import calculate_MD5
root_path = os.path.realpath(__file__)
import shutil
import os

VALID_SUCC_DESC_A = open(os.path.join(os.path.dirname(root_path), "boutiques_descriptors/tests_good_a.json")).read()
VALID_SUCC_DESC_B = open(os.path.join(os.path.dirname(root_path), "boutiques_descriptors/tests_good_b.json")).read()
VALID_SUCC_DESC_C = open(os.path.join(os.path.dirname(root_path), "boutiques_descriptors/tests_good_c.json")).read()
VALID_SUCC_DESC_D = open(os.path.join(os.path.dirname(root_path), "boutiques_descriptors/tests_good_d.json")).read()


VALID_UNSUCC_DESC_A = open(os.path.join(os.path.dirname(root_path), "boutiques_descriptors/tests_bad_a.json")).read()
VALID_UNSUCC_DESC_B = open(os.path.join(os.path.dirname(root_path), "boutiques_descriptors/tests_bad_b.json")).read()
VALID_UNSUCC_DESC_C = open(os.path.join(os.path.dirname(root_path), "boutiques_descriptors/tests_bad_c.json")).read()

INVALID_DESC_A = open(os.path.join(os.path.dirname(root_path), "boutiques_descriptors/tests_invalid_a.json")).read()
INVALID_DESC_B = open(os.path.join(os.path.dirname(root_path), "boutiques_descriptors/tests_invalid_b.json")).read()
INVALID_DESC_C = open(os.path.join(os.path.dirname(root_path), "boutiques_descriptors/tests_invalid_c.json")).read()

VALID_SUCC_DESC_A_MD5 = calculate_MD5(VALID_SUCC_DESC_A.encode())
VALID_SUCC_DESC_B_MD5 = calculate_MD5(VALID_SUCC_DESC_B.encode())
VALID_SUCC_DESC_C_MD5 = calculate_MD5(VALID_SUCC_DESC_C.encode())
VALID_SUCC_DESC_D_MD5 = calculate_MD5(VALID_SUCC_DESC_D.encode())

VALID_UNSUCC_DESC_A_MD5 = calculate_MD5(VALID_UNSUCC_DESC_A.encode())
VALID_UNSUCC_DESC_B_MD5 = calculate_MD5(VALID_UNSUCC_DESC_B.encode())
VALID_UNSUCC_DESC_C_MD5 = calculate_MD5(VALID_UNSUCC_DESC_C.encode())

INVALID_DESC_A_MD5 = calculate_MD5(INVALID_DESC_A.encode())
INVALID_DESC_B_MD5 = calculate_MD5(INVALID_DESC_B.encode())
INVALID_DESC_C_MD5 = calculate_MD5(INVALID_DESC_C.encode())

VALID_MULTIPLE_TESTS_DESC = open(os.path.join(os.path.dirname(root_path), "boutiques_descriptors/tests_multiple.json")).read()



import atop.models as db
from atop.settings import BASE_DIR

class DbDescriptorTestAssertionComparator:
    
    def __init__(self, type, operand1="", operand2=""):
        self.type = type
        self.operand1 = operand1
        self.operand2 = operand2

    def compare(self, db_assertion):

        if (self.type != db_assertion.type):
            return False
        
        if (self.operand1 != db_assertion.operand1):
            return False
            
        if (self.operand2 != db_assertion.operand2):
            return False
        
        return True



class DbDescriptorTestComparator:
    
    def __init__(self, test_name, evaluated_invocation, execution_status=None):
        self.assertions = []
        self.test_name = test_name
        self.evaluated_invocation = evaluated_invocation
        self.execution_status = execution_status

    def add_assertion(self, assertion):
        self.assertions.append(assertion)

    def compare(self, db_test, run_comparison=False):

        if (run_comparison):
            if (self.execution_status != db_test.execution_status):
                return False
            # To difficult to compare code outputs. We just check if the code output is non-empty
            if (db_test.code == ""):
                return False

        # Check if the name and command match
        if (self.test_name != db_test.test_name or self.evaluated_invocation != db_test.evaluated_invocation):
            return False
        

        # Get all the assertion entries related to this test entry.
        db_asserts = db.DescriptorTestAssertion.objects.filter(test=db_test.id)
        if (len(self.assertions) != len(db_asserts)):
            return False
        

        matches = 0
        i = 0
        while (i < len(self.assertions)):
            assertion = self.assertions[i]
            for db_assert in db_asserts:
                if (assertion.compare(db_assert)):
                    matches += 1
                    break
            i += 1

        if (matches != len(self.assertions)):
            return False

        return True



class DbDescriptorComparator:
    
    def __init__(self):
        self.tests = {}

    def create_test(self, test_name, evaluated_invocation):
        test = DbDescriptorTestComparator(test_name, evaluated_invocation)
        self.tests[test_name] = test

    def add_assertion(self, test_name, assertion):
        self.tests[test_name].add_assertion(assertion)

    def compare(self, db_desc, run_comparison=False):
        
        db_tests = db.DescriptorTest.objects.filter(descriptor=db_desc.id)

        if (len(db_tests) != len(self.tests)):
            return False
            
        for db_test in db_tests:
            test = self.tests.get(db_test.test_name)
            if (not test):
                return False
            status = test.compare(db_test, run_comparison=run_comparison)
            if (not status):
                return False

        return True



multiple_tests_comparator = DbDescriptorComparator()
multiple_tests_comparator.create_test("test1", "exampleTool1.py -c ./config.txt -i foo bar    -e val1  ./setup.py -l 1 2 3  &>  log-4.txt\n")
multiple_tests_comparator.create_test("test2", "exampleTool1.py -c ./config.txt -i foo bar    -e val1  ./setup.py -l 1 2 3  &>  log-4.txt\n")
multiple_tests_comparator.create_test("test3", "exampleTool1.py -c ./config.txt -i foo bar    -e val1  ./setup.py -l 1 2 3  &>  log-4.txt\n")
multiple_tests_comparator.add_assertion("test1", DbDescriptorTestAssertionComparator(db.ASSERTION_EXITCODE, "0"))
multiple_tests_comparator.add_assertion("test1", DbDescriptorTestAssertionComparator(db.ASSERTION_OUTPUT_FILE_MATCHES_MD5, "log-4.txt", "0868f0b9bf25d4e6a611be8f02a880b5"))
multiple_tests_comparator.add_assertion("test2", DbDescriptorTestAssertionComparator(db.ASSERTION_EXITCODE, "0"))
multiple_tests_comparator.add_assertion("test3", DbDescriptorTestAssertionComparator(db.ASSERTION_OUTPUT_FILE_EXISTS, "log-4.txt"))
multiple_tests_comparator.add_assertion("test3", DbDescriptorTestAssertionComparator(db.ASSERTION_OUTPUT_FILE_EXISTS, "./config.txt"))


valid_succ_desc_C_details = DbDescriptorComparator()
valid_succ_desc_C_details.create_test("test3", "exampleTool1.py -c ./config.txt -i foo bar    -e val1  ./setup.py -l 1 2 3  &>  log-4.txt\n")
valid_succ_desc_C_details.add_assertion("test3", DbDescriptorTestAssertionComparator(db.ASSERTION_OUTPUT_FILE_EXISTS, "log-4.txt"))
valid_succ_desc_C_details.add_assertion("test3", DbDescriptorTestAssertionComparator(db.ASSERTION_OUTPUT_FILE_EXISTS, "./config.txt"))

valid_unsucc_desc_A_details = DbDescriptorComparator()
valid_unsucc_desc_A_details.create_test("test1", "exampleTool1.py -c ./config.txt -i foo bar    -e val1  ./setup.py -l 1 2 3  &>  log-4.txt\n")
valid_unsucc_desc_A_details.add_assertion("test1", DbDescriptorTestAssertionComparator(db.ASSERTION_EXITCODE, "0"))
valid_unsucc_desc_A_details.add_assertion("test1", DbDescriptorTestAssertionComparator(db.ASSERTION_OUTPUT_FILE_MATCHES_MD5, "log-4.txt", "WRONGMD5"))

valid_unsucc_desc_B_details = DbDescriptorComparator()
valid_unsucc_desc_B_details.create_test("test1", "exampleTool1.py -c ./config.txt -i foo bar    -e val1  ./setup.py -l 1 2 3  &>  log-4.txt\n")
valid_unsucc_desc_B_details.add_assertion("test1", DbDescriptorTestAssertionComparator(db.ASSERTION_EXITCODE, "99"))

valid_unsucc_desc_C_details = DbDescriptorComparator()
valid_unsucc_desc_C_details.create_test("test1", "exampleTool1.py -c ./config.txt -i foo bar    -e val1  ./setup.py -l 1 2 3  &>  log-4.txt\n")
valid_unsucc_desc_C_details.add_assertion("test1", DbDescriptorTestAssertionComparator(db.ASSERTION_OUTPUT_FILE_EXISTS, "output/*_exampleOutputTag.resultType"))



def md5_compare(query_set, expected_md5_list):
    target_md5_list = []
    for descriptor in query_set.all():
        target_md5_list.append(descriptor.md5)
    for expected_md5 in expected_md5_list:
        if (not (expected_md5 in target_md5_list)):
            return False
    return True

def check_status(descriptor_md5, expected_status):
    desc = db.Descriptor.objects.filter(md5=descriptor_md5).all()[0]
    if (desc):
        if (desc.execution_status == expected_status):
            return True
    return False

class URLBasedDescriptorUpdater:
    
    def __init__(self, url, user):
        self.url = url
        self.user = user
        self.cached_db_desc = None

    def update(self, to_schedule=False,automatic_updating=True):
        if (not self.cached_db_desc):
            desc_data = desc_utils.DescriptorDataCandidate(desc_utils.DescriptorDataCandidateURLContainer(self.url), user=self.user, automatic_updating=automatic_updating)
            if (desc_data.validate() == True):
                desc_data.submit()
                self.cached_db_desc = desc_data.get_db()
        else:
            desc_data = desc_utils.DescriptorEntry(self.cached_db_desc)
            desc_data.update(scheduled=to_schedule)

def delete_user_testing_data():
    
    user_data_testing_path = BASE_DIR + "/user_data_testing/"
    if (os.path.exists(user_data_testing_path)):
        shutil.rmtree(user_data_testing_path)


def file_exists(relative_path):
    full_path = BASE_DIR + "/" + relative_path
    if (os.path.exists(full_path)):
        return True
    return False
