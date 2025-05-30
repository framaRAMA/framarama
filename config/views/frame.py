
from django.conf import settings
from django.views.generic import RedirectView
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError

from framarama.base import utils
from framarama.base.forms import UploadFieldForm
from config import jobs
from config import models
from config import plugins
from config.forms import frame as forms
from config.views import base
from config.utils import source
from config.utils import sorting
from config.utils import finishing
from api.views.config import RankedItemFrameSerializer


class CreateFrameView(base.BaseConfigView):
    template_name = 'config/frame.create.html'

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _context['form'] = forms.CreateFrameForm()
        return _context

    def _post(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _form = forms.CreateFrameForm(request.POST)
        if _form.is_valid():
            _frame = models.Frame(user=request.user, name=_form.cleaned_data['name'], description=_form.cleaned_data['description'], enabled=_form.cleaned_data['enabled'])
            _frame.save()
            self.redirect(_context, 'frame_info', args=[_frame.id])
        _context['form'] = _form
        return _context


class ListFrameView(base.BaseConfigView):
    template_name = 'config/frame.list.html'


class ThumbnailFrameView(base.BaseFrameConfigView):

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _items = self.qs().items.filter(frame__id=frame_id, thumbnail__isnull=False).order_by('?').all()[:1]
        self.response_item_thumbnail(_context, _items[0] if len(_items) else None)
        return _context


class ViewInfoFrameView(base.BaseFrameConfigView):
    template_name= 'config/frame.info.html'


class ActionFrameView(base.BaseFrameConfigView):

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _action = request.GET['action']
        if _action == 'delete':
            _frame.delete()
        self.redirect(_context, 'frame_list')
        return _context


class UpdateGeneralFrameView(base.BaseFrameConfigView):
    template_name = 'config/frame.general.html'

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _context['form'] = forms.UpdateFrameForm(instance=_frame)
        return _context

    def _post(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _form = forms.UpdateFrameForm(request.POST, instance=_frame)
        if _form.is_valid():
            _form.save()
            self.redirect(_context, 'frame_info', args=[_frame.id])
        _context['form'] = _form
        return _context


class CreateSourceFrameView(base.BaseFrameConfigView):
    template_name = 'config/frame.source.create.html'

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _context['form'] = forms.CreateSourceForm()
        return _context

    def _post(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _form = forms.CreateSourceForm(request.POST)
        if _form.is_valid():
            _source = models.Source(name=_form.cleaned_data['name'])
            _source.frame = _context['frame']
            _source.save()
            self.redirect(_context, 'frame_source_info', args=[_frame.id, _source.id])
        _context['form'] = _form
        return _context


class UpdateSourceFrameView(base.BaseSourceFrameConfigView):
    template_name = 'config/frame.source.update.html'

    def _get(self, request, frame_id, source_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _source = _context['source']
        _context['form'] = forms.UpdateSourceForm(instance=_source)
        return _context

    def _post(self, request, frame_id, source_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _frame = _context['frame']
        _source = _context['source']
        _form = forms.UpdateSourceForm(request.POST, instance=_source)
        if _form.is_valid():
            _form.save()
            self.redirect(_context, 'frame_source_info', args=[_frame.id, _source.id])
        _context['form'] = _form
        return _context


class ActionSourceFrameView(base.BaseSourceFrameConfigView):

    def _get(self, request, frame_id, source_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _frame = _context['frame']
        _source = _context['source']
        _action = request.GET['action']
        if _action == 'delete':
            _source.delete()
            self.redirect(_context, 'frame_source_list', args=[_frame.id])
        elif _action == 'run':
            _scheduler = self.get_scheduler()
            _scheduler.trigger_job(jobs.Scheduler.CFG_SOURCE_UPDATE, instance=[_frame.id, _source.id], frame=_frame, source=_source)
            self.redirect(_context, 'frame_source_step_list', args=[_frame.id, _source.id])
        return _context


class RedirectSourceFrameView(base.BaseFrameConfigView):

    def _get(self, request, *args, **kwargs):
        _context = super()._get(request, *args, **kwargs)
        _frame = _context['frame']
        _sources = _frame.sources.all()
        if _sources:
            self.redirect(_context, 'frame_source_info', args=[_frame.id, _sources[0].id])
        else:
            self.redirect(_context, 'frame_source_create', args=[_frame.id])
        return _context


class RedirectInfoSourceFrameView(RedirectView):
    permanent = False
    pattern_name = 'frame_source_info'


class ViewInfoSourceFrameView(base.BaseSourceFrameConfigView):
    template_name = 'config/frame.source.info.html'

    def _get(self, request, frame_id, source_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _context['source_running'] = self.get_scheduler().running_jobs(
            jobs.Scheduler.CFG_SOURCE_UPDATE,
            instance=[frame_id, source_id],
            starts_with=True)
        return _context


class ListStepSourceFrameView(base.BaseSourceFrameConfigView):
    template_name = 'config/frame.source.step.list.html'

    def _get(self, request, frame_id, source_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _context['source_plugins'] = plugins.SourcePluginRegistry.all()
        _context['source_running'] = self.get_scheduler().running_jobs(
            jobs.Scheduler.CFG_SOURCE_UPDATE,
            instance=frame_id,
            starts_with=True)
        return _context


class CreateStepSourceFrameView(base.BaseSourceFrameConfigView):
    template_name = 'config/frame.source.step.create.html'
    
    def _get(self, request, frame_id, source_id, plugin, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _plugin = plugins.SourcePluginRegistry.get(plugin)
        _context['plugin'] = _plugin
        _context['form'] = _plugin.get_form()
        return _context

    def _post(self, request, frame_id, source_id, plugin, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _plugin = plugins.SourcePluginRegistry.get(plugin)
        _frame = _context['frame']
        _source = _context['source']
        _form = _plugin.get_form(request.POST)
        if _form.is_valid():
            _form.save(_plugin, defaults={'source': _source}, models=_source.steps)
            self.redirect(_context, 'frame_source_step_list', args=[_frame.id, _source.id])
        _context['plugin'] = _plugin
        _context['form'] = _form
        return _context


class UpdateStepSourceFrameView(base.BaseStepSourceFrameConfigView):
    template_name = 'config/frame.source.step.update.html'
    
    def _get(self, request, frame_id, source_id, step_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, step_id, *args, **kwargs)
        _plugin = _context['plugin']
        _source_step = _context['source_step']
        _form = _plugin.get_form(instance=_source_step)
        _context['form'] = _form
        return _context

    def _post(self, request, frame_id, source_id, step_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, step_id, *args, **kwargs)
        _frame = _context['frame']
        _source = _context['source']
        _plugin = _context['plugin']
        _source_step = _context['source_step']
        _form = _plugin.get_form(request.POST, instance=_source_step)
        if _form.is_valid():
            _form.save(_plugin)
            self.redirect(_context, 'frame_source_step_list', args=[_frame.id, _source.id])
        _context['form'] = _form
        return _context


class ActionStepSourceFrameView(base.BaseStepSourceFrameConfigView):

    def _get(self, request, frame_id, source_id, step_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, step_id, *args, **kwargs)
        _frame = _context['frame']
        _source = _context['source']
        _source_step = _context['source_step']
        _action = request.GET['action']
        if _action == 'delete':
            self._item_order_delete(_source_step.pk, _source.steps)
        elif _action == 'up' or _action == 'down':
            self._item_order_move(_action, _source_step, _source.steps)
        self.redirect(_context, 'frame_source_step_list', args=[_frame.id, _source.id])
        return _context


class PathsStepSourceFrameView(base.BaseStepSourceFrameConfigView):

    def _post(self, request, frame_id, source_id, step_id, *args, **kwargs):
        _context = super()._post(request, frame_id, source_id, step_id, *args, **kwargs)
        _frame = _context['frame']
        _root = utils.Filesystem.path_normalize(settings.FRAMARAMA['MEDIA_PATH'], absolute=True)
        if _root:
            _path = request.POST.get('path', '')
            _path = utils.Filesystem.path_normalize(_path, root=_root, absolute=True) if _path != '' else _root
            _items = []
            for _item in utils.Filesystem.file_match(_path, '.*', files=False, dirs=True):
                _items.append({'name': _item[0]})
            self.response_json(_context, {'path': _path.replace(_root, '').strip('/'), 'items': _items})
        else:
            self.response_json(_context, {'path': '', 'items': _items})
        return _context


class ItemsSourceFrameView(base.BaseSourceFrameConfigView):
    template_name = 'config/frame.source.items.html'

    def _get(self, request, frame_id, source_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _source = self.qs().sources.filter(pk=source_id).get()
        _search = request.GET.get('search', '')
        _page = request.GET.get('page')
        _page_size = request.GET.get('page_size', 20)
        if _search:
            _items = _source.items.filter(url__icontains=_search)
        else:
            _items = _source.items.all()
        _context['items'] = Paginator(_items.order_by('created'), _page_size).get_page(_page)
        _context['search'] = _search

        _scheduler = self.get_scheduler()
        _action = request.GET.get('action')
        _id = request.GET.get('id')
        _item = list(self.qs().items.filter(pk=_id)) if _id else None
        _job_id = jobs.Scheduler.CFG_ITEM_THUMBNAIL
        _running = [_job.split('_')[-1] for _job in _scheduler.running_jobs(_job_id, instance=frame_id, starts_with=True, names=True)]
        if _action == 'item.thumbnail.generate' and len(_item):
            if len(_running) == 0:
                _scheduler.trigger_job(_job_id, instance=_id, item=_item[0])
        elif _action == 'item.thumbnail.delete' and len(_item):
            if _item[0].thumbnail:
                _item[0].thumbnail.data_file.delete()
                _item[0].thumbnail.delete()
        _context['running'] = _running
        return _context


class ThumbnailItemFrameView(base.BaseSourceFrameConfigView):

    def _get(self, request, frame_id, source_id, item_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _items = list(self.qs().items.filter(pk=item_id))
        self.response_item_thumbnail(_context, _items[0] if len(_items) else None)
        return _context


class DownloadItemFrameView(base.BaseSourceFrameConfigView):

    def _get(self, request, frame_id, source_id, item_id, *args, **kwargs):
        _context = super()._get(request, frame_id, source_id, *args, **kwargs)
        _items = list(self.qs().items.filter(pk=item_id))
        self.response_item_download(_context, _items[0] if len(_items) else None)
        return _context


class ListSortingFrameView(base.BaseFrameConfigView):
    template_name = 'config/frame.sorting.html'

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _context['sortings'] = _frame.sortings.all()
        _context['sorting_plugins'] = plugins.SortingPluginRegistry.all()
        
        _page = request.GET.get('page')
        _page_size = request.GET.get('page_size', 20)
        _processor = sorting.Processor(sorting.Context(_frame))
        _result = _processor.process()
        _result['items'] = Paginator(_result['items'], _page_size).get_page(_page)
        _context.update(_result)

        return _context


class CreateSortingFrameView(base.BaseFrameConfigView):
    template_name = 'config/frame.sorting.create.html'

    def _get(self, request, frame_id, plugin, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _plugin = plugins.SortingPluginRegistry.get(plugin)
        _context['plugin'] = _plugin
        _context['form'] = _plugin.get_form()
        return _context

    def _post(self, request, frame_id, plugin, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _plugin = plugins.SortingPluginRegistry.get(plugin)
        _frame = _context['frame']
        _form = _plugin.get_form(request.POST)
        if _form.is_valid():
            _form.save(_plugin, defaults={'frame': _frame}, models=_frame.sortings)
            self.redirect(_context, 'frame_sorting_list', args=[_frame.id])
        _context['plugin'] = _plugin
        _context['form'] = _form
        return _context


class UpdateSortingFrameView(base.BaseSortingFrameConfigView):
    template_name = 'config/frame.sorting.edit.html'

    def _get(self, request, frame_id, sorting_id, *args, **kwargs):
        _context = super()._get(request, frame_id, sorting_id, *args, **kwargs)
        _sorting = _context['sorting']
        _sorting_plugin = plugins.SortingPluginRegistry.get(_sorting.plugin)
        _form = _sorting_plugin.get_form(instance=_sorting)
        _context['form'] = _form
        return _context

    def _post(self, request, frame_id, sorting_id, *args, **kwargs):
        _context = super()._get(request, frame_id, sorting_id, *args, **kwargs)
        _frame = _context['frame']
        _sorting = _context['sorting']
        _sorting_plugin = plugins.SortingPluginRegistry.get(_sorting.plugin)
        _form = _sorting_plugin.get_form(request.POST, instance=_sorting)
        if _form.is_valid():
            _form.save(_sorting_plugin)
            self.redirect(_context, 'frame_sorting_list', args=[_frame.id])
        _context['form'] = _form
        return _context


class ActionSortingFrameView(base.BaseSortingFrameConfigView):

    def _get(self, request, frame_id, sorting_id, *args, **kwargs):
        _context = super()._get(request, frame_id, sorting_id, *args, **kwargs)
        _frame = _context['frame']
        _sorting = _context['sorting']
        _action = request.GET['action']
        if _action == 'delete':
            self._item_order_delete(_sorting.pk, _frame.sortings)
        self.redirect(_context, 'frame_sorting_list', args=[_frame.id])
        return _context

class EvalSortingFrameView(base.BaseSortingFrameConfigView):

    def _post(self, request, frame_id, sorting_id, *args, **kwargs):
        _context = super()._post(request, frame_id, sorting_id, *args, **kwargs)
        _frame = _context['frame']
        _code= request.POST.get('code')
        _page= request.POST.get('page') or 0
        _page_size = request.POST.get('page_size') or 20
        if settings.FRAMARAMA['CONFIG_SORTING_EVAL_QUERY'] and _code:
            try:
                _plugin = plugins.SortingPluginRegistry.get('custom')
                _custom = _plugin.create_model()
                _custom.weight = 1
                _custom.enabled = True
                _custom.plugin = 'custom'
                _custom.plugin_config['code'] = _code

                if int(_page_size) > 100:
                    _page_size = 100

                _processor = sorting.Processor(sorting.Context(_frame, sortings=[_custom]))
                _result = _processor.process()
                _result['items'] = Paginator(_result['items'], _page_size).get_page(_page)
                _items = []
                for _item in _result['items']:
                    _serializer = RankedItemFrameSerializer(_item)
                    _items.append(_serializer.data)
                self.response_json(_context, {
                    'start': _result['items'].start_index(),
                    'end': _result['items'].end_index(),
                    'error': ', '.join([str(_e) for _i, _e in _result['errors'].items()]) if _result['errors'] else None,
                    'page': _page,
                    'items': _items
                })
            except Exception as e:
                self.response_json(_context, {'items': [], 'error': str(e)})
        else:
            self.response_json(_context, {'items': []})
        return _context


class ListFinishingFrameView(base.BaseFrameConfigView):
    template_name = 'config/frame.finishing.html'

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _open = request.GET.get('open', '').split(',')
        _opens = []
        _frame = _context['frame']
        _finishings = []
        _id_path = [0]  # root item
        for (_finishing, _tree) in _frame.finishings.annotated():
            if len(_id_path) < _finishing.depth - 1:
                _id_path.append(_depth)
            else:
                while len(_id_path) > _finishing.depth - 1:
                    _id_path.pop()
            _depth = str(_finishing.id)
            _plugin = plugins.FinishingPluginRegistry.get(_finishing.plugin)
            _finishings.append({
                'entity': _finishing,
                'tree': _tree,
                'path': '-'.join(_id_path[1:] + [_depth])  # skip root item
            })
            if _open and str(_finishing.id) in _open:
                _opens.append(_finishings[-1]['path'])
        _context['finishings'] = _finishings
        _context['finishing_plugins'] = plugins.FinishingPluginRegistry.all()
        _context['finishing_opens'] = _opens
        _context['form_import'] = UploadFieldForm()
        return _context


class CreateFinishingFrameView(base.BaseFrameConfigView):
    template_name = 'config/frame.finishing.create.html'

    def _get(self, request, frame_id, plugin, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _plugin = plugins.FinishingPluginRegistry.get(plugin)
        _context['plugin'] = _plugin
        _context['form'] = _plugin.get_form()
        return _context

    def _post(self, request, frame_id, plugin, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _plugin = plugins.FinishingPluginRegistry.get(plugin)
        _frame = _context['frame']
        _form = _plugin.get_form(request.POST)
        if _form.is_valid():
            _defaults = {'frame': _frame}
            _finishing = _form.save(plugin=_plugin, models=_frame.finishings, defaults=_defaults, base_values=False)
            self.redirect_finishing_list(_context, _finishing, args=[_frame.id])
        _context['plugin'] = _plugin
        _context['form'] = _form
        return _context


class UpdateFinishingFrameView(base.BaseFinishingFrameConfigView):
    template_name = 'config/frame.finishing.update.html'

    def _get(self, request, frame_id, finishing_id, *args, **kwargs):
        _context = super()._get(request, frame_id, finishing_id, *args, **kwargs)
        _finishing = _context['finishing']
        _plugin = plugins.FinishingPluginRegistry.get(_finishing.plugin)
        _form = _plugin.get_form(instance=_finishing)
        _context['form'] = _form
        return _context

    def _post(self, request, frame_id, finishing_id, *args, **kwargs):
        _context = super()._get(request, frame_id, finishing_id, *args, **kwargs)
        _frame = _context['frame']
        _finishing = _context['finishing']
        _plugin = plugins.FinishingPluginRegistry.get(_finishing.plugin)
        _form = _plugin.get_form(request.POST, instance=_finishing)
        if _form.is_valid():
            _form.save(plugin=_plugin)
            self.redirect_finishing_list(_context, _finishing, args=[_frame.id])
        _context['form'] = _form
        return _context


class ActionFinishingFrameView(base.BaseFinishingFrameConfigView):

    def _get(self, request, frame_id, finishing_id, *args, **kwargs):
        _context = super()._get(request, frame_id, finishing_id, *args, **kwargs)
        _frame = _context['frame']
        _finishing = _context['finishing']
        _action = request.GET['action']
        if _action == 'delete':
            self._item_order_delete(_finishing.pk, _frame.finishings)
            self.redirect(_context, 'frame_finishing_list', args=[_frame.id])
        elif _action in ['up', 'down', 'up-out', 'down-in']:
            self._item_order_move(_action, _finishing, _frame.finishings)
            self.redirect_finishing_list(_context, _finishing, args=[_frame.id])
        elif _action in ['move-after', 'move-before', 'first-child']:
            self._item_order_move(_action, _finishing, _frame.finishings, request.GET['target'])
            self.redirect_finishing_list(_context, _finishing, args=[_frame.id])
        return _context


class ExportFinishingFrameView(base.BaseFrameConfigView):

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _config = plugins.FinishingPluginRegistry.export_config(
            'export.frame.{}.finishings'.format(frame_id),
            'Finishing export of frame #{}'.format(frame_id),
            _frame.finishings)
        self.response_download(_context, _config, 'application/json')
        return _context


class ImportFinishingFrameView(base.BaseFrameConfigView):

    def _post(self, request, frame_id, *args, **kwargs):
        _context = super()._post(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _form = UploadFieldForm(request.POST, request.FILES)
        if _form.is_valid():
            _upload = request.FILES['upload']
            if _upload.size > 1024*1024:
                raise ValidationError('Upload too large (limit 1 MB)')
            try:
                _config = utils.Json.to_dict(_upload.read())
            except Exception as e:
                raise ValidationError('Can not parse JSON: ' + str(e))
            plugins.FinishingPluginRegistry.import_config(
                _config['data'],
                _frame.finishings,
                {'frame': _frame})
        self.response_json(_context, {})
        return _context


class RawEditFinishingFrameView(base.BaseFrameConfigView):
    template_name = 'config/frame.finishing.rawedit.html'

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _config = plugins.FinishingPluginRegistry.export_config(
            'export.frame.{}.finishings'.format(frame_id),
            'Finishing export of frame #{}'.format(frame_id),
            _frame.finishings,
            plugins.PluginRegistry.EXPORT_DICT, True)
        _form = forms.RawEditFinishingForm(initial={"config": _config})
        _context['form'] = _form
        return _context

    def _post(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _form = forms.RawEditFinishingForm(request.POST)
        if _form.is_valid():
            plugins.FinishingPluginRegistry.import_config(
                _form.cleaned_data['config'],
                _frame.finishings,
                {'frame': _frame})
            self.redirect(_context, 'frame_finishing_list', args=[_frame.id])
        _context['form'] = _form
        return _context


class PreviewImageFrameView(base.BaseFrameConfigView):

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _items = _frame.items
        _items = _items.filter(id=request.GET['id']) if 'id' in request.GET else _items
        _items = _items.order_by('?').all()
        _paginator = Paginator(_items, 1)
        _page = _paginator.get_page(0)
        _item = _page.object_list[0] if len(_page.object_list) else None
        _width = request.GET['w'] if 'w' in request.GET else 1024
        _height = request.GET['h'] if 'h' in request.GET else 768
        _display = models.Display(**{'name': 'Preivew display', 'description': 'Display for preparing previews', 'enabled': True, 'device_width': int(_width), 'device_height': int(_height)})
        if _item:
            _finishing_context = finishing.Context(
                _display,
                _frame,
                _frame.contexts.all(),
                _item,
                _frame.finishings.all(),
                _frame.get_variables(),
                finishing.ImageProcessingAdapter.get_default())
            with _finishing_context:
                _result = finishing.Processor(_finishing_context).process()
                self.response(_context, _result.get_image_data(), _result.get_image_mime())
        else:
            self.response(_context, '', 'text/plain')
        return _context


class ListContextFrameView(base.BaseFrameConfigView):
    template_name = 'config/frame.context.list.html'

    def _get(self, request, frame_id, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _frame = _context['frame']
        _context['contexts'] = _frame.contexts.all()
        _context['context_plugins'] = plugins.ContextPluginRegistry.all()
        return _context


class CreateContextFrameView(base.BaseFrameConfigView):
    template_name = 'config/frame.context.create.html'

    def _get(self, request, frame_id, plugin, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _plugin = plugins.ContextPluginRegistry.get(plugin)
        _context['plugin'] = _plugin
        _context['form'] = _plugin.get_form()
        return _context

    def _post(self, request, frame_id, plugin, *args, **kwargs):
        _context = super()._get(request, frame_id, *args, **kwargs)
        _plugin = plugins.ContextPluginRegistry.get(plugin)
        _frame = _context['frame']
        _form = _plugin.get_form(request.POST)
        if _form.is_valid():
            _form.save(_plugin, defaults={'frame': _frame}, models=_frame.contexts)
            self.redirect(_context, 'frame_context_list', args=[_frame.id])
        _context['plugin'] = _plugin
        _context['form'] = _form
        return _context


class UpdateContextFrameView(base.BaseContextFrameConfigView):
    template_name = 'config/frame.context.update.html'

    def _get(self, request, frame_id, context_id, *args, **kwargs):
        _context = super()._get(request, frame_id, context_id, *args, **kwargs)
        _frame_context = _context['context']
        _context_plugin = plugins.ContextPluginRegistry.get(_frame_context.plugin)
        _form = _context_plugin.get_form(instance=_frame_context)
        _context['form'] = _form
        return _context

    def _post(self, request, frame_id, context_id, *args, **kwargs):
        _context = super()._get(request, frame_id, context_id, *args, **kwargs)
        _frame = _context['frame']
        _frame_context = _context['context']
        _context_plugin = plugins.ContextPluginRegistry.get(_frame_context.plugin)
        _form = _context_plugin.get_form(request.POST, instance=_frame_context)
        if _form.is_valid():
            _form.save(_context_plugin)
            self.redirect(_context, 'frame_context_list', args=[_frame.id])
        _context['form'] = _form
        return _context


class ActionContextFrameView(base.BaseContextFrameConfigView):

    def _get(self, request, frame_id, context_id, *args, **kwargs):
        _context = super()._get(request, frame_id, context_id, *args, **kwargs)
        _frame = _context['frame']
        _frame_context = _context['context']
        _action = request.GET['action']
        if _action == 'delete':
            self._item_order_delete(_frame_context.pk, _frame.contexts)
        elif _action == 'up' or _action == 'down':
            self._item_order_move(_action, _frame_context, _frame.contexts)
        self.redirect(_context, 'frame_context_list', args=[_frame.id])
        return _context


