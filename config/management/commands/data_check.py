
from django.core.management.base import BaseCommand

from framarama.base import utils
from config import models

class Command(BaseCommand):
    help = 'Check files of Data models and report status'

    def add_arguments(self, parser):
        parser.add_argument('--cleanup', action='store_true', help='Delete models without files or files without model')
        parser.add_argument('--db', action='store_true', help='If given only check database')
        parser.add_argument('--fs', action='store_true', help='If given only check filesystem')
        parser.add_argument('--chunk', type=int, default=100, help='Process with given chunk size (default 100)')

    def handle(self, *args, **options):
        _rm = options['cleanup']
        _db = options['db']
        _fs = options['fs']
        _chunk = options['chunk']
        _processes = []
        if _db or not _fs:
            _processes.append([
                'Database',
                self._db_items,
                lambda items: [_item for _item in items if _item.data_file and utils.Filesystem.file_exists(_item.data_file.path)],
                lambda item: item.delete()
            ])
        if _fs or not _db:
            _processes.append([
                'Filesystem',
                self._fs_items,
                lambda items: [_item.data_file.name for _item in models.Data.objects.filter(data_file__in=items)],
                lambda item: utils.Filesystem.file_delete(item)
            ])
        for _name, _generator, _check, _delete in _processes:
            _status = self._check_items(_name, _generator, _rm, _chunk, _check, _delete)
            self._report_status(_name, _status, _rm)

    def _db_items(self):
        for _item in models.Data.objects.all():
            yield _item

    def _fs_items(self):
        _skip = [models.Data, models.BaseImageData]
        _classes = utils.Classes.subclasses(models.Data)
        for _clazz in [_clazz for _clazz in _classes if _clazz not in _skip]:
            _path = _clazz.path().replace('./', '')
            self.stdout.write('Filesystem: Reading items in {}'.format(_path))
            _dirs = utils.Filesystem.file_match(_path, '.*', files=False, dirs=True, recurse=1)
            for _dir in [_dir[0] for _dir in _dirs if '/' in _dir[0]]:
                for _item in utils.Filesystem.file_match(_path + '/' + _dir, '.*'):
                    yield _path + '/' + _dir + '/' + _item[0]

    def _check_items(self, prefix, items, remove, size, check_items, delete_item):
        self.stdout.write('{}: Checking items'.format(prefix))
        _stats = {'total': 0, 'ok': 0, 'delete': 0}
        for _items in self._chunked(items, size):
            _existing = check_items(_items)
            _deletes = set(_items) - set(_existing)
            for _delete in _deletes:
                self.stdout.write('{}: Missing {}'.format(prefix, _delete))
                if remove:
                    delete_item(_delete)
                    self.stdout.write('{}: Deleted {}'.format(prefix, _delete))
            _stats['total'] = _stats['total'] + len(_items)
            _stats['ok'] = _stats['ok'] + len(_existing)
            _stats['delete'] = _stats['delete'] + len(_deletes)
            self.stdout.write('{}: Checked {} items (last {} items: {} ok, {} delete)'.format(
                prefix,
                _stats['total'],
                len(_items),
                len(_existing),
                len(_deletes)))
        return _stats

    def _chunked(self, items, size):
        _result = []
        for _item in items():
            _result.append(_item)
            if len(_result) == size:
                yield _result
                _result[:] = []
        else:
            yield _result

    def _report_status(self, prefix, stats, remove):
        self.stdout.write('{}: {}, checked {} items ({} ok, {} delete)'.format(
            prefix,
            'All OK' if stats['total'] == stats['ok'] else 'Cleaned up' if remove else 'Cleanup required',
            stats['total'],
            stats['ok'],
            stats['delete']))

