# Sources

The source plugins can be used to build the photo collection for a frame.

All configured source steps can use a given plugin and will receive input
data (generated from a previous step) and provide output data (which is
handed over to the next plugin).

The generated output data can have a name. Previously generated output data
with the same name will overwrite existing data. But using different names
can help to separate them in logical steps.

Common fields for all source steps:

* **title** - a short title
* **description** - brief description what it does
* instance - optional instance name
* data_in - if required provide input data
* mime_in - if auto detection fails specify the mime type of input data
* merge_in - flag to merge all input data into one input data before processing
* data_out - if required provide name for output data
* mime_out - if required provide mime type of output data
* loop_out - flag if following steps should loop over generated output data

## data

Manipulates a given input data (e.g. a CSV list) and convert/filter/strip data
from it to generate new output data.

Fields:

* filter_in - if data should be filtered provide a filter expression
* template_out - if output data should be transformed provide a template

## http

Retrieve input data by fetching a given URL (which could be a remote CSV
data file) to provide it as new output data.

Fields:

* url_formatted - enable in case you use tokens, placeholders or variables
* **url** - the URL to fetch
* method - the method to use (GET, POST, etc.)
* body_formatted - enable in case you use tokens, placeholders or variables
* body - the body to submit in request
* body_type - the content type to set (e.g. `application/x-www-form-urlencoded`)
* auth_user - username for basic authentication
* auth_pass - password for basic authentication
* **headers** - additional list of headers as JSON structure

