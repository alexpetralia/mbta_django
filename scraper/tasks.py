from celery import shared_task
import mbta_trips

@shared_task
def scrape_mbta():
	mbta_trips.main()

scrape_mbta.delay()