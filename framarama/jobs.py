import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_SUBMITTED, EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

class Scheduler:
    JOB_PARAM_FUNC = '__func'
    JOB_PARAM_NAME = 'name'

    def __init__(self):
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_listener(self._event_start, EVENT_JOB_SUBMITTED)
        self._scheduler.add_listener(self._event_success, EVENT_JOB_EXECUTED)
        self._scheduler.add_listener(self._event_error, EVENT_JOB_ERROR)
        self._running = []
        self._jobs = {}

    def _event_start(self, event):
        self._running.append(event.job_id)

    def _event_success(self, event):
        self._running.remove(event.job_id)

    def _event_error(self, event):
        self._running.remove(event.job_id)

    def _add_job(self, job_id, func, *args, **kwargs):
        _func_args = kwargs.pop('func_args', {})
        _func_kwargs = kwargs.pop('func_kwargs', {})
        self._scheduler.add_job(lambda *args, **kwargs: func(*args, **kwargs), id=job_id, args=_func_args, kwargs=_func_kwargs, *args, **kwargs)

    def run_job(self, job_id, func, *args, **kwargs):
        self._add_job(job_id, func, *args, **kwargs)

    def add_job(self, job_id, func, *args, **kwargs):
        self._add_job(job_id, func, trigger='interval', *args, **kwargs)

    def remove_job(self, job_id):
        self._scheduler.remove_job(job_id)

    def get_job(self, job_id):
        return self._scheduler.get_job(job_id)

    def register_job(self, job_id, func, **kwargs):
        _job = kwargs.copy()
        _job[Scheduler.JOB_PARAM_FUNC] = func
        self._jobs[job_id] = _job

    def enable_job(self, job_id):
        if job_id in self._jobs and not self.get_job(job_id):
            _job = self._jobs.get(job_id).copy()
            _func = _job.pop(Scheduler.JOB_PARAM_FUNC)
            self.add_job(job_id, _func, **_job)

    def enable_jobs(self, job_ids=None):
        for job_id in job_ids if job_ids else self._jobs.keys():
            self.enable_job(job_id)

    def disable_job(self, job_id):
        if job_id in self._jobs and self._scheduler.get_job(job_id):
            self.remove_job(job_id)

    def disable_jobs(self, job_ids=None):
        for job_id in job_ids if job_ids else self._jobs.keys():
            self.disable_job(job_id)

    def trigger_job(self, job_id, *args, **kwargs):
        if job_id in self._jobs:
            _job = self._jobs.get(job_id)
            _func = _job.get(Scheduler.JOB_PARAM_FUNC)
            _name = _job.get(Scheduler.JOB_PARAM_NAME) + ' triggered'
            _job_id = job_id + '_' + str(time.time())
            self.run_job(_job_id, _func, name=_name, func_args=args, func_kwargs=kwargs)
            return _job_id

    def running_jobs(self, job_id, starts_with=False):
        if starts_with:
            _compare = lambda job: job.startswith(job_id)
        else:
            _compare = lambda job: job == job_id
        return len([_job for _job in self._running if _compare(_job)])

    def configure(self):
        pass

    def start(self):
        self._scheduler.start()
        self.configure()

