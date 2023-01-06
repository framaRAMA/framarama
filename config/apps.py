
from framarama import apps


class ConfigAppConfig(apps.BaseAppConfig):
    name = 'config'

    def setup_server(self):
        from config import jobs
        self.get_scheduler().setup(jobs)

