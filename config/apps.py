
from django.conf import settings

from framarama import apps


class ConfigAppConfig(apps.BaseAppConfig):
    name = 'config'

    def setup(self):
        if 'server' not in settings.FRAMARAMA['MODES']:
            return
        from config import jobs
        self._scheduler = jobs.Scheduler()
        self._scheduler.start()

