# MBTA Live

**<a href="http://bostonmbta.info/" target="_blank">You can view this project live here.</a>**

MBTA Live is a django-powered web application which displays, for each MBTA route in Boston, the number of currently active MBTA trips and the average trip duration over a typical week. Every 10 seconds, a `celery` background worker scrapes .json data from the <a href="http://realtime.mbta.com/portal" target="_blank">MBTA Developer Portal</a> containing information on all ongoing trips. The time at which new trips (*see footnote 1*) appear is saved, as well as when they disappear - the difference yields the trip's duration. Each completed trip is saved in a postgres database.

The primary motivation for this project was to visualize when certain routes are busiest throughout a typical week. Additionally, this project was designed around using as many new technologies as possible as a learning experience.

### Installation for Ubuntu Linux

While I don't anticipate anyone thoroughly replicating this installation, outlining the general steps could prove useful for those with a similar stack.
Ensure your default Python environment uses Python 2, not Python 3. You can check this by running `python` in your terminal to see which version you are using.

**1. Ensure your Ubuntu distribution is up-to-date**

`sudo apt-get update && sudo apt-get dist-upgrade`

**2. Clone the repository**

Within your projects folder that will house the mbta\_django repo, enter: 

`sudo git clone https://github.com/alexpetralia/mbta_django/`

**3. Create a new virtual environment**

I would advise against using `python3-venv` because it will default to Python 3 for package installation. This is problematic when installing `supervisor`, which requires Pyhon 2. I also advise against Anaconda's virtual environment manager with this specific project. Within the "mbta_django folder", run:

`virtualenv venv` (uses the existing "venv" directory that you cloned)

To activate your virtual environment, use `source venv/bin/activate` from your cloned mbta_django root folder. I recommend creating an `alias` in your `~/.bashrc` so you don't have to type that command each time you need to activate your virtual environment.

If you run into permissions issues, do **not** use `sudo` to circumvent them. If you do, everything you do in the virtual environment will require `sudo` as well, which you don't want. Rather, change ownership of the "mbta_django" folder to your username: `sudo chown -R user:group venv`. For example, I used `sudo chown -R alexpetralia:alexpetralia venv`. Then, retry the command above.

**4. Install the postgres server**

`sudo apt-get install postgresql postgresql-contrib`

**5. Configure postgres and create your database**

For this django webapp to work, django requires certain postgres settings. They are:

username: 'postgres'<br />
password: 'password'<br />
database_name: 'mbta'<br />

Run the following commands:

`sudo -u postgres psql mbta` (to enter the interactive prompt)<br />
`\password password`<br />
`\q` (to quit)<br />
`sudo -u postgres createdb mbta`<br />

If accessing the interactive prompt does not work for you, try using TCP/IP instead of Unix sockets. To do so, type `psl postgres -h 127.0.0.1 -d mbta` (where `mbta` is the name of your database) to get around the the default connecting behavior. Once you are in the interactive prompt, you can run your normal SQL commands (eg. `SELECT * FROM table WHERE...`). Don't forget a `;` to terminate your commands!

**6. Install and run the RabbitMQ server**

I used <a href="http://monkeyhacks.com/post/installing-rabbitmq-on-ubuntu-14-04" target="_blank">this</a> tutorial to install RabbitMQ. Those steps (slightly modified here) are:

`sudo su -c "echo 'deb http://www.rabbitmq.com/debian testing main' >> /etc/apt/sources.list"`<br />
`sudo wget https://www.rabbitmq.com/rabbitmq-signing-key-public.asc`<br />
`sudo apt-key add rabbitmq-signing-key-public.asc`<br />
`sudo apt-get update && sudo apt-get install rabbitmq-server`<br />

Your RabbitMQ server should install automatically.

**7. Install python-dev**

`sudo apt-get install python-dev`

This is required for the pandas module to install correctly.

**8. Get your own API key**

Register for an account <a href="http://realtime.mbta.com/Portal/Account/Register" target="_blank">here</a> and request an API key.

Once you receive an API key, create an `api_key.py` in the folder mbta\_django/scraper/settings. It contains only one line: `API_KEY = <your_api_key_here>`

**9. Install all the remaining Python packages**

