
from django.core.management.base import BaseCommand

from framarama.base import utils
from config.models import base as models

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
                lambda ids: [(_id, _id) for _id in ids if utils.Filesystem.file_exists(_id)],
                lambda item: item.delete()
            ])
        if _fs or not _db:
            _processes.append([
                'Filesystem',
                self._fs_items,
                lambda ids: [(_item.data_file.name, _item) for _item in models.Data.objects.filter(data_file__in=ids)],
                lambda item: utils.Filesystem.file_delete(item)
            ])
        for _name, _generator, _check, _delete in _processes:
            self.stdout.write('{}: Checking items'.format(_name))
            _stats = utils.Lists.process(
                source=_generator(),
                target_match=_check,
                size=_chunk,
                delete_func=lambda id, tval: print("delete {} {}".format(id, tval)))
            self._report_status(_name, _stats, _rm)

    def _db_items(self):
        for _item in models.Data.objects.all():
            yield _item.data_file.name, _item

    def _fs_items(self):
        _skip = [models.Data, models.BaseImageData]
        _classes = utils.Classes.subclasses(models.Data)
        for _clazz in [_clazz for _clazz in _classes if _clazz not in _skip]:
            _path = _clazz.path().replace('./', '')
            self.stdout.write('Filesystem: Reading items in {}'.format(_path))
            _dirs = utils.Filesystem.file_match(_path, '.*', files=False, dirs=True, recurse=1)
            for _dir in [_dir[0] for _dir in _dirs if '/' in _dir[0]]:
                for _item in utils.Filesystem.file_match(_path + '/' + _dir, '.*'):
                    _filename = _path + '/' + _dir + '/' + _item[0]
                    yield _filename, _filename

    def _report_status(self, prefix, stats, remove):
        self.stdout.write('{}: {}, checked {} items ({} ok, {} delete)'.format(
            prefix,
            'All OK' if stats['total'] == stats['update'] else 'Cleaned up' if remove else 'Cleanup required',
            stats['total'],
            stats['update'],
            stats['delete']))

