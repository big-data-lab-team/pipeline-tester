from threading import Lock
from queue import Queue

from atop.models import CarminPlatform, Descriptor
from atop.models import EXECUTION_STATUS_SCHEDULED

from django.db.models import Q

import atop.carmin as carmin
import atop.descriptor as desc_utils

class RunQueue:
   
    def __init__(self):
        self.lock = Lock()
        self.queue = Queue()

        self.serving_lock = Lock()
    
    # Takes a user as argument
    def add(self, user):

        self.serving_lock.acquire(True)       

        # First: check if the user can add descriptors / carmin platforms to the RunQueue.
        allowed, message = self.is_allowed(user)
        if (not allowed):
            return (False, message)
        
        # Then:
        self.prepare(user)

        self.serving_lock.release()        


        # Acquire semaphore
        self.lock.acquire(True)


        # Add user to queue
        self.queue.put(user)
       
        # Release semaphore
        self.lock.release()
        return (True, None)

    def is_allowed(self, user):
        
        if (user in self.queue.queue):
            return (False, "User's descriptors update already scheduled/in progress")       
        return (True, None)
       
   
    def prepare(self, user):

        descriptors = []
        
        # Update and get all the carmin platforms
        get_platforms = CarminPlatform.objects.filter(user=user)
        db_carmin_platforms = get_platforms.all()

        if (db_carmin_platforms):
            for db_carmin_platform in db_carmin_platforms:
                carmin_platform = carmin.CarminPlatformEntry(db_carmin_platform)
                carmin_platform.update(scheduled=True)

        # Update and get all the URL specified descriptors
        get_url_based_descriptors = Descriptor.objects.filter(automatic_updating=True, user_id=user)
        url_based_descriptors = get_url_based_descriptors.all()
        
        if (url_based_descriptors):
            for db_desc in url_based_descriptors:
                desc = desc_utils.DescriptorEntry(db_desc)
                desc.update(scheduled=True)

        # Get local descriptors
        get_regular_descriptors = Descriptor.objects.filter(Q(automatic_updating=False) & Q(carmin_platform=None))
        regular_descriptors = get_regular_descriptors.all()

        if (regular_descriptors):
            for db_desc in regular_descriptors:
                desc = desc_utils.DescriptorEntry(db_desc)
                desc.update(scheduled=True)


    def run_loop(self):
       
        while 1:
            # If the queue contains a user instance
            self.serve()

                    

    def serve(self):

        if (not self.queue.empty()):
            # Pop it
            user = self.queue.get()
           
            # We get the descriptors that belong to the user.
            # In addition to that we also exclude descriptors that have been marked as erroneous during the preparation part.
            get_descriptors = Descriptor.objects.filter(Q(user_id=user) & Q(execution_status=EXECUTION_STATUS_SCHEDULED))
            db_descs = get_descriptors.all()
            #for db_desc in db_descs:
            #   print("n:" + db_desc.tool_name)
            
            for db_desc in db_descs:
                desc = desc_utils.DescriptorEntry(db_desc)
                desc.test()        
                    
                
