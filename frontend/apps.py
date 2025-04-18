
from django.conf import settings

from framarama import apps


class FrontendAppConfig(apps.BaseAppConfig):
    name = 'frontend'

    def setup(self):
        if 'frontend' not in settings.FRAMARAMA['MODES']:
            return
        from frontend import jobs
        self._scheduler = jobs.Scheduler()
        self._scheduler.start()

