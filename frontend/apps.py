
from framarama import apps


class FrontendAppConfig(apps.BaseAppConfig):
    name = 'frontend'

    def setup_frontend(self):
        from frontend import jobs
        self._scheduler = jobs.Scheduler()
        self._scheduler.start()

