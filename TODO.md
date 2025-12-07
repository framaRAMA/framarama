
## TODO
* fix saving text finishing: enabled column may no be null (DB error)
* text finishing with text rotation setting
* config settings for plugins or plugin templates (like parameters for plugins, but settings/configs)
* show which finishing failed (with error message) in finishing preview
* when updating system only run "collectstatic" when static folder contains changes
* when updating system only run "pip install" when requirements.txt changed
* admin frontend, editing for finishings, contexts, trees/treebeard, etc.
* implement new context plugin: weather (for given coordinates or picture coordinates)
* implement new context plugin: calendar (for adding current date/time/week/year info)
* database reconnect to avoid "server is gone" (on source update), https://stackoverflow.com/questions/59773675/why-am-i-getting-the-mysql-server-has-gone-away-exception-in-django
* configure email in profile and notify user on update errors
* in edit/delete forms/views check if given instance exists, if not redirect to listing pages
* make update and edit consistent (templates, views, forms, urls & pages), same logic everywhere, maybe base classes/templates
* auto mount usb sticks or access network shares (useful for "directory" source)
* is a network/USB mount helpful for filesystem source?

### templating

* templates can be defined in an own section
* templates can be used in source/finishing entities
* template consists of a item strucutre (like source/finshings)
* the entity (source/finishing) has a field "template\_id" set to the ID of template
* using templates will copy the structure to source/finishing and setting template\_id
* in case an entity (source/finishing) is a template it can not be opened to show structure
* the template has a plugin config containing all required parameters (used in structure below)
* the "enabled" flag should be represent an expression (be able to decide if item should be processed or not depending on plugin config)
* the child items can use the fields from plugin config using "local.name" as jinja variable
  (local reference to the local scope: first direct parameter, then parent parameter, then variables, then globals)


