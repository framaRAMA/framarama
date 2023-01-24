import re
import math
import logging
import requests
import importlib

from django.core.paginator import Paginator

from framarama.base.utils import Filesystem
from config import models
from config.plugins import FinishingPluginRegistry
from config.utils import context


logger = logging.getLogger(__name__)


class Context:
    DEFAULT_IMAGE_NAME = 'default'

    def __init__(self, display, frame, item, finishings, adapter):
        self._display = display
        self._frame = frame
        self._item = item
        self._finishings = finishings
        self._image_data = {}
        self._adapter = adapter
        self._context = context.Context()

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def get_display(self):
        return self._display
    
    def get_frame(self):
        return self._frame
    
    def get_item(self):
        return self._item

    def get_finishings(self):
        return self._finishings

    def get_adapter(self):
        return self._adapter

    def get_image(self):
        return self._image_data[Context.DEFAULT_IMAGE_NAME]
    
    def set_image(self, image):
        self._image_data[Context.DEFAULT_IMAGE_NAME] = image

    def get_images(self):
        return self._image_data
    
    def get_image_data(self, image_name):
        return self._image_data[image_name] if image_name in self._image_data else None
    
    def set_image_data(self, image_name, image):
        self._image_data[image_name] = image

    def set_resolver(self, name, resolver):
        self._context.set_resolver(name, resolver)

    def evaluate(self, expr):
        return self._context.evaluate(expr)

    def evaluate_model(self, model):
        return self._context.evaluate_model(model)

    def close(self):
        _names = list(self._image_data.keys())
        for _name in _names:
            _images = self._image_data[_name].get_images()
            for _image in _images:
                self._adapter.image_close(_image)
            del self._image_data[_name]


