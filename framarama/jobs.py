import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_SUBMITTED, EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

class Scheduler:

    def __init__(self):
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_listener(self._event_start, EVENT_JOB_SUBMITTED)
        self._scheduler.add_listener(self._event_success, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._event_error, EVENT_JOB_ERROR)
        self._running = []

    def _event_start(self, event):
        self._running.append(event.job_id)

    def _event_success(self, event):
        self._running.remove(event.job_id)

    def _event_error(self, event):
        self._running.remove(event.job_id)

    def running(self, name, starts_with=False):
        if starts_with:
            _compare = lambda job: job.startswith(name)
        else:
            _compare = lambda job: job == name
        return len([_job for _job in self._running if _compare(_job)])

    def jobs(self):
        return self._scheduler.get_jobs()

    def add(self, func, *args, **kwargs):
        _func_args = kwargs.pop('func_args', {})
        _func_kwargs = kwargs.pop('func_kwargs', {})
        self._scheduler.add_job(lambda *args, **kwargs: func(*args, **kwargs), args=_func_args, kwargs=_func_kwargs, *args, **kwargs)

    def remove(self, name):
        self._scheduler.remove_job(name)

    def trigger(self, name, *func_args, **func_kwargs):
        _job = self.get(name)
        _job_id = _job.id + '_' + str(time.time())
        self._scheduler.add_job(_job.func, id=_job_id, args=func_args, kwargs=func_kwargs)
        return _job_id

    def get(self, name):
        return self._scheduler.get_job(name)

    def setup(self, module):
        self._scheduler.start()

        if (hasattr(module, 'Jobs')):
            module.Jobs(self)

