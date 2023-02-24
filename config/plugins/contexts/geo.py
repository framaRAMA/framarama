import logging
import requests

from django.db import models
from django.template import Context, Template

from framarama.base import forms as base
from config.models import FrameContext
from config.plugins import ContextPluginImplementation
from config.forms.frame import CreateContextForm, UpdateContextForm
from config.utils import context


logger = logging.getLogger(__name__)

FIELDS = [
    'image',
]
WIDGETS = {
    'image': base.charFieldWidget(),
}


class GeoModel(FrameContext):
    frame_ptr = models.OneToOneField(FrameContext, on_delete=models.DO_NOTHING, parent_link=True, primary_key=True)
    image = models.CharField(
        max_length=256, blank=True,
        verbose_name='Images', help_text='Specify images to provide geo location information (defaults to "default")')

    class Meta:
        managed = False


class GeoCreateForm(CreateContextForm):
    class Meta:
        model = GeoModel
        fields = CreateContextForm.fields(FIELDS)
        widgets = CreateContextForm.widgets(WIDGETS)


class GeoUpdateForm(UpdateContextForm):
    class Meta:
        model = GeoModel
        fields = UpdateContextForm.fields(FIELDS)
        widgets = UpdateContextForm.widgets(WIDGETS)


class Implementation(ContextPluginImplementation):
    CAT = FrameContext.CAT_GEO
    TITLE = 'Geo'
    DESCR = 'Provide geo location information of image'

    Model = GeoModel
    CreateForm = GeoCreateForm
    UpdateForm = GeoUpdateForm

    def __init__(self):
        self._cache = {}

    def _coord(self, ref, coord):
        if ref == 'W' or ref == 'S':
            _factor = -1
        else:
            _factor = 1
        _info = coord.split()  # split string "49/1, 28/1, 50264282/1000000"
        _deg = _info[0].strip(',') if len(_info) > 0 else 0
        _min = _info[1].strip(',') if len(_info) > 1 else 0
        _sec = _info[2].strip(',') if len(_info) > 2 else 0
        _coord = 0
        for _val in [_sec, _min, _deg]:
            _num, _fract = _val.split('/')
            _coord = _coord / 60 + _factor * int(_num) / int(_fract)
        return _coord

    def _geo(self, exif):
        _coords = {}
        for _name in ['lat', 'long']:
            _key_ref = 'gps{}ituderef'.format(_name)  # exif:GPSLatitudeRef=N
            _key_str = 'gps{}itude'.format(_name)     # exif:GPSLatitude=49/1, 28/1, 50264282/1000000
            _vals = [exif[_key] for _key in [_key_ref, _key_str] if _key in exif]
            if len(_vals) < 2:
                return {}
            _coords[_name] = self._coord(_vals[0], _vals[1])

        # Use OpenStreetMap API
        # https://nominatim.org/release-docs/develop/api/Overview/ - entry point
        # https://nominatim.org/release-docs/develop/api/Output/ - output formats
        _key = " ".join([f"{k}:{v}" for k, v in _coords.items()])
        if _key not in self._cache:
            _url = "https://nominatim.openstreetmap.org/reverse.php?lat={}&lon={}&zoom=18&format=jsonv2".format(
                _coords['lat'],
                _coords['long'])
            _response = requests.get(_url, timeout=(5, 10))
            _response.raise_for_status()
            _json = _response.json()

            # Extract information from JSON response:
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
            if 'address' in _json:
                _addr = _json['address']
                _info = []
                for _item in ['postcode', 'road', 'village', 'state', 'country']:
                    if _item in _addr:
                        _info.append(_addr[_item])
                _json['geo_display_name'] = ', '.join(_info)
            logger.debug("Resolving coordinates via {} to {}".format(_url, _json))
            self._cache[_key] = _json
        return self._cache[_key]

    def run(self, model, image, ctx):
        _adapter = ctx.get_adapter()

        _resolvers = {'geos': {}}
        for _name, _image in self.get_images(ctx, model.image).items():
            _image_exif = _adapter.image_exif(_image) if _image.get_images() else {}

            _resolver = context.MapResolver(self._geo(_image_exif))
            if _name == 'default':
                _resolvers['geo'] = _resolver
            else:
                _resolvers['geos'][_name] = _resolver

        return _resolvers

