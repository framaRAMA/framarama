# framaRAMA

<img src="common/static/common/stripes.svg" alt="stripes" style="width:100%" height="48"/>

Keep your memories alive with framaRAMA. The smart way to show your memories from
a photo collection on a digital photo frame.

Features:
* 📷 configure multiple different sets of photos
* 📺 show them on different devices
* 🤝 integrate you own photo collections
* 🎯 priorize the photos to show by meta data (e.g. date taken)
* 🪄 add make up to your photos (resize, write text, etc)
* 🍿 enjoy your memories

## 🚀 How to start

The software consists of mainly two parts:
* the **server** component, for administration and management
* the **frontend** component, for displaying the photos

Usually the server component is setup on a central device or server and
the frontend component is runningo on a device attached to a display (e.g.
a Raspberry Pi with a display connected). But it's also possible to run
both components on the same device.

### ⚙ General setup

Follow the steps below to setup both components on the same system. If you
want to separate them, see sections below.

📢 Before starting check the requirements of the components below and install
them if required.


```
git clone https://github.com/framaRAMA/framarama.git framarama
cd  framarama
mkdir data
python -m ven venv
. ./venv/bin/activate
pip install -r requirements.txt
```

Running both components on one system, set `MODES` in `framarama/settings.py`:
```
    'MODES': [
        'server',
        'frontend'
    ],
```

Start application:
```
python manage.py runserver 0.0.0.0:8000 --noreload
```

... and navigate browser to
* http://server:8000/config/ for server setup or
* http://server:8000/frontend/ for frontend setup

Enjoy!


### 🏢 Server setup

This component is the central place where all the configuration and
setup is done. It is providing a web interface to setup your photo collection
and assign them to different frames or displays.

Checkout the project as mentioned before and adjust the configuration:
```
    'MODES': [
        #'server',
        'frontend'
    ],
```

The server component depends on the following dependencies:
* ☝ `python3`, `python3-venv`, `python3-dev` - standard Python environment
* ☝ `gsfonts`, `gsfonts-other`, `fonts-liberation`, `fonts-urw-base35`, `fonts-freefont-ttf`, `fonts-freefont-otf` - fonts support, might be other packages (install them an check via `convert -list font`)
* 💡 `libmariadb3` - for external database support

After application startup you can open the server setup in the browser.

### 📺 Frontend setup

This component is used to retrieve data from the server component and
prepare the photo to display it - usually - locally on the display
connected to the device.

Checkout the project as mentioned before and adjust the configuration:
```
    'MODES': [
        #'server',
        'frontend'
    ],
```

The frontend component depends on the following dependencies:
* ☝ `python3`, `python3-venv`, `python3-dev` - standard Python environment
* 💡 `network-manager`, `dnsmasq-base` - configuring and setting up networking
* 💡 `plymouth`, `plymouth-themes`, `plymouth-x11` - create startup booting screen
* 💡 `xserver-xorg`, `xrandr|x11-server-utils`, `xinit`, `openbox`, `feh`, `imagemagick` - show pictures using graphical frontend
* 💡 `xinput` - register keystores for fallback commands

After application startup you can open the frontend setup in the browser.

## ☯ Final notes

This project was born because we all have large collection of photo but
don't regularly look at them to benefit. Maybe we have some photos
in some photo frames on walls or we have some of them in paper albums. But
how often do we look at them to enjoy the memory?

With this project you can resurrect you memories by showing your photos
on a digital photo frame.

If you like this project, please [donate](https://www.paypal.com/donate?hosted_button_id=5TDSCVP5X7QFA). Thanks!