`(venv)>> pip install -r requirements.txt`

Note: make sure your virtual environment is active for this step.

**10. Verify the celery daemon runs correctly**

`(venv)>> celery -A mbta_django worker -l info`

**11. Test that django runs on the development server**

First, make `manage.py` executable by issuing `chmod u+x manage.py`. Then, in the repo's root folder, run in your virtual environment:

`(venv)>> ./manage.py makemigrations` (to issue database commands) <br />
`(venv)>> ./manage.py migrate` (to commit database migrations) <br />
`(venv)>> ./manage.py runserver` (to run the server; use `runserver 0.0.0.0:8000` to make the app visible from other machines on the network) <br />

You should now see the mbta_django app running locally at `http://localhost:8000`.

**12. Prepare django for production server**

In a production environment, we'll use nginx (webserver) to serve static files and uWSGI (application server) to serve the django app. For nginx to easily find the static files in one location, django offers a command to conveniently put them in one. From your app root, type:

`(venv)>> python ./manage.py collectstatic`

This will copy all of your app's static files and any other files included under django's STATIC\_DIRS into the STATIC\_ROOT.

**13. Install and configure nginx**

`sudo apt-get install nginx`

Once nginx is installed, you should find the default "Welcome" page at `http://localhost:80`, or more simply, `localhost`. Currently, nginx is showing the default webpage, whose settings are located in `/etc/nginx/nginx/sites-enabled`. You can `sudo rm -rf default` to remove this default file as it can mask errors.

Next, we need to point nginx to mbta_django's `nginx.conf`. To do so, using your own path below, run:

`cd /etc/nginx/nginx/sites-enabled`<br />
`sudo ln -s /path/to/cloned/repo/mbta_django/nginx.conf mbta_django.conf`

Now, update `mbta_django/nginx.conf` (ie. the nginx.conf you cloned) to update the paths for your machine's paths:

* Change `server unix:///home/alexpetralia/Projects/mbta_django/run/uwsgi.sock` to `server unix:///path/to/cloned/repo/mbta_django/run/uwsgi.sock`
* Change `alias /home/alexpetralia/Projects/mbta_django/static` to `alias /path/to/cloned/repo/mbta_django/static`
* Change `uwsgi_pass  unix:/home/alexpetralia/Projects/mbta_django/run/uwsgi.sock` to `uwsgi_pass  unix:/path/to/cloned/repo/mbta_django/run/uwsgi.sock`

Finally, edit to `/etc/nginx/nginx.conf`. Nginx needs to be run with the same user as uWSGI, so change the `user` field from `www-data` to your username. If you forget to do this, you will see a permissions issue in the error logs when connecting to the Unix socket.

For now, nginx should show an error because it is trying to connect to the uWSGI socket that's not yet configured. We'll set that up next.

If you are having errors with nginx (eg. 503 Bad Gateway), check the log via `tail -5 /var/log/nginx/error.log`. You can restart the server using `sudo service nginx restart`. If you run into permissions issues, verify again that your cloned repo uses `chmod -R 755 <dirname>` permissions.

**14. Install memcached**

`sudo apt-get install memcached`

**15. Configure uWSGI**

uWSGI requires a specific set of parameters to start properly, so this is often done using shell start script. In the cloned repo, this file is `uwsgi_ctl`. Ensure that this file is an executable using `chmod u+x uwsgi_ctl`.

Within `uwsgi_ctl`, we need to update the path for your specific machine. Change `MAIN_DIR=/home/alexpetralia/Projects/mbta_django` to `MAIN_DIR=/path/to/cloned/repo`

We want to test if this `uwsgi_ctl` file runs correctly. Currently, it's configured to issue a socket file `run/uwsgi.sock` that nginx can connect to. To have it run over HTTP, uncomment `--http 127.0.0.1:8000` and comment out `--socket ${SOCKFILE}`. Then in your virtual environment, test if the uWSGI server will run.

`(venv)>> ./uswgi_ctl`

Once you're done, we can test if uWSGI works with nginx. Recomment the `--http` line and uncomment out the ``--socket`` line. 