class Processor:

    def __init__(self, context):
        self._context = context
        self._instances = {}
        self._watermark = []
        self.set_watermark('ribbon', None, None)

    def set_watermark(self, style, shift, scale):
        if style == 'ribbon':
            _scale = scale if scale else 6
            _shift = shift if shift else 15
            self._watermark = self._watermark_ribbon(self._context.get_frame(), _shift, _scale)
        elif style == 'hbars':
            _scale = scale if scale else 4
            _shift = shift if shift else 4
            self._watermark = self._watermark_hbars(self._context.get_frame(), _shift, _scale)
        elif style == 'vbars':
            _scale = scale if scale else 4
            _shift = shift if shift else 4
            self._watermark = self._watermark_vbars(self._context.get_frame(), _shift, _scale)

    def _watermark_ribbon(self, frame, shift, scale):
        _factor = "images['default']['width']*0.01"
        _shift = _factor + "*" + str(math.sqrt(int(shift)**2*2))
        _scale = _factor + "*" + str(math.sqrt(int(scale)**2/2)) + "*1.1"  # 10% saftey factor
        _size_x = f"{_factor}*{scale}+{_factor}*{shift}"
        _size_y = f"{_factor}*{scale}"
        _finishings = [{
            'plugin': 'image', 'image_out': 'line', 'plugin_config': {
                'url': './static/common/stripes.png',
                'color_alpha': 70,
            }
        }, {
            'plugin': 'resize', 'image_in': 'line', 'image_out': 'line', 'plugin_config': {
                'resize_x': "{" + _size_x + "}",
                'resize_y': "{" + _size_y + "}",
            }
        }, {
            'plugin': 'transform', 'image_in': 'line', 'image_out': 'linetl', 'plugin_config': {
                'mode': 'rotate',
                'factor': '-45',
            }
        }, {
            'plugin': 'transform', 'image_in': 'line', 'image_out': 'linebr', 'plugin_config': {
                'mode': 'rotate',
                'factor': '135',
            }
        }, {
            'plugin': 'merge', 'image_in': 'default linetl', 'plugin_config': {
                'alignment': 'coords',
                'left': "{-" + _scale + "}",
                'top': "{-" + _scale + "}",
            }
        }, {
            'plugin': 'merge', 'image_in': 'default linebr', 'plugin_config': {
                'alignment': 'coords',
                'left': "{" + _scale + "+image['width']-images['linebr']['width']}",
                'top': " {" + _scale + "+image['height']-images['linebr']['height']}",
            }
        }]
        return [models.Finishing(frame=frame, enabled=True, **_config) for _config in _finishings]

    def _watermark_hbars(self, frame, shift, scale):
        _factor = "images['default']['width']*0.01"
        _shift = _factor + "*" + str(shift)
        _size_x = f"images['default']['width']"
        _size_y = f"{_factor}*{scale}"
        _finishings = [{
            'plugin': 'image', 'image_out': 'line', 'plugin_config': {
                'url': './static/common/stripes.png',
                'color_alpha': 70,
            }
        }, {
            'plugin': 'resize', 'image_in': 'line', 'image_out': 'linet', 'plugin_config': {
                'resize_x': "{" + _size_x + "}",
                'resize_y': "{" + _size_y + "}",
            }
        }, {
            'plugin': 'transform', 'image_in': 'linet', 'image_out': 'lineb', 'plugin_config': {
                'mode': 'rotate',
                'factor': '180',
            }
        }, {
            'plugin': 'merge', 'image_in': 'default linet', 'plugin_config': {
                'alignment': 'coords',
                'left': "0",
                'top': "{" + _shift + "}",
            }
        }, {
            'plugin': 'merge', 'image_in': 'default lineb', 'plugin_config': {
                'alignment': 'coords',
                'left': "0",
                'top': "{-" + _shift + "+image['height']-images['lineb']['height']}",
            }
        }]
        return [models.Finishing(frame=frame, enabled=True, **_config) for _config in _finishings]

    def _watermark_vbars(self, frame, shift, scale):
        _factor = "images['default']['width']*0.01"
        _shift = _factor + "*" + str(shift)
        _size_x = f"images['default']['height']"
        _size_y = f"{_factor}*{scale}"
        _finishings = [{
            'plugin': 'image', 'image_out': 'line', 'plugin_config': {
                'url': './static/common/stripes.png',
                'color_alpha': 70,
            }
        }, {
            'plugin': 'resize', 'image_in': 'line', 'image_out': 'line', 'plugin_config': {
                'resize_x': "{" + _size_x + "}",
                'resize_y': "{" + _size_y + "}",
            }
        }, {
            'plugin': 'transform', 'image_in': 'line', 'image_out': 'linel', 'plugin_config': {
                'mode': 'rotate',
                'factor': '-90',
            }
        }, {
            'plugin': 'transform', 'image_in': 'line', 'image_out': 'liner', 'plugin_config': {
                'mode': 'rotate',
                'factor': '90',
            }
        }, {
            'plugin': 'merge', 'image_in': 'default linel', 'plugin_config': {
                'alignment': 'coords',
                'left': "{" + _shift + "}",
                'top': "0",
            }
        }, {
            'plugin': 'merge', 'image_in': 'default liner', 'plugin_config': {
                'alignment': 'coords',
                'left': "{-" + _shift + "+image['width']-images['liner']['width']}",
                'top': "0",
            }
        }]
        return [models.Finishing(frame=frame, enabled=True, **_config) for _config in _finishings]

    def process(self):
        _item = self._context.get_item()
        if not _item.url:
            return None
        _display = self._context.get_display()
        if not _display.enabled:
            return None
        _frame= self._context.get_frame()
        if not _frame.enabled:
            return None
        logger.info("Finishing {}".format(_item))
        _adapter = self._context.get_adapter()
        self._context.set_image(_adapter.image_open(_item.url))
        for _finishing in list(self._context.get_finishings()) + self._watermark:
            if not _finishing.enabled:
                continue
            logger.info("Processing finishing {}".format(_finishing))
            _plugin = FinishingPluginRegistry.get(_finishing.plugin)
            if not _plugin:
                logger.warn("Unknown plugin {} - skipping.".format(_finishing.plugin))
                continue
            _finishing = _plugin.create_model(_finishing)

            if _finishing.image_in:
                _images_in = _finishing.get_image_names_in()
            else:
                _images_in = [Context.DEFAULT_IMAGE_NAME]
            
            if _finishing.image_out:
                _images_out = _finishing.get_image_names_out()
            else:
                _images_out = [Context.DEFAULT_IMAGE_NAME]

            _image_metas = {}
            for _image_name, _image in self._context.get_images().items():
                _image_metas[_image_name] = _adapter.image_meta(_image)

            _image = ImageContainer()
            for i, _name in enumerate(_images_in):
                _image_in = self._context.get_image_data(_name)
                if not _image_in:
                    logger.warn('Image {} does not exists - ignoring.'.format(_name))
                    continue
                if _name not in _images_out:
                    _image_in = _adapter.image_clone(_image_in)
                _image.add_images(_image_in.get_images())

            self._context.set_resolver('display', context.ObjectResolver(_display))
            self._context.set_resolver('frame', context.ObjectResolver(_frame))
            self._context.set_resolver('item', context.ObjectResolver(_item))
            self._context.set_resolver('var', context.MapResolver({}))
            self._context.set_resolver('env', context.EnvironmentResolver())
            self._context.set_resolver('image', context.MapResolver(_adapter.image_meta(_image)))
            self._context.set_resolver('images', context.MapResolver(_image_metas))
            self._context.set_resolver('exif', context.MapResolver(_adapter.image_exif(_image)))

            logger.info("Input: {} = {}".format(_images_in, _image))
            _image_out = _plugin.run(self._context.evaluate_model(_finishing), _image, self._context)
            logger.info("Output: {} = {}".format(_images_out, _image_out))
    
            for _name_out in _images_out:
                self._context.set_image_data(_name_out, _image_out)

        _image = self._context.get_image()
        _image_data = _adapter.image_data(_image)
        _image_meta = _adapter.image_meta(_image)

        _adapter.image_resize(_image, 640, 480, True)
        _image_preview = _adapter.image_data(_image)

        logger.info("Result: {}x{} pixels, {} bytes".format(
            _image_meta['width'],
            _image_meta['height'],
            len(_image_data)))

        return ProcessingResult(_image_meta, _image_data, _image_preview)


