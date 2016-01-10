from django.conf.urls import url
from . import views

app_name = 'scraper'
urlpatterns = [
	url(r'^$', views.index, name='index'),
	url(r'^api/get_trip_times', views.get_avg_trip_time, name="get_avg_trip_time")
]