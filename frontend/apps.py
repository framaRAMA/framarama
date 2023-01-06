import sys

from django.apps import AppConfig

from framarama import settings


class FrontendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'frontend'

    def get_scheduler(self):
        return self._scheduler

    def ready(self):
        if 'frontend' not in settings.FRAMARAMA['MODES']:
            return

        is_manage_py = any(arg.casefold().endswith("manage.py") for arg in sys.argv)
        is_runserver = any(arg.casefold() == "runserver" for arg in sys.argv)

        # Instance is running application (no service tasks or other commands)
        if (is_manage_py and is_runserver) or (not is_manage_py):
            from framarama.jobs import Scheduler
            from frontend import jobs
            self._scheduler = Scheduler()
            self._scheduler.setup(jobs)

