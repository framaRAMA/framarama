
from django.core.management.base import BaseCommand

from framarama.base import utils
from config import models

class Command(BaseCommand):
    help = 'Check files of Data models and report status'

    def add_arguments(self, parser):
        parser.add_argument('--cleanup', action='store_true', help='Delete models without files or files without model')

    def handle(self, *args, **options):
        _remove = options['cleanup']
        self._report_status('Database', self._check_db(_remove), _remove)
        self._report_status('Filesystem', self._check_fs(_remove), _remove)

    def _check_db(self, remove=False):
        _items = models.Data.objects.all()
        _count = len(_items)
        _chunk = int(_count/10) if _count > 100 else _count
        self.stdout.write('Database: Checking {} items'.format(_count))
        _stats = {'total': 0, 'ok': 0, 'delete': 0}
        for _i, _data in enumerate(_items):
            _stats['total'] = _stats['total'] + 1
            if _data.data_file and utils.Filesystem.file_exists(_data.data_file.path):
                _stats['ok'] = _stats['ok'] + 1
            else:
                _stats['delete'] = _stats['delete'] + 1
                self.stdout.write('Database: Missing file for {}'.format(_data))
                if remove:
                    _data.delete()
                    self.stdout.write('Database: Deleted {}'.format(_data))
            if (_i % _chunk == 0) or (_stats['total'] == _count):
                self.stdout.write('Database: {:.0%}, checked {} items ...'.format(_stats['total']/_count, _stats['total']))
        return _stats

    def _check_fs(self, remove=False):
        _skip = [models.Data, models.BaseImageData]
        _classes = utils.Classes.subclasses(models.Data)
        _stats = {'total': 0, 'ok': 0, 'delete': 0}
        for _clazz in [_clazz for _clazz in _classes if _clazz not in _skip]:
            _path = _clazz.path().replace('./', '')
            _files = utils.Filesystem.file_match(_path, '.*', recurse=True)
            _files = [_path + '/' + _file[0] for _file in _files]
            self.stdout.write('Filesystem: Checking {} items in {}'.format(len(_files), _path))
            _items = models.Data.objects.filter(data_file__in=_files)
            _deletes = set(_files) - set([_item.data_file.name for _item in _items])
            for _delete in _deletes:
                self.stdout.write('Filesystem: Missing model for {}'.format(_delete))
                if remove:
                    utils.Filesystem.file_delete(_delete)
                    self.stdout.write('Filesystem: Deleted {}'.format(_delete))
            _stats['total'] = _stats['total'] + len(_files)
            _stats['ok'] = _stats['ok'] + len(_items)
            _stats['delete'] = _stats['delete'] + len(_deletes)
        return _stats

    def _report_status(self, prefix, stats, remove):
        self.stdout.write('{}: {}, checked {} items ({} ok, {} delete)'.format(
            prefix,
            'All OK' if stats['total'] == stats['ok'] else 'Cleaned up' if remove else 'Cleanup required',
            stats['total'],
            stats['ok'],
            stats['delete']))

