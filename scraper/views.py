from django.shortcuts import render
from django.db.models import Avg, Sum

from .models import TripCount
from .settings.routes import ROUTES_DICT

# Create your views here.
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

		trips[route] = num_trips_first_dir + num_trips_second_dir

	# Average number of trips for each route
	num_trips = {}
	for route in ROUTES_DICT:

		avg_num_trips_query = TripCount.objects.filter(route__contains = route).values('direction').annotate(avg_num_trips = Avg('count'))
		avg_num_trips = avg_num_trips_query.aggregate(Sum('avg_num_trips'))['avg_num_trips__sum']
		avg_num_trips_rounded = "{:10.2f}".format(avg_num_trips)

		num_trips[route] = avg_num_trips_rounded.strip()

	return render(request, "scraper/index.html", locals())

def get_direction(route):

	try: 
		direction = TripCount.objects.filter(route__contains = route).order_by('-time').values('direction').first()['direction']
	except TypeError:
		direction = None

	return direction


# Get average number of trips over time
# Group by direction A, direction B