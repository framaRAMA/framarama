
from django.core.management.base import BaseCommand

from framarama.base import utils
from config import models

class Command(BaseCommand):
    help = 'Check files of Data models and report status'

    def add_arguments(self, parser):
        parser.add_argument('--cleanup', action='store_true', help='Delete models without files or files without model')
        parser.add_argument('--db', action='store_true', help='If given only check database')
        parser.add_argument('--fs', action='store_true', help='If given only check filesystem')

    def handle(self, *args, **options):
        _rm = options['cleanup']
        _db = options['db']
        _fs = options['fs']
        if _db or not _fs:
            self.stdout.write('Database: Reading items')
            _items = models.Data.objects.all()
            _status = self._check_items('Database', _items, _rm, self._check_db_item)
            self._report_status('Database', _status, _rm)
        if _fs or not _db:
            _skip = [models.Data, models.BaseImageData]
            _classes = utils.Classes.subclasses(models.Data)
            _dirs = []
            for _clazz in [_clazz for _clazz in _classes if _clazz not in _skip]:
                _path = _clazz.path().replace('./', '')
                self.stdout.write('Filesystem: Reading items in {}'.format(_path))
                _data_dirs = utils.Filesystem.file_match(_path, '.*', files=False, dirs=True, recurse=1)
                _dirs.extend([_path + '/' + _dir[0] for _dir in _data_dirs if '/' in _dir[0]])
            _status = self._check_items('Filesystem', _dirs, _rm, self._check_fs_item)
            self._report_status('Filesystem', _status, _rm)

    def _check_db_item(self, item, remove):
        if item.data_file and utils.Filesystem.file_exists(item.data_file.path):
            return (1, 1, 0)
        else:
            self.stdout.write('Database: Missing file for {}'.format(item))
            if remove:
                item.delete()
                self.stdout.write('Database: Deleted {}'.format(item))
            return (1, 0, 1)

    def _check_fs_item(self, item, remove):
        _files = utils.Filesystem.file_match(item, '.*')
        _files = [item + '/' + _file[0] for _file in _files]
        _items = models.Data.objects.filter(data_file__in=_files)
        _deletes = set(_files) - set([_item.data_file.name for _item in _items])
        for _delete in _deletes:
            self.stdout.write('Filesystem: Missing model for {}'.format(_delete))
            if remove:
                utils.Filesystem.file_delete(_delete)
                self.stdout.write('Filesystem: Deleted {}'.format(_delete))
        return (len(_files), len(_files) - len(_deletes), len(_deletes))

    def _check_items(self, prefix, items, remove, check_item):
        _count = len(items)
        _chunk = int(_count/10) if _count > 100 else _count
        self.stdout.write('{}: Checking {} items'.format(prefix, _count))
        _stats = {'total': 0, 'ok': 0, 'delete': 0, 'items': 0}
        for _i, _item in enumerate(items):
            _total, _ok, _deletes = check_item(_item, remove)
            _stats['items'] = _stats['items'] + 1
            _stats['total'] = _stats['total'] + _total
            _stats['ok'] = _stats['ok'] + _ok
            _stats['delete'] = _stats['delete'] + _deletes
            if (_i % _chunk == 0) or (_stats['items'] == _count):
                self.stdout.write('{}: {:.0%}, checked {} items ...'.format(prefix, _stats['items']/_count, _stats['items']))
        return _stats

    def _report_status(self, prefix, stats, remove):
        self.stdout.write('{}: {}, checked {} items ({} ok, {} delete)'.format(
            prefix,
            'All OK' if stats['total'] == stats['ok'] else 'Cleaned up' if remove else 'Cleanup required',
            stats['total'],
            stats['ok'],
            stats['delete']))