Run ``./uwsgi_ctl`` again and navigate to `localhost` (your nginx server should be running in the background by default; it will now see the uWSGI socket). **Your entire web app should now load correctly.** If there are errors, remember to investigate in your app root's `logs/mbta_uwsgi.log`.

**16. Install and configure supervisor**

Run `sudo apt-get install supervisor`.

The webapp fundamentally runs on two processes: (1) the django application running via UWSGI and (2) the celery background worker that scrapes data from the MBTA Developer's API. Supervisor watches these processes and restarts them if there any failures - essentially it is a safety net for your processes in a production environment.

The supervisor configuration is located in your app root's `/mbta_django/supervisor.conf`. There are *nine* (9) absolute paths here which need to be changed for your specific setup. There is also the `user` field. You must change this to your username (critical, otherwise supervisor will not have the correct permissions to access `mbta_django/uwsgi.sock`).

Finally, supervisor needs to know where to find this configuration file. To do so, run:

`cd /etc/supervisor/conf.d`<br />
`sudo ln -s /path/to/cloned/repo/mbta_django/supervisor.conf mbta_django.conf`

Restart supervisor: `sudo service supervisor restart`. If you would like to control your supervisor from the browser, add this to `/etc/supervisor/supervisor.conf` and restart the process:

```
[inet_http_server]
port = 9001
username = username
password = password
```

Now, if your server reboots or your processes die, supervisor should start on boot and automatically restart dead processes.

**17. Protect settings for future git cloning**

If you need to update your repo to the most recent version, you'll run `git pull`.

However, because you updated a couple of files with your specific machine's settings (ie. the absolute pathnames), you'll want git to ignore those and keep your version of those files. Therefore, before running `git pull`, first run:

`git stash` in  "mbta_django/mbta_django" (ie. where your `settings.py` is located)

You may have to `git add <file>` specifically to a file to make sure it is ignored. After, run `git pull`. Finally, to revert to your pre-updated config settings, go back to both folders and enter `git stash pop`.

### Usage

###### To start supervisor processes, type:
`sudo supervisorctl restart all`

###### To check the status of your supervisor processes, type:
`sudo supervisorctl status`

### Debugging individual processes

###### To start the celery worker, type:
`(venv)>> celery -A mbta_django worker -l info`<br />
`(venv)>> nohup celery -A mbta_django worker -l info &` (to run in background)<br />

###### To start the django development server, type:
`(venv)>> ./manage.py runserver 127.0.0.1:8000`

###### To start the uWSGI application server, type:
`(venv)>> ./uwsgi_ctl`
Note: ensure that `uwsgi_ctl` is configured to use `--http` and not `--socket`.

###### To restart the nginx webserver, type:
`sudo service nginx restart`

###### To restart supervisor, type:
`sudo service supervisor restart`

### Software stack
* **Web framework:** Django
* **Templating language:** Jinja2
* **Database:** Postgres
* **Webserver:** nginx
* **Application server:** uWSGI
* **Caching system:** Memcached
* **Task monitor:** Flower (to do)
* **Website analytics:** Google Analytics
* **Task manager:** Celery
* **Message broker:** RabbitMQ
* **Messaging library**: Kombu
* **Process manager:** Supervisor
* **CSS framework:** Bootstrap 3
* **JS framework:** jquery.js (Ajax)
* **JS plotting library:** plotly.js (responsive)

### To do

**Critical**
* load testing

**Follow-up**
* apiStatus should be using a message queue Publisher/Subscriber model (Kombu) or Unix socket instead of postgres
* add more routes (?)
* jquery only 1 plot at a time (?)

### License

This software is distributed under the <a href="https://opensource.org/licenses/MIT" target="_blank">MIT License</a>.

### Contact

If you have any questions, bug reports or any other feedback, you can contact the author at <a href="http://alexpetralia.com/contact/" target="_blank">his personal website</a>.

#### Footnotes

1. A "new trip" is defined as a trip with a unique trip_id for that day. Often however, a trip appears with one trip\_id, disappears, then reappears seconds or minutes later with a different trip\_id, but same vehicle\_id, route and direction. For all intents and purposes, it is the same trip. The second trip is not a new trip. If a trip follows this pattern, it is considered a single trip by the program.

