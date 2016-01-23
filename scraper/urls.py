from django.conf.urls import url
from . import views

app_name = 'scraper'
urlpatterns = [
	url(r'^$', views.index, name='index'),
	url(r'^request/$', views.http_request_trip_counts, name='request_trip_counts')
]