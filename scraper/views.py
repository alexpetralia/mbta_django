from django.shortcuts import render
from django.db.models import Avg, Sum

from .models import TripCount, CompletedTrip, apiStatus
from .settings.routes import ROUTES_DICT

import pandas as pd
import numpy as np

def index(request):

	# Active trips for each route
	trips = {}
	for route in ROUTES_DICT:

		# Get the direction of the most recent trip for that route
		direction = get_direction(route)

		# Get number of trips for first direction
		num_trips_first_dir = TripCount.objects.filter(route__contains = route).order_by('-time').values('count').first()['count']
	
		# Get number of trips for second direction
		num_trips_second_dir = TripCount.objects.filter(route__contains = route).exclude(direction__contains = direction).order_by('-time').values('count').first()['count']

		# Check if the MBTA API is still alive (ie. returning a .json response)
		status = apiStatus.objects.all().values().first()['status']

		# If alive, return number of trips
		trips[route] = num_trips_first_dir + num_trips_second_dir if status else 0

	# Average number of trips for each route
	num_trips = {}
	for route in ROUTES_DICT:

		avg_num_trips_query = TripCount.objects.filter(route__contains = route).values('direction').annotate(avg_num_trips = Avg('count'))
		avg_num_trips = avg_num_trips_query.aggregate(Sum('avg_num_trips'))['avg_num_trips__sum']
		avg_num_trips_rounded = "{:10.2f}".format(avg_num_trips)

		num_trips[route] = avg_num_trips_rounded.strip()

	# Average trip times
	avg_trip_times_all = get_avg_trip_times()
	filter = ('Red Line', 'Blue Line', 'Orange Line', 'Green Line B', 'Green Line C', 'Green Line D', 'Green Line E', 'Silver Line SL1', 'Silver Line SL2', 'Silver Line SL4', 'Silver Line SL5',) # can only pass routes into the dict that have associated plotly charts. if a route is passed without one, no plotly chart will display
	avg_trip_times = {k:v for k, v in avg_trip_times_all.items() if k in filter}

	return render(request, "scraper/index.html", locals())

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
	queryset = CompletedTrip.objects.all().values('start_time', 'route', 'duration')[0:100]
	df = pd.DataFrame.from_records(queryset)

	# Set dataframe index as datetime
	df = df.set_index(pd.to_datetime(df['start_time'])).drop('start_time', axis=1)

	# Get unique routes as returned by QuerySet
	routes = df['route'].unique()

	json = {}
	for route in routes:
		
		# Take route subset from the entire query
		route_df = df[df['route'] == route].copy()
		route_df.drop('route', axis=1, inplace=True)
		route_df = route_df.between_time('5:00', '2:30')

		# Remove spurious results from lognormal dist of trip lengths
		med = np.median(route_df['duration'])
		# mad = calc_mad(route_df['duration'])
		buffer_mins = med * .1
		lowerLim, upperLim = med - 3 * buffer_mins, med + 10 * buffer_mins
		route_df = route_df[(route_df['duration'] > lowerLim) & (route_df['duration'] < upperLim)]

		# Calculate minute-level durations, averaged by week
		route_df = route_df.groupby(route_df.index.weekday).resample('15Min', how=lambda x: np.sum(x) / len(x)).dropna() # np.mean does not work
		route_df = route_df.astype('<m8[ns]') # convert Ints back to timestamps

		# Reset index
		route_df = route_df.reset_index().drop('level_0', axis=1).sort_values('start_time')

		# Format as strings for json serialization
		route_df = route_df.astype(str)
		route_df['duration'] = route_df['duration'].str.split().str[-1]

		# Convert objects to list for json serialization
		x_values = list(route_df['start_time'].values)
		y_values = map(lambda x: '2016-01-01 '+x, list(route_df['duration'].values))

		# Append to dictionary
		json[route] = {'x': x_values, 'y': y_values}

	return json