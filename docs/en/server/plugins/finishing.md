# Finishing

The finishings define the post processing of the item before showing it.
It can be use to scale, convert or annotate the image.

Common fields for all finishings:

* **title** - a short title
* image_in - name of input image
* image_out - name of output image
* enabled - enables the use of this finishing

## image

Loads an image from the given URL.

Fields:

* **url** - the URL to load images from (files, URLs, bytes)

## resize

Resize the image to given geometry.

Fields:

* resize_x - the target X (width) resolution in pixels
* resize_y - the target Y (height) resolution in pixels
* keep_aspect - flag to keep aspect (only use maximum resolution of X or Y)

## text

Add text to the image using a given font style (e.g. weight, size).

Fields:

* **font** - the name of font to use (e.g. Helvetica)
* weigth - the weight to use (e.g. 400)
* **text** - text to add
* **size** - size to use
* **color_stroke** - color for text
* stroke_width - width for strokes
* color_fill - the fill color
* color_alpha - alpha/transparency of the color
* **alignment** - text alignment
* **start_x** - X position to start with text
* **start_y** - Y position to start with text
* border - border size to use
* border_radius - size of rounded corners
* border_alpha - alpha/transparency of the color
* border_padding - spacing between text and border

## shape

Draw a simple shape (e.g. lines, rectangles)

Fields:

* **shape** - the shape to draw
* color_stroke - color to use for drawing
* color_fill - the fill color
* color_alpha - alpha/transparency of the color
* start_x - X position to start with shape
* start_y - Y position to start with shape
* size_x - the target horizontal size defining the ending point
* size_y - the target vertical size defining the ending point

## transform

Transform the image using a predefined filter.

Fields:

* **type** - the type of the transformation (e.g. blur)
* factor - the factor for the transformation

## merge

Merge images to one image using given merge strategy.

Fields:

* **alignment** - The alignment to use when merging
* left - when using coordinates use this as horizontal position
* top - when using coordinates use this as vertical position

