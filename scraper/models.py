from django.db import models
import datetime

class CompletedTrip(models.Model):


	trip_id = models.CharField(max_length=200)
	vehicle_id = models.CharField(max_length=200)
	direction = models.CharField(max_length=200)
	route = models.CharField(max_length=200)
	start_location = models.CharField(max_length=200)
	end_location = models.CharField(max_length=200)
	start_time = models.DateTimeField()
	end_time = models.DateTimeField()
	duration = models.DurationField(default = datetime.timedelta(days=0))

	def __str__(self):
		return "%s (%s): %s" % (self.route, self.direction, self.vehicle_id)

class TripCount(models.Model):

	time = models.DateTimeField()
	count = models.IntegerField(default = 0)
	direction = models.CharField(max_length=200)
	route = models.CharField(max_length=200)

	def __str__(self):
		return "%s (%s): %s" % (self.route, self.direction, self.count)