class ProcessingResult:

    def __init__(self, meta, image_data, image_preview):
        self._image_data = image_data
        self._image_preview = image_preview
        self._meta = meta

    def get_data(self):
        return self._image_data

    def get_preview(self):
        return self._image_preview

    def get_width(self):
        return self._meta['width']

    def get_height(self):
        return self._meta['height']

    def get_mime(self):
        return self._meta['mime']


class Color:

    def __init__(self, color:str, alpha:int=None):
        self._color = color
        self._alpha = alpha

    def __repr__(self):
        return "<{}: color={}, alpha={}>".format(type(self).__name__, self._color, self._alpha)

    def get_color(self):
        return self._color

    def get_alpha(self):
        return self._alpha


class Brush:

    def __init__(self, stroke_color:Color, stroke_width:int=None, fill_color:Color=None):
        self._stroke_color = stroke_color
        self._stroke_width = stroke_width
        self._fill_color = fill_color

    def __repr__(self):
        return "<{}: stroke={}, width={}, fill={}>".format(type(self).__name__, self._stroke_color, self._stroke_width, self._fill_color)

    def get_stroke_color(self):
        return self._stroke_color

    def get_stroke_width(self):
        return self._stroke_width

    def get_fill_color(self):
        if self._fill_color:
            return self._fill_color
        return self._stroke_color


