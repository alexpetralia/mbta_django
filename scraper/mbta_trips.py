# @author: apetralia

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

from datetime import timedelta, datetime as dt
# from django.conf import settings as django_settings
import requests
import time
import logging

from .settings.api_key import API_KEY
from .settings.routes import ROUTES
from .models import CompletedTrip, TripCount, apiStatus

WAIT_TIME_SEC = 10

class Route():
    
    """
    Route class houses all of the Direction objects.
    """
    
    def __init__(self, route_name, ignored_trips):
        self.directions = {}
        self.route_name = route_name
        self.ignored_trips = ignored_trips
        
    def update_route(self, json):
        
        """
        Updates all of the Direction objects.
        
        Parameters:
        ``json`` (list): the Requests JSON list. Root parents of .json tree must be ['direction'].
        
        Return values:
        ``None``
        """
        
        for direction in json['direction']:
        
            # Scrape this direction's metadata from .json dump
            direction_name = direction['direction_name']
            
            # If direction_name doesn't already exist as Direction object, create it
            if not self.directions.get(direction_name):
                self.directions[direction_name] = Direction(direction_name, self.route_name, self.ignored_trips)
            
            # See `get_relevant_trips` docstring
            all_trips_json = direction['trip']
            relevant_trips = get_relevant_trips(all_trips_json)
                    
            # Open this direction's Direction object
            this_direction = self.directions.get(direction_name)
            
            # PART 1: Update Direction
            this_direction.update_trips(relevant_trips)
            
            # PART 2: Write count to postgres
            this_direction.write_count_to_sql(relevant_trips)
        
class Direction():
    
    """
    Direction class houses all of the Trip objects.
    """
    
    def __init__(self, direction_name, route_name, ignored_trips):
        self.pre_update_trips = {}
        self.updated_trips = {}
        self.direction_name = direction_name
        self.route_name = route_name
        self.ignored_trips = ignored_trips
    
    def update_trips(self, curr_trips_json):
        
        """
        Updates all of the Trip objects.
        
        Parameters:
        ``curr_trips_json`` (list): the Requests JSON list. Root parents of .json tree must be ['trip_id'].
        
        Return values:
        ``None``
        """
        
        new_trips, finished_trips = [], [] # for logging
        logger = logging.getLogger(__name__)
        
        # Check if current trips already exist
        for curr_trip in curr_trips_json:
            trip_id = curr_trip['trip_id']
            lat = curr_trip['vehicle']['vehicle_lat']
            long = curr_trip['vehicle']['vehicle_lon']
            vehicle_id = curr_trip['vehicle']['vehicle_id']
            location = (lat, long)
            
            # If current trip already in Direction object, update the Trip's location
            if trip_id in self.pre_update_trips:
                self.pre_update_trips[trip_id].update_location(location)
            # If current trip not already in Direction object, add it as a new Trip()
            else:
                new_trip = Trip(trip_id, vehicle_id,
                                location, self.direction_name, self.route_name)
                self.updated_trips[trip_id] = new_trip
                new_trips.append(new_trip)
                
        # Check if prior trips still currently exist
        curr_trip_ids = [x['trip_id'] for x in curr_trips_json]
        for pre_update_trip_id in self.pre_update_trips:
            trip_obj = self.pre_update_trips[pre_update_trip_id]
            trip_id = trip_obj.get()['Trip ID']
            
            # If pre-update trip is not in current trips, it may have terminated
            if trip_id not in curr_trip_ids:

                # Give the trip n attempts to rediscover the same trip_id if it does not appear in the .json temporarily
                waiting_bool = trip_obj.retry()

                # If waiting_bool is false (ie. no more retries available), end the trip
                if not waiting_bool:

                    trip_obj.end_trip()
                    del self.updated_trips[trip_id]
                    finished_trips.append(trip_obj)
                    
                    # Only write to postgres if finished_trip is not a trip beginning before runtime               
                    if trip_id not in self.ignored_trips:
                        trip_obj.write_trip_to_sql()
                
        # Update set of pre_updated trips after extracting new/finished trips
        self.pre_update_trips = self.updated_trips.copy()
        
        # Logging
        new_trip_ids = [x.get()['Trip ID'] for x in new_trips]
        if new_trip_ids:
            logger.info("New trips (%s, %s): %s" % (self.route_name, self.direction_name, new_trip_ids))
        finished_trip_ids = [x.get()['Trip ID'] for x in finished_trips]
        if finished_trip_ids:
            logger.info("Finished trips (%s, %s): %s" % \
                (self.route_name, self.direction_name, finished_trip_ids))
                        
    def write_count_to_sql(self, curr_trips):
        
        """
        Takes the amount of current trips for each route and direction, then writes it to a postgres database at the time that the count was checked.
        
        Parameters:
        ``curr_trips`` (list): current trips housed in the Direction object
        """

        trip = TripCount(
            time = dt.now(),
            count = len(curr_trips),
            direction = self.direction_name,
            route = self.route_name,
            )

        # If the current amount of trips differs from the last saved value in the database, insert new value into the database
        try: # pull the most recent trip count for this direction/route
            all_trips = TripCount.objects.filter(direction = self.direction_name, route = self.route_name).order_by('-time')
            last_count = all_trips.values()[0]['count'] 
        except IndexError: # ie. returned QuerySetis None
            last_count = -1 # write first trips to database
        finally:
            if last_count != len(curr_trips):
                trip.save()

