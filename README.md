# framaRAMA

## Frontend

* based on templates using Django with Jinja2 templates
* make use of MDB with fontawesome
  https://mdbootstrap.com/docs/standard/tools/design/gradients/

## Backend

### Install

#### Project setup
```
git clone https://some.repo/framarama.git
```

#### Dependency setup
```
python3 -m venv venv
. ./venv/bin/activate
pip install -r requirements.txt
```

... or manually:
```
pip install jsonpickle                              # store obj as JSON (renderer)
pip install django                                  # Django
pip install Jinja2                                  # Templating
pip install mysqlclient                             # Database storage
pip install gunicorn daphne                         # Webserver flavours
pip install djangorestframework drf-extensions      # DRF
pip install pyyaml uritemplate                      # DRF OpenAPI / Schemas
pip install django_apscheduler                      # Scheduling
```
http:
```
pip install requests
```
data:
```
pip install magic
pip install jsonpath-python
```
finishing:
```
pip install Wand
pip install requests
```

#### Database setup

```
. ./venv/bin/activate
ln -s /tmp/db.sqlite3 db.sqlite3    # required if working in a read-only filesystem
python3 manage.py migrate
```

#### User setup

Create admin account:
```
python manage.py createsuperuser --username=admin --email=user@somedomain.tld
```

Create User account in admin frontend:
http://somehost:8000/admin/auth/user/add/

#### Other stuff

Dump data and import into different database:
```
python3 manage.py dumpdata config > config.json
# change database in settings.py to new setup
python3 manage.py migrate
python3 manage.py loaddata config.json
```

Reset migrations and recreate them from current database structure:
* mysqldump databases
* delete data from django_migrations tables
* move or delete files in migrations folders
```
delete from django_migrations;
python manage.py migrate --fake
python manage.py makemigrations config
python manage.py makemigrations frontend
python manage.py makemigrations api
# admin, auth, config, contenttypes, frontend, sessions
python manage.py migrate --fake-initial frontend
python manage.py migrate --fake-initial
```

Generate API schema:
```
python manage.py generateschema
```

### Project setup

```
django-admin startproject framarama framarama
python3 manage.py startapp config
python3 manage.py startapp api
python3 manage.py startapp frontend
```

### Configuration `config`

settings.py:
* ALLOWED_HOSTS add `*` (allow remote access to all hosts)
* INSTALLED_APP add "config"
* TEMPLATES / BACKEND set to Jinja
* TEMPLATES / OPTION / environment to Jinja environment file
* DATABASES add "default" (MySQL) and "frontend" database (SQLite)
* LOGIN_URL = '/config/accounts/login'
* LOGIN_REDIRECT_URL set to '/config/'
* LOGOUT_REDIRECT_URL set to LOGIN_URL

Create files:
* jinja.py environment file to configure Jinja environment

Create admin account:
```
python manage.py createsuperuser --username=admin --email=info@ollisnet.de
```

### Startup

Development server provided with Django:
```
python3 manage.py runserver
```

WSGI startup using gunicorn (prefered)
```
gunicorn framarama.wsgi:application -b 0.0.0.0:8000
```

ASGI startup using daphine
```
daphne framarama.asgi:application -b 0.0.0.0
```

### Models

Edit `config/models.py` and update schema:
```
python3 manage.py makemigrations
python3 manage.py migrate
```

## Architecture

* server web application to configure frames and displays (config)
* display web application to configure device showing a display (viewer)

### Server / config app

The server application can be used to configure frames and displays.

#### Frames

A frame is a representation of a collection of images. It contains:
* basic properties (name, description)
* several sources to retrieve image collections
* weightning definition to define image order
* processing queue to generate image to be displayed

#### Displays

A display is a device which can show an image. It contains:
* configuration how to display images (feh, fim, X.org, etc.)
* frame assignment
* display settings (size, image change time, display off time, ...)

### Display / viewer app

The display applcation is running on the client to show image
collections. It is using a specific display which is configured
in the server application.

# Other

* https://editsvgcode.com/ - SVN Editor online with preview
* https://favicon.io/favicon-converter/ - favicon generator online