class Position:

    def __init__(self, x:int, y:int):
        self._x = x
        self._y = y

    def __repr__(self):
        return "<{}: x={}, y={}>".format(type(self).__name__, self._x, self._y)

    def __add__(self, other):
        if type(other) == Position:
            return Position(self._x + other.get_x(), self._y + other.get_y())
        if type(other) == Size:
            return Position(self._x + other.get_width(), self._y + other.get_height())
        raise NotImplemented("Can not operate {} with {}".format(type(self), type(other)))

    def __sub__(self, other):
        if type(other) == Position:
            return Position(self._x - other.get_x(), self._y - other.get_y())
        if type(other) == Size:
            return Position(self._x - other.get_width(), self._y - other.get_height())
        raise NotImplemented("Can not operate {} with {}".format(type(self), type(other)))

    def get_x(self):
        return self._x

    def get_y(self):
        return self._y


class Size:

    def __init__(self, width:int, height:int):
        self._width = width
        self._height = height

    def __repr__(self):
        return "<{}: width={}, heigth={}>".format(type(self).__name__, self._width, self._height)

    def __add__(self, other):
        if type(other) == Size:
            return Size(self._width + other.get_width(), self._height + other.get_height())
        raise NotImplemented("Can not operate {} with {}".format(type(self), type(other)))

    def __sub__(self, other):
        if type(other) == Size:
            return Size(self._width - other.get_width(), self._height - other.get_height())
        raise NotImplemented("Can not operate {} with {}".format(type(self), type(other)))

    def get_width(self):
        return self._width

    def get_height(self):
        return self._height


class Geometry:

    def __init__(self, position:Position, size:int=None, end:int=None):
        self._position = position
        if size:
            self._size = int(size)
        if end:
            self._size = Size(end.get_x() - self._position.get_x(), end.get_y() - self._position.get_y())


class Text:
    ALIGN_LEFT = 'left'
    ALIGN_RIGHT = 'right'
    ALIGN_CENTER = 'center'

    def __init__(self, text:str, font:str=None, size:int=None, weight:int=None, alignment:str=None, border:int=None, border_radius:int=None):
        self._text = text
        self._font = font
        self._size = size
        self._weight = weight
        self._alignment = alignment
        self._border = border
        self._border_radius = border_radius

    def __repr__(self):
        return "<{}: text={}, font={}, size={}, align={}>".format(type(self).__name__, self._text, self._font, self._size, self._align)

    def get_text(self):
        return self._text

    def get_font(self):
        return self._font

    def get_size(self):
        return self._size

    def get_weight(self):
        return self._weight

    def get_alignment(self):
        return self._alignment

    def get_border(self):
        return self._border

    def get_border_radius(self):
        return self._border_radius


class ImageContainer:

    def __init__(self):
        self._images = []

    def __repr__(self):
        return "<{}: {} images: {}>".format(
            type(self).__name__,
            len(self._images),
            ', '.join(["{}x{}".format(_i.width, _i.height) for _i in self._images]))

    def add_image(self, image):
        self._images.append(image)

    def add_images(self, images):
        self._images.extend(images)

    def get_images(self):
        return self._images


class ImageProcessingAdapter:

    def image_open(self, url, background=None):
        raise NotImplementedException()

    def image_data(self, image):
        raise NotImplementedException()

    def image_meta(self, image):
        raise NotImplementedException()

    def image_exif(self, image):
        raise NotImplementedException()

    def image_resize(self, image, resize_x, resize_y, keep_aspect):
        raise NotImplementedException()

    def image_scale(self, image, factor):
        raise NotImplementedException()

    def image_rotate(self, image, factor):
        raise NotImplementedException()

    def image_blur(self, image, factor):
        raise NotImplementedException()

    def image_alpha(self, image, alpha):
        raise NotImplementedException()

    def image_merge(self, image, alignment, coords):
        raise NotImplementedException()

    def image_clone(self, image):
        raise NotImplementedException()

    def image_close(self):
        raise NotImplementedException()

    def draw_line(self, image, start, end, brush):
        raise NotImplementedException()

    def draw_rect(self, image, start, end, brush):
        raise NotImplementedException()

    def draw_circle(self, image, _pos, _size, _brush):
        raise NotImplementedException()

    def draw_text(self, image, pos, text, brush, border_brush=None, border_radius=None, border_padding=None):
        raise NotImplementedException()