class Trip():
    
    """
    Each trip that is added to the .json response is created as a Trip object. 
    """

    global WAIT_TIME_SEC
    TOTAL_SECONDS_TO_WAIT = 180
    MAX_RETRIES = TOTAL_SECONDS_TO_WAIT / WAIT_TIME_SEC
    
    def __init__(self, trip_id, vehicle_id, location, direction, route):
        self.trip_id = trip_id
        self.vehicle_id = vehicle_id
        self.direction = direction
        self.start_location = location
        self.end_location = self.start_location
        self.route = route
        self.start_time = dt.now()
        self.end_time = None
        self.duration = None
        self.curr_location = None
        self.retries = 0
        
    def get(self):
        
        """
        Get function to return the object's attributes in dictionary-format.
        """
        
        return { "Trip ID": self.trip_id,
                 "Vehicle ID": self.trip_id,
                 "Start location": self.start_location,
                 "End location": self.end_location,
                 "Direction": self.direction,
                 "Route": self.route,
                 "Start time": format(self.start_time),
                 "End time": format(self.end_time),
                 "Duration": format(self.duration) }

    def retry(self):

        """
        Checks how many retries have been attempted to rediscover a trip with the same trip_id. If number of retries is fewer than RETRIES_MAX, increment self.retries and return True.
        """

        if self.retries <= Trip.MAX_RETRIES:
            self.retries += 1
            return True
        else:
            return False
                 
    def update_location(self, location):
        
        """
        Updates the `end_location` as the current location. If the Trip disappears from the .json response, that current location is the last known location, and therefore the end location.
        """
        
        self.end_location = location

    def end_trip(self):
    
        """
        Once `end_trip` is called, the `duration` is evaluated as the difference between the end and start time of the trip.

        A caveat: because the program checks for trips that disappear and then reappear for TOTAL_SECONDS_TO_WAIT seconds, genuine trips must have this duration subtracted from their final recorded end time.
        """
        
        self.end_time = dt.now() - timedelta(0, Trip.TOTAL_SECONDS_TO_WAIT)
        self.duration = self.end_time - self.start_time
        
    def write_trip_to_sql(self):
        
        """ 
        Once a trip is completed, it is written to the postgres database.
        """

        fmt = "%Y-%m-%d %H:%M:%S"
        trip = CompletedTrip(
            trip_id = self.trip_id,
            vehicle_id = self.vehicle_id,
            direction = self.direction,
            route = self.route,
            start_location = self.start_location,
            end_location = self.end_location,
            start_time = dt.strftime(self.start_time, fmt),
            end_time = dt.strftime(self.end_time, fmt),
            duration = self.duration,
            )
        trip.save()
                                
