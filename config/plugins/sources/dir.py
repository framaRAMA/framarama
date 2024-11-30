import json
import requests
import hashlib
import logging

from django import forms
from django.conf import settings

from framarama.base import forms as base, api, utils
from config.models import SourceStep
from config.plugins import SourcePluginImplementation
from config.forms.frame import SourceStepForm
from config.utils import data, finishing


logger = logging.getLogger(__name__)


class DirectoryForm(SourceStepForm):
    path = forms.CharField(
        max_length=255, required=False, widget=base.charFieldWidget(),
        label='Directory', help_text='Path to read the media files from (defaults to media directory)')
    filter_files = forms.CharField(
        max_length=64, required=False, widget=base.charFieldWidget(),
        label='Filter files', help_text='Regular expression pattern to filter files (defaults to ".*\.(jpg|JPG)")')

    class Meta(SourceStepForm.Meta):
        entangled_fields = {'plugin_config': ['path']}

    field_order = SourceStepForm.Meta.untangled_fields + Meta.entangled_fields['plugin_config']


class Implementation(SourcePluginImplementation):
    CAT = SourceStep.CAT_DIR
    TITLE = 'Directory'
    DESCR = 'Read media files from directory'
    
    Form = DirectoryForm
    
    def run(self, model, config, data_in, ctx):
        _adapter = finishing.ImageProcessingAdapter.get_default()
        _root = settings.FRAMARAMA['MEDIA_PATH'] + '/'
        _path = utils.Filesystem.path_normalize(config.path.as_str(), root=_root, absolute=True)
        _filter_files = config.filter_files.as_str() if config.filter_files.as_str() else '.*\.(jpg|JPG)'

        logger.info('Reading {} (filter "{}")'.format(_path, _filter_files))
        _files = []
        for _file, _dummy in utils.Filesystem.file_match(_path, _filter_files, files=True, dirs=False, recurse=True):
            _filename = _root + _file
            _image = _adapter.image_open(_filename)
            _exif = _adapter.image_exif(_image)
            _adapter.image_close(_image);
            _files.append({
                'id': hashlib.md5(_filename.encode()).hexdigest(),
                'url': _filename.replace(_root, ''),
                'date': utils.DateTime.format(utils.DateTime.parse(_exif['datetime'])),
            })

        return [data.DataContainer(_files, data_type=data.DataType(data.DataType.TYPE, 'dict'))]

