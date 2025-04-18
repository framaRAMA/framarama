import logging
import requests
import functools

from django import forms
from django.template import Context

from framarama.base import api, utils, forms as base
from config.models import FrameContext
from config.plugins import ContextPluginImplementation
from config.forms.frame import ContextForm
from config.utils import context


logger = logging.getLogger(__name__)


class GeoForm(ContextForm):
    image = forms.CharField(
        max_length=256, required=False, widget=base.charFieldWidget(),
        label='Images', help_text='Specify images to provide geo location information (defaults to "default")')

    class Meta(ContextForm.Meta):
        entangled_fields = {'plugin_config': ['image']}

    field_order = ContextForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(ContextPluginImplementation):
    CAT = FrameContext.CAT_GEO
    TITLE = 'Geo'
    DESCR = 'Provide geo location information of image'

    Form = GeoForm

    def __init__(self):
        self._cache = {}

    def _coord(self, ref, coord):
        _factor = -1 if ref == 'W' or ref == 'S' else 1
        _info = coord.split()  # split string "49/1, 28/1, 50264282/1000000"
        _deg = _info[0].strip(',') if len(_info) > 0 else '0/0'
        _min = _info[1].strip(',') if len(_info) > 1 else '0/0'
        _sec = _info[2].strip(',') if len(_info) > 2 else '0/0'
        _fractions = []
        for _val in [_sec, _min, _deg]:
            _num, _fract = _val.split('/')
            if len(_num) and len(_fract) and _fract != '0':
                _fractions.append(_factor * int(_num) / int(_fract))
        return functools.reduce(lambda _coord, _fract: _coord / 60 + _fract, _fractions, 0) if len(_fractions) else None

    def _resolve(self, data, attrs, level=0):
        _info = []
        for _attr in attrs:
            if type(_attr) == list:
                _recurse = self._resolve(data, _attr, level=level+1)
                if len(_recurse):
                    _info.append(' '.join(_recurse))
            elif _attr in data and data[_attr] != '':
                _info.append(data[_attr])
                break;
        return ', '.join(_info) if level == 0 else _info

    def _geo(self, exif):
        _coords = {'lat': None, 'long': None}
        for _name in ['lat', 'long']:
            _key_ref = 'gps{}ituderef'.format(_name)  # exif:GPSLatitudeRef=N
            _key_str = 'gps{}itude'.format(_name)     # exif:GPSLatitude=49/1, 28/1, 50264282/1000000
            _vals = [exif[_key] for _key in [_key_ref, _key_str] if _key in exif]
            _coords[_name] = self._coord(_vals[0], _vals[1]) if len(_vals) > 1 else None
        return _coords

    def _lookup(self, coords):
        if coords['lat'] is None or coords['long'] is None:
            return {}

        # Use OpenStreetMap API
        # https://nominatim.org/release-docs/develop/api/Overview/ - entry point
        # https://nominatim.org/release-docs/develop/api/Output/ - output formats
        _key = " ".join([f"{k}:{v}" for k, v in coords.items()])
        if _key not in self._cache:
            _url = "https://nominatim.openstreetmap.org/reverse.php?lat={}&lon={}&zoom=18&format=jsonv2".format(
                coords['lat'],
                coords['long'])

            try:
                _response = api.ApiClient.get().get_url(_url)
                _response.raise_for_status()
            except Exception as e:
                logger.warn("Resolving coordinates via {} failed: {}".format(_url, e))
                return {}

            _json = _response.json()

            # Extract information from JSON response:
            # https://nominatim.openstreetmap.org/reverse.php?lat=48.8031042&lon=8.5028172&zoom=22&format=jsonv2
            #   place_id	92224919
            #   licence	"Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright"
            #   osm_type	"node"
            #   osm_id	9006423316
            #   lat	"48.8031042"
            #   lon	"8.5028172"
            #   display_name	"Schwanner Rain Waldklinik, Hinterer Baumweg, Dobel, Verwaltungsgemeinschaft Bad Herrenalb, Landkreis Calw, Baden-Württemberg, 75335, Germany"
            #   address
            #     tourism	"Schwanner Rain Waldklinik"
            #     road	"Hinterer Baumweg"
            #     village	"Dobel"
            #     municipality	"Verwaltungsgemeinschaft Bad Herrenalb"
            #     county	"Landkreis Calw"
            #     state	"Baden-Württemberg"
            #     ISO3166-2-lvl4	"DE-BW"
            #     postcode	"75335"
            #     country	"Germany"
            #     country_code	"de"
            #   boundingbox
            #     0	"48.8030542"
            #     1	"48.8031542"
            #     2	"8.5027672"
            #     3	"8.5028672"
            # https://nominatim.openstreetmap.org/reverse.php?lat=49.013343810833&lon=8.4008913038889&zoom=22&format=jsonv2
            # place_id	59049923
            # licence	"Data © OpenStreetMap contributors, ODbL 1.0. https://osm.org/copyright"
            # osm_type	"node"
            # osm_id	5486732812
            # lat	"49.0131412"
            # lon	"8.4008583"
            # place_rank	30
            # category	"tourism"
            # type	"artwork"
            # importance	0.00000999999999995449
            # addresstype	"tourism"
            # name	"Orest und Pylades"
            # display_name	"Orest und Pylades, Schlossbezirk, Innenstadt-West Östlicher Teil, Innenstadt-West, Karlsruhe, Baden-Württemberg, 76131, Germany"
            # address
            #   tourism	"Orest und Pylades"
            #   road	"Schlossbezirk"
            #   neighbourhood	"Innenstadt-West Östlicher Teil"
            #   suburb	"Innenstadt-West"
            #   city	"Karlsruhe"
            #   state	"Baden-Württemberg"
            #   ISO3166-2-lvl4	"DE-BW"
            #   postcode	"76131"
            #   country	"Germany"
            #   country_code	"de"
            # boundingbox
            #   0	"49.0130912"
            #   1	"49.0131912"
            #   2	"8.4008083"
            #   3	"8.4009083"
            if 'address' in _json:
                _fields = [['road'], [['postcode'], ['city', 'town', 'village']], ['state'], ['country']]
                _json['geo_display_name'] = self._resolve(_json['address'], _fields)
            logger.debug("Resolving coordinates {} via {} to {}".format(coords, _url, _json))
            self._cache[_key] = _json
        return self._cache[_key]

    def run(self, model, config, image, ctx):
        _image = config.image.as_str()

        _adapter = ctx.get_adapter()

        _resolvers = {'geos': {}}
        for _name, _img in self.get_images(ctx, _image).items():
            _image_exif = _adapter.image_exif(_img) if _img.get_images() else {}

            _resolver = context.MapResolver(self._lookup(self._geo(_image_exif)))
            if _name == 'default':
                _resolvers['geo'] = _resolver
            else:
                _resolvers['geos'][_name] = _resolver

        return _resolvers

