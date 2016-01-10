from celery import shared_task
import mbta_trips

@shared_task
def scrape_mbta():
	mbta_trips.main()

# Run on django-server start
scrape_mbta.delay()