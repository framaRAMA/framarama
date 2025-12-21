
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from framarama.base import utils
from config import models

class Command(BaseCommand):
    help = 'Manage internal configuration settings for users'

    def add_arguments(self, parser):
        parser.add_argument('--user', help='Manage settings of given users by username', type=str)
        parser.add_argument('--set', action='append', help='Set given setting to given value')

    def handle(self, *args, **options):
        _user = get_user_model().objects.filter(username=options['user']).get()
        _settings = list(models.Settings.objects.filter(user=_user, category=models.Settings.CAT_INT_USER_CFG).all())
        if len(_settings) == 0:
            _settings = models.Settings(user=_user, category=models.Settings.CAT_INT_USER_CFG, name='user.config')
        else:
            _settings = _settings[0]
        if options['set']:
            _values = [_opt.split('=', 1) if '=' in _opt else (_opt, None) for _opt in options['set']]
            _settings.properties.update(_values)
            _settings.save()
        print('Listing {} settings for {}:'.format(len(_settings.properties), _user))
        for _name, _value in _settings.properties.items():
            print('- {} = {}'.format(_name, _value))
        print('Done.');
