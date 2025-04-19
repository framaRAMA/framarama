# Configuration

The application configuration is mainly placed into the `framarama/settings.py`
file. Please adjust settings there.

### General

#### `SECRET_KEY`

Default: temporary key

This configures a secret key which is used internally for different things. Please
do not use the default and change it to something really serect.

#### `FRAMARAMA.MODES`

Default: `server` and `frontend`

Defines which component to start: server, frontend or both. Just comment in or out
to define what to start.

Only start server component:

```
'MODES': [
    'server',
],
```

Only start frontend component:

```
'MODES': [
    'frontend',
],
```

Start both components:

```
'MODES': [
    'server',
    'frontend',
],
```

#### `FRAMARAMA.DATA_PATH`

Default: `./data/`

Should point to a directory where the application can store some data. Please
do not point this to a temporary directory. It will contain persistent data
which should not be deleted.

#### `FRAMARAMA.MEDIA_PATH`

Default: `./data/media/`

Points to a directory where some media files can be placed to read. The directory
source plugin will read the files located in this directory.

#### `FRAMARAMA.MOUNT_PATH`

Default: `/media`

To automatically provide mounted storaged in media path to use for picture collecton,
this settings points to the standard system mount path for external storages (e.g.
when using `automount`).

#### `FRAMARAMA.MOUNT_LEVEL`

Default: `1`

When `MOUNT_PATH` is configured to watch for new mounted storaged, this setting
will define how many directory levels to check (useful when external storages
will be mounted in sub-directory of `MOUNT_PATH` (e.g. `/media/username/ext-storage`).
Using level of `0` will make directories one level below `MOUNT_PATH` available,
`1` will make directories two levels below `MOUNT_PATH` as media directories (e.g.
`ext-storage`).


### Server

#### `FRAMARAMA.ADMIN_USERNAME`

Default: `admin`

Contains the username for the adminstrative user which will be created initially
when starting the server application for the first time.

#### `FRAMARAMA.ADMIN_PASSWORD`

Default: `testabc123`

The simple administrator password - please change it!

#### `FRAMARAMA.ADMIN_MAIL`

Default: `admin@some-domain.tld`

This is the mail address used for the administrative user. Currently it does not
have any effect, and do not require a valid mail address.

#### `FRAMARAMA.CONFIG_THUMBNAIL_SIZE`

Default: `[640, 480]`

When the frontend component submits the photo to the server it is also providing
a thumbnail of the current photo. If not specified the thumbnail is generated
on the server side.

#### `FRAMARAMA.CONFIG_SOURCE_UPDATE_INTERVAL`

Default: `23:00:00`

The interval (hours, minutes, seconds) when the server is updating the
photo collection and adding, removing or updating them on the server. Set the
value to `None` to disable automatic updates completely.

### Frontend

#### `FRAMARAMA.AP_NAME`

Default: `framaRAMA`

In case the wireless network connection can not be established a fallback
access point will be started with this name.

#### `FRAMARAMA.AP_PASS`

Default: `framarama`

When the fallback access point is started it is using this password.

#### `FRAMARAMA.FRONTEND_KEYSTROKES`

Default: `True`

Register key strokes to control the frontend device when connecting a keyboard
to it (e.g. activate wireless access point, reboot device, etc.).

#### `FRAMARAMA.FRONTEND_ITEM_UPDATE_INTERVAL`

Default: `00:05:00`

The inverval (hours, minutes, seconds) when the frontend is updating the
display settings and applying them.

#### `FRAMARAMA.FRONTEND_THUMBNAIL_SIZE`

Default: `[640, 480]`

This defines the resolution to use when generating a thumbnail of the
photos displayed on the frontend. It is used in the frontend application
and - when activated - when sumbmitting them to the server.

#### `FRAMARAMA.FRONTEND_APP_UPDATE_INTERVAL`

Default: `23:00:00`

Default the interval for the update check. This will only fetch the updates
but does not install them.

### Docker

When using the docker container the following environment variables can
be used. Some of them refer to the settings listed above, others are docker-only
settings.

#### `DJANGO_DEUBG`

Default: `True`

Enables or disable Django debug logging and debug mode.

#### `DJANGO_SECRET_KEY`

Default: some non-secure secret

Configures the common Django secret key. This should be set in any environment to
a secure value.

#### `FRAMARAMA_MODES`

See `FRAMARAMA.MODES`.

#### `FRAMARAMA_PORT`

Default: `8000`

Specifies the HTTP port to use for the application.

