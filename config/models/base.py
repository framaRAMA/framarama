import os
import io
import hashlib
import logging


from django.db import models
from django.conf import settings
from django.core.files.base import File


from framarama.base import utils
from framarama.base.models import BaseModel


logger = logging.getLogger(__name__)


class Data(BaseModel):
    STR_FIELDS = BaseModel.STR_FIELDS + ['category', 'data_file']
    PATH = [settings.FRAMARAMA['DATA_PATH'], 'config']
    NAME_NEW = '__NEW_DATA_FILE__'

    def _upload(instance, path):
        _md5 = hashlib.md5()
        _md5.update("{}#{}".format(path, utils.DateTime.now().timestamp()).encode())
        _md5_hex = _md5.hexdigest()
        return instance.path([_md5_hex[0:2], _md5_hex[2:4], _md5_hex])

    category = models.CharField(
        max_length=255,
        verbose_name='Category', help_text='The category of the type of data item')
    data_size = models.IntegerField(
        blank=True, null=True,
        verbose_name='Size', help_text='Amount of bytes used for this data item')
    data_mime = models.CharField(
        max_length=64, blank=True, null=True,
        verbose_name='Mime type', help_text='The content type of this data item')
    data_file = models.FileField(
        blank=True, null=True, editable=False, upload_to=_upload,
        verbose_name='Save as file', help_text='Store content in the filesystem')
    meta = models.JSONField(
        blank=True, null=True, editable=False, default=dict,
        verbose_name='Info', help_text='Meta information for data item')

    def update(self, other):
        self.category = other.category
        self.data_size = other.data_size
        self.data_mime = other.data_mime
        self.data_file.open('wb')
        self.data_file.write(other.data())
        self.meta = other.meta

    def set_meta(self, name, value):
        self.meta[name] = value

    def get_meta(self, name):
        self.meta.get(name, None)

    def data(self):
        if self.data_file.name == Data.NAME_NEW:
            return self.data_file.read()
        else:
            return utils.Filesystem.file_read(self.data_file.path)

    def delete(self, *args, **kwargs):
        if self.data_file:
            self.data_file.delete()
        super(Data, self).delete(*args, **kwargs)

    @classmethod
    def path(cls, additional=None):
        _path = Data.PATH.copy() + (additional if additional else [])
        return os.path.join(*_path)

    @classmethod
    def create(cls, json=None, data=None, mime=None, meta=None):
        if json:
            _data = utils.Json.from_dict(json).encode()
            _mime = 'application/json' if mime is None else mime
        elif data:
            _data = data
        else:
            raise Exception('Specify JSON or data to create a Data object')
        _file = File(io.BytesIO(_data), name=Data.NAME_NEW)
        _instance = cls()
        _instance.data_mime = mime
        _instance.data_size = _file.size
        _instance.data_file = _file
        _instance.meta = meta if meta else {}
        return _instance

    @classmethod
    def post_delete(cls, sender, instance, entity, *args, **kwargs):
        logger.debug("Delete from {} for {}: {}".format(sender, instance, entity))
        if entity:
            entity.delete()


class BaseImageData(Data):
    PATH = []

    class Meta:
        proxy = True

    @classmethod
    def path(cls, additional=None):
        return super().path(cls.PATH + (additional if additional else []))

    def get_width(self):
        return self.get_meta('width')

    def set_width(self, width):
        return self.set_meta('width', width)

    def get_height(self):
        return self.get_meta('height')

    def set_width(self, height):
        return self.set_meta('height', height)


class ItemThumbnailData(BaseImageData):
    PATH = ['item', 'thumbnail']

    class Meta:
        proxy = True


class DisplayItemThumbnailData(BaseImageData):
    PATH = ['display', 'thumbnail']

    class Meta:
        proxy = True