class WandImageProcessingAdapter(ImageProcessingAdapter):

    def __init__(self):
        self._wand_resource = importlib.import_module('wand.resource')
        self._wand_image = importlib.import_module('wand.image')
        self._wand_drawing = importlib.import_module('wand.drawing')
        self._wand_color = importlib.import_module('wand.color')

    def _color(self, color):
        if color is None:
            return None
        _color = self._wand_color.Color(color.get_color())
        if color.get_alpha():
            _color.alpha = color.get_alpha() / 100
        return _color

    def _drawing(self, brush=None, text=None):
        _drawing = self._wand_drawing.Drawing()
        if brush:
          if brush.get_stroke_color():
              _drawing.stroke_color = self._color(brush.get_stroke_color())
          if brush.get_stroke_width():
              _drawing.stroke_width = brush.get_stroke_width()
          if brush.get_fill_color():
              _drawing.fill_color = self._color(brush.get_fill_color())
        if text:
          _drawing.stroke_color = self._wand_color.Color('none')
          _drawing.stroke_width = 0
          if brush.get_stroke_color():
              _drawing.fill_color = self._color(brush.get_stroke_color())
          if text.get_font():
              _drawing.font_familiy = text.get_font()
          if text.get_weight():
              _drawing.font_weight = text.get_weight()
          if text.get_size():
              _drawing.font_size = text.get_size()
          if text.get_alignment():
              _align_map = {Text.ALIGN_LEFT: 'left', Text.ALIGN_RIGHT: 'right', Text.ALIGN_CENTER: 'center'}
              _drawing.text_alignment = _align_map[text.get_alignment()]
        return _drawing

    def _apply_drawing(self, image, drawing):
        self._apply(image, lambda i: drawing(i))

    def _apply(self, image, func):
        for _image in image.get_images():
            func(_image)

    def image_open(self, url, background=None):
        if url.startswith('http://') or url.startswith('https://'):
            _image = self._wand_image.Image(blob=requests.get(url, timeout=(15, 30), stream=True).raw)
        elif Filesystem.file_exists(url):
            _image = self._wand_image.Image(blob=Filesystem.file_read(url))
        else:
            raise Exception('Only URLs and files are supported, not {}'.format(url))
        _image.auto_orient()
        if background:
            _bg = self._wand_image.Image(width=_image.width, height=_image.height, background=self._color(background))
            _bg.composite(_image)
            _image.close()
            _image = _bg
        _image_container = ImageContainer()
        _image_container.add_image(_image)
        return _image_container

    def image_data(self, image):
        return image.get_images()[0].make_blob()

    def image_meta(self, image):
        _image = image.get_images()[0]
        return {
          'width': _image.width,
          'height': _image.height,
          'mime': _image.mimetype
        }

    def image_exif(self, image):
        _meta = image.get_images()[0].metadata.items()
        _exif = {}
        _exif.update((_k[5:].lower(), _v) for _k, _v in _meta if _k.startswith('exif:'))
        return _exif

    def image_resize(self, image, resize_x, resize_y, keep_aspect):
        def resize(i):
            if keep_aspect:
                _w_factor = resize_x / i.width
                _h_factor = resize_y / i.height
                _factor = _w_factor if _w_factor < _h_factor else _h_factor
                i.resize(int(i.width * _factor), int(i.height * _factor))
            else:
                i.resize(resize_x, resize_y)
        self._apply(image, resize)

    def image_scale(self, image, factor):
        self._apply(image, lambda i: i.resize(int(i.width*factor), int(i.height*factor)))

    def image_rotate(self, image, factor):
        self._apply(image, lambda i: i.rotate(factor))

    def image_blur(self, image, factor):
        self._apply(image, lambda i: i.resize(filter='gaussian', blur=factor))

    def image_alpha(self, image, background, factor):
        def alpha(i):
            i.alpha_channel = 'set'
            if background and factor:
                _bg = self._wand_image.Image(width=i.width, height=i.height, background=self._color(background))
                _bg.alpha_channel = 'set'
                _bg.evaluate(operator='set', value=i.quantum_range*factor/100, channel='alpha')
                i.composite(_bg)
                _bg.close()
            i.evaluate(operator='set', value=i.quantum_range*factor/100, channel='alpha')
        self._apply(image, alpha)

    def image_merge(self, image, alignment, coords=None):
        _gravity_map = {
            'top': 'north',
            'top-left': 'north_west',
            'top-right': 'north_east',
            'bottom': 'south',
            'bottom-left': 'south_west',
            'bottom-right': 'south_east',
            'left': 'west',
            'right': 'east',
            'center': 'center',
        }
        _first = image.get_images()[0]
        if coords:
            _gravity = None
            _left, _top = coords
        else:
            _gravity = _gravity_map[alignment] if alignment in _gravity_map else 'center'
            _top = None
            _left = None
        for _image in image.get_images()[1:]:
            _first.composite(_image, top=_top, left=_left, gravity=_gravity)
        _image_container = ImageContainer()
        _image_container.add_image(_first)
        return _image_container

    def image_clone(self, image):
        _image_container = ImageContainer()
        for _image in image.get_images():
            _image_container.add_image(_image.clone())
        return _image_container
    
    def image_close(self, image):
        image.destroy()

    def draw_line(self, image, start, end, brush):
        with self._drawing(brush=brush) as _drawing:
            _drawing.line((start.get_x(), start.get_y()), (end.get_x(), end.get_y()))
            self._apply_drawing(image, _drawing)

    def draw_rect(self, image, start, end, brush, radius=None):
        with self._drawing(brush=brush) as _drawing:
            _drawing.rectangle(start.get_x(), start.get_y(), end.get_x(), end.get_y(), radius=radius)
            self._apply_drawing(image, _drawing)

    def draw_circle(self, image, pos, size, brush):
        with self._drawing(brush=brush) as _drawing:
          _drawing.circle((pos.get_x(), pos.get_y()), (size.get_width(), size.get_height()))
          self._apply_drawing(image, _drawing)

    def draw_text(self, image, pos, text, brush, border_brush=None, border_radius=None, border_padding=None):
        with self._drawing(text=text, brush=brush) as _drawing:
            _text = text.get_text()
            if border_brush and border_brush.get_stroke_width() is not None:
                _padding = int(border_padding) if border_padding else 0
                _metrics = _drawing.get_font_metrics(image.get_images()[0], _text)
                if text.get_alignment() == Text.ALIGN_LEFT:
                    _xoffset = 0
                elif text.get_alignment() == Text.ALIGN_RIGHT:
                    _xoffset = -_metrics.text_width
                elif text.get_alignment() == Text.ALIGN_CENTER:
                    _xoffset = int(-_metrics.text_width/2)
                if border_brush.get_stroke_width() == 0:
                    border_brush = Brush(
                        None, 0,
                        border_brush.get_fill_color())
                _x1 = pos.get_x() - _padding + _xoffset + _metrics.descender
                _y1 = pos.get_y() - _padding - _metrics.text_height - _metrics.descender
                _x2 = pos.get_x() + _padding + _metrics.text_width + _xoffset - _metrics.descender
                _y2 = pos.get_y() + _padding - _metrics.descender
                self.draw_rect(image, Position(_x1, _y1), Position(_x2, _y2), border_brush, radius=border_radius)
            _drawing.text(pos.get_x(), pos.get_y(), _text)
            self._apply_drawing(image, _drawing)


