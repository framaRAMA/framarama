from apscheduler.schedulers.background import BackgroundScheduler
from config import jobs as config_jobs
from api import jobs as api_jobs
from frontend import jobs as frontend_jobs


class Scheduler:

    def __init__(self):
        self._scheduler = BackgroundScheduler()

    def jobs(self):
        return self._scheduler.get_jobs()

    def add(self, func, *args, **kwargs):
        self._scheduler.add_job(lambda: func(), *args, **kwargs)

    def setup(self):
        self._scheduler.start()

        for module in [config_jobs, api_jobs, frontend_jobs]:
            if (hasattr(module, 'Jobs')):
                _jobs = module.Jobs(self)


