
from framarama import apps


class FrontendAppConfig(apps.BaseAppConfig):
    name = 'frontend'

    def setup_frontend(self):
        from frontend import jobs
        self.get_scheduler().setup(jobs)

