from celery import shared_task
import mbta_trips
import views

@shared_task
def scrape_mbta():
	mbta_trips.main()

@shared_task
def update_mbta_trips():
	mbta_trips.main()

scrape_mbta.delay()

update_mbta_trips.delay()