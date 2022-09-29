import sys

from django.apps import AppConfig


class FrontendConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'frontend'

    def ready(self):
        is_manage_py = any(arg.casefold().endswith("manage.py") for arg in sys.argv)
        is_runserver = any(arg.casefold() == "runserver" for arg in sys.argv)

        # Instance is running application (no service tasks or other commands)
        if (is_manage_py and is_runserver) or (not is_manage_py):
            from framarama.jobs import Scheduler
            scheduler = Scheduler()
            scheduler.setup()

