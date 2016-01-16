# MBTA Trips

MBTA Trips is a django-powered web application which displays, for each MBTA route in Boston, the number of currently active MBTA trips and the average trip duration over a typical week. Every 10 seconds, a `celery` background worker scrapes .json data from the [MBTA Developer Portal](http://realtime.mbta.com/portal) containing information on all ongoing trips. The time at which new trips (*see footnote 1*) appear is saved, as well as when they disappear - the difference yields the trip's duration. Each completed trip is saved in a postgres database.

The primary motivation for this project was to visualize when certain routes are busiest throughout a typical week. Additionally, however, this project was designed around using as many new technologies as possible; prior to this, I had limited to no experience with any of the software listed below.

### Installation for Ubuntu Linux

While I don't anticipate anyone thoroughly replicating this installation, outlining the general steps could prove useful for those use a similar stack.
Ensure your default Python environment uses Python 2, not Python 3. You can check this by running `python` in your terminal to see which version you are using.

1. Ensure your Ubuntu distrubtion is up-to-date

`sudo apt-get update && sudo apt-get dist-upgrate`

2. Clone the repository

Within your projects folder that will house the mbta\_django repo, enter: 

`sudo git clone https://github.com/alexpetralia/mbta_django/`

3. Create a new virtual environment

I would advise against using `python3-venv` because it will default to Python 3 for package installation. This is problematic when installing `supervisord`, which requires Pyhon 2. I also advise against Anaconda's virtual environment manager with this specific project. Within the "mbta_django folder", run:

`virtualenv venv` (uses the existing "venv" directory that you cloned)

To activate your virtual environment, use `source venv/bin/activate`. I recommend creating an `alias` in your `~/.bashrc` so you don't have to type that command in each time you need to activate your virtual environment.

If you run into permissions issues, do **not** use `sudo` to circumvent them. If you do, everything you do in the virtual environment will require `sudo` as well, but enjoy getting `sudo pip` to work neatly. Rather, change ownership of the "mbta_django" folder to your username: `sudo chown -R user:group venv`. Then, retry the command above.

3. Install the postgres server

`sudo apt-get install postgresql postgresql-contrib`

4. Configure postgres and create your database

For this django web application to work, django requires certain postgres settings. They are as follows:

username: 'postgres'
password: 'password'
database_name: 'mbta'

Run the following commands:

`sudo -u postgres psql postgres`
`\password password`
`\q` (to quit)
`sudo -u postgres createdb mbta`

Accessing the interactive prompt (at least on an AWS EC2 instance) can be tricky. I used `psl postgres -h 127.0.0.1 -d mbta` to get around the the default behavior of using Unix sockets and instead use TCP/IP. Once you are in the interactive prompt, you can run your normal SQL commands (eg. "SELECT * FROM table WHERE...").

5. Install and run the rabbitmq message-broker server

I used [this](http://monkeyhacks.com/post/installing-rabbitmq-on-ubuntu-14-04) tutorial to install RabbitMQ. Those steps (slightly modified here) are:

`sudo su -c "echo 'deb http://www.rabbitmq.com/debian testing main' >> /etc/apt/sources.list"`
`sudo wget https://www.rabbitmq.com/rabbitmq-signing-key-public.asc`
`sudo apt-key add rabbitmq-signing-key-public.asc`
`sudo apt-get update && sudo apt-get install rabbitmq-server`

Your RabbitMQ server should install automatically.

6. Install python-dev

`sudo apt-get install python-dev`

This is required for the pandas module to install correctly.

7. Get your own API key

Register for an account [here](http://realtime.mbta.com/Portal/Account/Register) and request an API key.

Once you receive an API key, create an `api_key.py` in the folder mbta\_django/scraper/settings. It contains only one line: `API_KEY = <your\_api\_key\_here>`

8. Install all the remaining Python packages

`(venv)>> pip install -r requirements.txt`

Note: make sure your virtual environment is active for this step.

### Usage

###### To start the celery worker, type:
`celery -A mbta_django worker -l info`
`nohup celery -A mbta_django worker -l info &` (run in background)

###### To start the django server (available from all IPs, as opposed to just localhost), type:
`python ./manage.py runserver 0.0.0.0:8000`
`python ./manage.py runserver 127.0.0.1:8000` (to run on localhost)

You should also `chmod u+x manage.py` so you don't have to type python in everytime.

### Software used
* django
* jinja2
* postgres
* nginx (to do)
* gunicorn (to do)
* memcached (to do)
* flower (to do)
* celery
* rabbitmq
* supervisord (to do on server)
* bootstrap.css
* jquery.js
* plotly.js

### To do

**Critical**
* pandas filtering for erroneous trips
* pandas groupby only within 1 week timeframe.. "an average week"
* after hours, return 0 for no ongoing trips (ie. don't use database for these results)

**Follow-up**
* set up on server (supervisor, gunicorn, nginx, associate fqdn)
* jquery only 1 plot at a time
* Ajax refreshes every 10 seconds
* memcached for redundant queries

### License

This software is distributed under the MIT License.

#### Footnotes

1. A "new trip" is defined as a trip with a unique trip_id for that day. Often however, a trip appears with one trip\_id, disappears, then reappears seconds or minutes later with a different trip\_id, but same vehicle\_id, route and direction. For all intents and purposes, it is the same trip. The second trip is not a new trip. If a trip follows this pattern, it is considered a single trip by the program.

