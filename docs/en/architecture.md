# Architecture

The application is split up into a **server component** and a **frontend
component**. Each component can be run on own devices where the frontend
component is interacting with the server component by using an API.

This way the server component can be run on a central device, which
provides all the information about the frontends used, the photos in
collections, the photo processing and more.

And the frontend component is interacting remotely with the server component
using the API provided by the server component.

On the other hand it is also possible to run both components on the
same system. In this case the server API is also used, but just from
the local device - no change in the architecture.

## Server component

The place where all the configuration is set up is the server component.
It provides an web interface which can be used to setup photo collections,
apply some further processing, configure displays to show them.

For this case the following parts can be configured:

* frames - a frame is a representation for a photo collection
* displays - a display is a physical device showing content from a frame

![Dashboard](../assets/screenshots/config-dashboard.png)

## Frontend component

This component runs on the device showing the photos. Usually a device
connected to a display/monitor.

There're also some settings which are frontend specific and which can
be managed by a web interface (e.g. device geometry, network setup, etc.).

![Frontend](../assets/screenshots/frontend-display.png)

## API

All components mentioned before provides an API. The frontend API is used
by the frontend itself, the server API is used by the frontend.

