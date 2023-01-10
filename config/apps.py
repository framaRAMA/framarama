
from framarama import apps


class ConfigAppConfig(apps.BaseAppConfig):
    name = 'config'

    def setup_server(self):
        from config import jobs
        self._scheduler = jobs.Scheduler()
        self._scheduler.start()

