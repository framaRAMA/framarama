
from django.core.management.base import BaseCommand

from framarama.base import utils
from frontend import models

class Command(BaseCommand):
    help = 'Create or change initial system setup'

    def add_arguments(self, parser):
        parser.add_argument('--set', action='append', help='Set a given field to given value')

    def handle(self, *args, **options):
        _config = utils.Config.get().get_config()
        _config = _config if _config else models.Config()
        _fields = sorted(vars(_config))
        self._dump('Current values:', _config, _fields)
        _values = options['set'] if options['set'] else []
        _values = [_opt.split('=', 1) if '=' in _opt else (_opt, None) for _opt in _values]
        _wrong = [_n for _n, _v in _values if _n not in _fields]
        if len(_wrong):
            self.stderr.write("Wrong values specified: {}".format(_wrong))
            return
        if len(_values) == 0:
            return
        for _name, _value in _values:
            if _value is None:
                _value = input('Value for {}: '.format(_name))
            setattr(_config, _name, _value)
        self._dump('Updated values:', _config, [_n for _n, _v in _values])
        _config.save()

    def _dump(self, title, config, fields):
        self.stdout.write(title)
        for _field in fields:
            if _field[0] == '_':
                continue
            self.stdout.write("- {} = {}".format(_field, getattr(config, _field)))

