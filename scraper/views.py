from django.shortcuts import render
from django.db.models import Avg, Sum
from django.core.cache import cache
from django.conf import settings
from django.http import JsonResponse
from djangosecure.decorators import frame_deny_exempt

from .models import TripCount, CompletedTrip, apiStatus
from .settings.routes import ROUTES_DICT

import pandas as pd
import numpy as np
from datetime import datetime as dt, timedelta as td

@frame_deny_exempt
def index(request):

	###############################
	# Active trips for each route #
	###############################

	trips = get_trip_counts()

	##########################################
	# Average number of trips for each route #
	##########################################

	today = str(dt.now().date()) + "-avg_num_trips"
	avg_num_trips = cache.get(today)
	
	if avg_num_trips is None:
		avg_num_trips = {}
		for route in ROUTES_DICT:
			avg_num_trips_query = TripCount.objects.filter(route__contains = route).values('direction').annotate(avg_num_trips = Avg('count'))
			avg_num_trips_sum = avg_num_trips_query.aggregate(Sum('avg_num_trips'))['avg_num_trips__sum']
			avg_num_trips_rounded = "{:10.2f}".format(avg_num_trips_sum)
			avg_num_trips[route] = avg_num_trips_rounded.strip()
		cache.set(today, avg_num_trips, settings.TIMEOUT)

	######################
	# Average trip times #
	######################

	avg_trip_times_all, range_min, range_max = get_avg_trip_times()
	filter = ('Red Line', 'Blue Line', 'Orange Line', 'Green Line B', 'Green Line C', 'Green Line D', 'Green Line E', 'Silver Line SL1', 'Silver Line SL2', 'Silver Line SL4', 'Silver Line SL5',) # can only pass routes into the dict that have associated plotly charts. if a route is passed without one, no plotly chart will display
	avg_trip_times = {k:v for k, v in avg_trip_times_all.items() if k in filter}

	##########
	# Return #
	##########

	return render(request, "scraper/index.jinja", locals())

def get_direction(route):

	try: 
		direction = TripCount.objects.filter(route__contains = route).order_by('-time').values('direction').first()['direction']
	except TypeError:
		direction = None

	return direction

def calc_mad(data):

    return np.median(np.absolute(data - np.median(data)))

def get_avg_trip_times():

	# Convert QuerySet to pd.DataFrame
	queryset = CompletedTrip.objects.all().values('start_time', 'route', 'duration')
	df = pd.DataFrame.from_records(queryset)

	# Set dataframe index as datetime
	df = df.set_index(pd.to_datetime(df['start_time'])).drop('start_time', axis=1)

	# Get unique routes as returned by QuerySet
	routes = df['route'].unique()

	# Before expensive calculation, check if it was already computed today and stored in Memcached
	today = str(dt.now().date())
	memcached_response = cache.get(today)
	if memcached_response is not None:
		return memcached_response

	json, range_min_list, range_max_list = {}, {}, {}
	for route in routes:
		
		# Take route subset from the entire query
		route_df = df[df['route'] == route].copy()
		route_df.drop('route', axis=1, inplace=True)
		route_df = route_df.between_time('5:00', '2:30')

		# Remove spurious results from lognormal dist of trip lengths
		med = np.median(route_df['duration'])
		# mad = calc_mad(route_df['duration'])
		buffer_mins = med * .1
		lowerLim, upperLim = med - 3 * buffer_mins, med + 8 * buffer_mins
		route_df = route_df[(route_df['duration'] > lowerLim) & (route_df['duration'] < upperLim)]

		# Calculate average duration over an average day, resampled every 15 minutes
		route_df = route_df.resample('15Min', how=lambda x: np.sum(x) / len(x)).dropna()
		route_df['qtr_hour'] = route_df.index.map(lambda x: x.strftime("%H:%M:%S")) # pd.TimeGroup(freq='15Min') implicitly includes DayGrouper
		route_df = route_df.groupby('qtr_hour')['duration'].apply(np.mean) # cannot use apply on entire df; must force on a column
		route_df = route_df.sort_index()

		# Place early-morning hours at end of dataframe (plotly order matters)
		route_df = pd.concat([route_df.ix['06:00:00':], route_df.ix[:'02:15:00']])

		# Calculate range values for plotly.js plots in Unix time
		# Must use fixed range because plotly.js does not allow (auto, fixed) format - both must be fixed or auto. For our plotly.js graphs, we need conditional fixed max (ie. 55 mins or less) and auto min
		range_min_delta = route_df.min()
		range_min = dt(2016, 1, 1) + range_min_delta - td(minutes=2)
		unix_range_min = int(range_min.strftime("%s"))*1000

		# If max duration is too low (ie. < 35 mins) or too high (ie. > 55 minutes), override with fixed limits
		range_max_delta = route_df.max()
		range_max = dt(2016, 1, 1) + range_max_delta
		range_max_unix = int(range_max.strftime("%s"))*1000
		unix_lims = (1451626500000, 1451627700000) # Unix equivalent of 35 and 55 minutes
		if range_max_unix < unix_lims[0]: 
			unix_range_max = unix_lims[0]
		elif range_max_unix > unix_lims[1]: 
			unix_range_max = unix_lims[1]
		else: 
			unix_range_max = range_max_unix

		# Format as strings for json serialization
		route_df = route_df.astype(str)
		route_df = route_df.str.split().str[-1]

		# Convert objects to list for json serialization (show early morning hours on next day)
		x_values = map(lambda x: '2016-01-01 '+x if x >= "06:00:00" else '2016-01-02 '+x, list(route_df.index.values))
		y_values = map(lambda x: '2016-01-01 '+x, list(route_df.values))

		# Append to dictionary
		json[route] = {'x': x_values, 'y': y_values}
		range_min_list[route] = unix_range_min
		range_max_list[route] = unix_range_max

	cache.set(today, (json, range_min_list, range_max_list), settings.TIMEOUT)

	return json, range_min_list, range_max_list

def get_trip_counts():

	# Check if the MBTA API is still alive (ie. returning a .json response)
	status = apiStatus.objects.all().values().first()['status']

	# [THIS SQL IS ACTUALLY SLOWER THAN MULTIPLE QUERIES]
	# from django.db import connection
	# sql = ("SELECT route, SUM(count) as count FROM ( "
	# 			"SELECT DISTINCT ON (direction, route) route, count "
	# 			"FROM scraper_tripcount "
	# 			"ORDER BY route, direction, time DESC ) as t1 "
	# 		"GROUP BY route")
	# cursor = connection.cursor()
	# cursor.execute(sql)
	# trips = { str(k):int(v) if status else 0 for k, v in cursor.fetchall() }

	trips = {}
	for route in ROUTES_DICT:

		# Get the direction of the most recent trip for that route
		direction = get_direction(route)

		# Get number of trips for first direction
		num_trips_first_dir = TripCount.objects.filter(route__contains = route).order_by('-time').values('count').first()['count']
	
		# Get number of trips for second direction
		num_trips_second_dir = TripCount.objects.filter(route__contains = route).exclude(direction__contains = direction).order_by('-time').values('count').first()['count']

		# If alive, return number of trips
		trips[route] = num_trips_first_dir + num_trips_second_dir if status else 0

	return trips

def http_request_trip_counts(request):
	
	trips = get_trip_counts()

	return JsonResponse(trips)