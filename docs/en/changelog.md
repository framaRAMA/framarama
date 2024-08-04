# Changelog

## v0.5.0 - not yet released

* update to Django 4.2.14, Jinja2 3.1.3, requests 2.31.0
* create some documentation pages and add workflows
* frontend: use serializer for client API to be more robust
* frontend: configure options for auto update check and auto install
* config: wrap all plugin config values into ResultValue to be more failsafe
* config: refactor plugin storage to use django-entangled for JSON config
* config: separate models into modules
* config: replace format strings with Jinja templating for model expressions
* config: !! update all model expression to Jinja templating !!
* config: support tree structures in finishings (for grouping)
* config: switch to use Jinja2 templats in "data" plugin
* config: ignore duplicates when updating source items
* config: extend length for text in text plugin
* config: add "globals" plugin to inject global server parameters
* config: improve data_check command (generators, chunks)
* config: some dashboard improvements (media/version info, short dates, resources)
* config: start JSON exports and imports for frame configuration
* config: add query evaluation popup for sorting queries


## v0.4.0 - 2023-04-09

* frontend: refactor frontend rendering, add website renderer
* frontend: render date time in frontend's timezone
* frontend: configure/disable display status submission information
* frontend: use hit endpoint via POST and submit thumbnails
* frontend: refactor/simplify frontend capability handling
* frontend: improve quality on picture watermark
* frontend: redirect user for config changes or action to origin page
* frontend: configure timezone to use
* config: add "setup" command to create/modify initial config settings
* config: add "data_check" command to verify data model/files integrity
* config: render date time in user's timezone
* config: pages to view and edit profile, including new timezone setting
* config: integrate thumbnails in different pages (frames, displays, items)
* config: introduced frame context management (inject data to finishing, e.g. exif, geo)
* config: add update interval per frame source
* config, api: add data model, use for display item thumbnails
* config, frontend, api: refactor finishing fields into plugin config
* config: enhance dashboard and add own dashboard to display pages
* config, frontend: refactor device capability into own file
* config: extend alignment and add custom position/coordinates to merge plugin
* api: implement new display item hit endpoint via POST
* api: include version information in user-agent

## v0.3.0 - 2023-01-11

* frontend: auto-update and refresh display settings per interval
* frontend: use custom messages when saving configuration (redirect to startup page)
* frontend: refactor startup screen to own pages (can be used for different things now)
* frontend: add current revision to app version info and in display status
* frontend: activate latest item - if available - when restarting application
* frontend: introduced a new frontend API
* frontend: refactor views into own packages (setup, dashboard, system, status)
* frontend: check sudo commands before execution (avoid security warnings)
* config, frontend: refactor jobs / scheduler
* config: add new image finishing plugin
* config: replace source update with scheduler job and run auto-updates
* config: fix mapping app fields in display status
* api: refactor urls and views into own packages (config, later frontend)

## v0.2.0 - 2023-01-03

* frontend: provide buttons to check for updates and install updates
* frontend: show version information in own frontend page
* frontend: add button in display frontend page to load next item
* frontend, config: submit display status information
* frontend: keep current item in own file, not only in numbered files
* frontend: extend network check for static/LAN configurations
* frontend: fix not starting keyboard monitoring when commands missing
* config: fix setting external ID when updating items 
* api: make all endpoint read-only endpoints

## v0.1.0 - 2022-12-24

* first release version with all basic features