def ignore_trips(response):
    
    """
    At runtime, we cannot determine the 'true' start time of any trip. As a result, all of these trips should be ignored and never written to the postgres database.
    """
    
    ignored_trips = []
    for mode in response['mode']:
        for route in mode['route']:
            for direction in route['direction']:
                for trip in direction['trip']:
                    ignored_trips.append(trip['trip_id'])
    return ignored_trips
    
def get_relevant_trips(all_trips_json):
    
    """
    The MBTA API initializes a trip with in the format: <vehicle_ID>_[0,1]. The trip is then removed once the car starts moving and renamed to format: <trip_id>_[0,1]. Initialized trips should be ignored (ie. if trip_id == vehicle_id), while only moving trips should count. This is a known bug by the MBTA.
    
    Parameters:
    ``all_trips_json`` (dict): the Requests JSON dictionary. Root parents of .json tree must be ['vehicle'].
        
    Return values:
    ``relevant_trips_json`` (list): a filtered list of only trips whose vehicle_ids do not equal their trip_ids
    """
    
    relevant_trip_ids = []
    for trip in all_trips_json:
        vehicle_id = trip['vehicle']['vehicle_id']
        stripped_trip_id = trip['trip_id'].split("_")[0]
        if vehicle_id != stripped_trip_id:
            relevant_trip_ids.append(trip['trip_id'])
    relevant_trips_json = [x for x in all_trips_json if x['trip_id'] in relevant_trip_ids]
    return relevant_trips_json
    
def get_json(url):
    
    """
    Function to query the MBTA API, or retry upon failure.
    """
    logger = logging.getLogger(__name__)
    
    while True:
        try:        
            response = requests.get(url).json()
            return response
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.debug(e)
            logger.debug("Retrying in 10 seconds...")
            time.sleep(10)
    
def init_logging(logname):
    
    """
    Function to intialize logging with certain default settings.
    
    Parameters:
    ``logname`` (str): The name of the file to which the log should be written. This is used to record each day's log individually.
    """
    
    LOGS_PATH = BASE_DIR + "/logs"
    if not os.path.exists(LOGS_PATH):
        os.mkdir(LOGS_PATH)
       
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    handler = logging.FileHandler(LOGS_PATH + "/%s.txt" % logname)
    handler.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
    handler.setFormatter(fmt)
    
    logger.addHandler(handler)
    return logger

def main():

    today = dt.today().strftime('%Y-%m-%d')
    logger = init_logging(today)

    BASE_URL = 'http://realtime.mbta.com/developer/api/v2/' \
               'vehiclesbyroutes?api_key=%s&routes=%s&format=json' % (API_KEY, ROUTES)
    
    # Ignore all trips existing at runtime because their start times cannot be determined
    ignored_trips = ignore_trips( requests.get(BASE_URL).json() )

    Routes = {}
    while True:
        
        response = get_json(BASE_URL)
        
        modes = response.get('mode')
        if not modes:
            logger.debug(e)
            apiStatus.objects.update_or_create(id = 1, defaults = {'status': 0})
            time.sleep(300)
            continue
        apiStatus.objects.update_or_create(id = 1, defaults = {'status': 1})
            
        for mode in modes:
            for route in mode['route']:
                route_name = route['route_name']

                # If route_name doesn't already exist as Route object, create it
                if not Routes.get(route_name):
                    Routes[route_name] = Route(route_name, ignored_trips)
                    
                # Open this route's Route object
                this_route = Routes.get(route_name)
        
                # Update Route
                this_route.update_route(route)
        
        # Log next iteration        
        for route_name, route_obj in Routes.items():
            for direction_name, direction_obj in route_obj.directions.items():
                logger.info("Currently active trips (%s, %s): %s" % \
                            (route_name, direction_name,
                             list(direction_obj.pre_update_trips)))
        
        logger.info("*** Starting next .json dump... ***")
        
        global WAIT_TIME_SEC
        time.sleep(WAIT_TIME_SEC)

if __name__ == "__main__":   
    
    main()