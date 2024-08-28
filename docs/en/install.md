# Installation

The application is split into different components:

* the **server** component which provides all the configuration and setup of photo collections
* the **frontend** component which displays the photos

It can be setup to run both components on one system (e.g. a Raspberry Pi connected
to a display) or separately (e.g. server on a Raspberry Pi and frontend on a different
Raspberry Pi connected to a display).

For each device running one of the components you have to

* checkout the source code
* setup a Python environment
* install required Python dependencies
* install required system dependencies
* configure components to start

## General installation

As mentioned before, the components can be installed on different devices. All
of them require some common installation steps described in the next section.

After the common installation proceed with the server and/or frontend
installation steps.

### Common installation

Checking out the source code:

```
git clone https://github.com/framaRAMA/framarama.git framarama
cd framarama
```

Setup a Python environment:

```
python -m venv venv
. ./venv/bin/activate
```

Installing Python dependencies:

```
pip install -r requirements/default.txt
```

### Server installation

After completion of the general installation proceed with the follwing steps
for the server installation.

```
# Basic fonts support
sudo apt-get install gsfonts gsfonts-other
sudo apt-get install fonts-liberation fonts-urw-base35 fonts-freefont-ttf fonts-freefont-otf

# When using external MariaDB database instead of SQLite (optional)
sudo apt-get install libmariadb3
```

### Frontend installation

After completion of the general installation proceed with the follwing steps
for the frontend installation.

```
# For standalone device setup (all in one) install the following (optional)

# Network configuration/discovery support
sudo apt-get install network-manager dnsmasq-base

# Startup/shutdown screens
sudo apt-get install plymouth plymouth-themes plymouth-x11

# Displaying locally on a connected device using X server
sudo apt-get install xserver-xorg [xrandr|x11-server-utils] xinit openbox feh imagemagick

# Support for keystrokes
sudo apt-get install xinput
```

### Configuration

Basic configuration is done in `framarama/settings.py`. This contains the basic
startup configuration (server, frontend or both). Just comment the component
which should not be started:

```
'MODES': [
    'server',
    'frontend'
],
```

On first startup the database will be initialized and the initial admin user
will be created. The default credentials can also be configured (please change
them):

```
'ADMIN_USERNAME': 'admin',
'ADMIN_PASSWORD': 'testabc123',
```

Please also set a new secret key by generating them with random characters (e.g
using a password manager):

```
SECRET_KEY = 'django-insecure-@+o7lclaqfg8rkb0dp$q&eibn1b$-#-!)@ayalffvx7ztlwkf@'
```

### Starting application

To start the application use the following command:

```
python manage.py runserver --noreload
```

This will start the application and serve it using the following URLs:

* [http://server:8000/frontend/](http://server:8000/frontend/) - the frontend running on the device showing pictures
* [http://server:8000/config/](http://server:8000/config/) - the server running to configure the photo collections

