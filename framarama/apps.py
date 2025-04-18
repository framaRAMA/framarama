import sys

from django.conf import settings
from django.apps import AppConfig

from framarama import jobs


class BaseAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'

    def get_scheduler(self):
        return self._scheduler

    def setup(self):
        pass

    def ready(self):
        is_manage_py = any(arg.casefold().endswith("manage.py") for arg in sys.argv)
        is_runserver = any(arg.casefold() == "runserver" for arg in sys.argv)

        # Instance is running application (no service tasks or other commands)
        #if (is_manage_py and is_runserver) or (not is_manage_py):
        if is_manage_py and not is_runserver:
            return

        self.setup()

