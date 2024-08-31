import base64
import mimetypes

from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from django.http import StreamingHttpResponse
from rest_framework import generics, viewsets, mixins, permissions, serializers, decorators, response
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.reverse import reverse

from framarama.base import utils
from framarama.base.views import BaseQuerySetMixin
from config import models
from config.utils import sorting, finishing
from api import auth


class BaseSerializer(serializers.ModelSerializer):
    links = serializers.SerializerMethodField()

    class Meta:
        fields = ('id', 'links',)
        read_only_fields = ('id', 'links',)

    def _link(self, name, href=None, template=None):
        # Examples:
        # { "rel": "action", "href": "http://domain/entity/1/action" },
        # { "rel": "self", "href": "http://domain/entities/1" },
        # { "rel": "others", "href": "http://domain/entitie/1/others" },
        # { "rel": "search", "template": "http://domain/search?keyword={query}" },
        # { "rel": "add", "target": "http://domain/entities/add", "template": { "name" : ..., "state": ... } }
        _link = {'rel': name}
        if href:
          _link['href'] = href
        if template:
          _link['template'] = template
        return _link

    def _link_view(self, name, view, args):
        return self._link(name, href=self.reverse(view, args))

    def get_links(self, obj):
        return ()

    def get_request(self):
        return self.context.get('request')

    def get_kwargs(self):
        return self.get_request().parser_context['kwargs'] if self.get_request() else {}

    def reverse(self, view_name, args):
        return reverse(view_name, args=args, request=self.get_request())

    def map(self, data, validated_data):
        _instance = self.Meta.model(**validated_data)
        if hasattr(self.Meta, 'map_fields'):
            for _name in [_name for _name in self.Meta.map_fields if _name in data]:
                setattr(_instance, _name, data.get(_name))
        return _instance

    def map_fields(self, data, validated_data, fields):
        for _name, _field in self.fields.items():
            if _name not in fields:
                continue
            if isinstance(_field, BaseSerializer):
                serializer = type(_field)(data=validated_data.get(_name, {}))
                serializer.is_valid()
                validated_data[_name] = serializer.map(data.get(_name, {}), serializer.validated_data)
            elif _name in data:
                validated_data[_name] = data.get(_name)
        return validated_data


class FrameSerializer(BaseSerializer):

    class Meta:
        model = models.Frame
        fields = BaseSerializer.Meta.fields + ('name', 'description', 'enabled')
        read_only_fields = BaseSerializer.Meta.read_only_fields
        map_fields = BaseSerializer.Meta.fields

    def get_links(self, obj):
        return super().get_links(obj) + (
            self._link_view('self', 'frame-detail', [obj.id]),
            self._link_view('items', 'frame_item-list', [obj.id]),
        )


class SourceSerializer(BaseSerializer):

    class Meta:
        model = models.Source
        fields = BaseSerializer.Meta.fields + ('name',)
        read_only_fields = BaseSerializer.Meta.read_only_fields
        map_fields = BaseSerializer.Meta.fields


class DisplaySerializer(BaseSerializer):
    enabled = serializers.SerializerMethodField()
    device_type_name = serializers.SerializerMethodField()
    frame = FrameSerializer()

    class Meta:
        model = models.Display
        fields = BaseSerializer.Meta.fields + ('name', 'description', 'enabled', 'device_type', 'device_type_name', 'device_width', 'device_height', 'time_on', 'time_off', 'time_change', 'frame')
        read_only_fields = BaseSerializer.Meta.read_only_fields
        map_fields = BaseSerializer.Meta.fields + ('enabled',)

    def get_links(self, obj):
        return super().get_links(obj) + (
            self._link_view('self', 'display-detail', [obj.id]),
            self._link_view('item-list', 'display_item_all-list', [obj.id]),
            self._link_view('item-next', 'display_item_next-list', [obj.id]),
            self._link_view('finishing-list', 'display_finishing-list', [obj.id]),
            self._link_view('context-list', 'display_context-list', [obj.id]),
            self._link_view('status-list', 'display_status-list', [obj.id]),
        )

    def get_enabled(self, obj):
        return obj.enabled and (obj.frame is None or obj.frame.enabled)

    def get_device_type_name(self, obj):
        choice = [value for value in models.DEVICE_CHOICES if value[0] == obj.device_type]
        return choice[0][1] if choice else None

    def map(self, data, validated_data):
        return super().map(data, self.map_fields(data, validated_data, ['frame']))


class DisplayStatusSerializer(BaseSerializer):
    _json_renderer = JSONRenderer()
    _json_parser = JSONParser()

    class Meta:
        model = models.DisplayStatus
        fields = BaseSerializer.Meta.fields + (
            'uptime',
            'memory_used', 'memory_free',
            'cpu_load', 'cpu_temp',
            'disk_data_free', 'disk_tmp_free',
            'network_profile', 'network_connected', 'network_address_ip', 'network_address_gateway',
            'screen_on', 'screen_width', 'screen_height',
            'items_total', 'items_shown', 'items_error', 'items_updated',
            'app_uptime', 'app_date', 'app_branch', 'app_hash', 'app_checked', 'app_installed',
            'container_name', 'container_version',  'python_version', 'django_version',
            'links',
        )
        read_only_fields = BaseSerializer.Meta.read_only_fields
        map_fields = BaseSerializer.Meta.fields

    def get_links(self, obj):
        _display_id = self.get_kwargs().get('display_id')
        return super().get_links(obj) + (
            self._link_view('self', 'display_status-detail', [_display_id, obj.id]),
        ) if _display_id else ()

    def to_representation(self, instance):
        _result = super().to_representation(instance)
        _result = utils.Json.from_object_dict(_result)
        return _result

    def to_internal_value(self, data):
        _result = utils.Json.to_object_dict(data, [_name for _name in self.Meta.fields])
        _result = super().to_internal_value(_result)
        return _result

    def create(self, validated_data):
        _status = models.DisplayStatus(**validated_data)
        _status.save()
        return _status


class ItemFrameSerializer(BaseSerializer):

    class Meta:
        model = models.Item
        fields = BaseSerializer.Meta.fields + ('date_creation', 'url',)
        read_only_fields = BaseSerializer.Meta.read_only_fields
        map_fields = BaseSerializer.Meta.fields + ('url',)

    def get_links(self, obj):
        _frame_id = self.get_kwargs().get('frame_id')
        return super().get_links(obj) + (
            self._link_view('self', 'frame_item-detail', [_frame_id, obj.id]),
            self._link_view('frame', 'frame-detail', [_frame_id]),
        ) if _frame_id else ()


class ItemDisplaySerializer(BaseSerializer):

    class Meta:
        model = models.Item
        fields = BaseSerializer.Meta.fields + ('date_creation', 'url',)
        read_only_fields = BaseSerializer.Meta.read_only_fields
        map_fields = BaseSerializer.Meta.fields + ('url',)

    def get_links(self, obj):
        _display_id = self.get_kwargs().get('display_id')
        return super().get_links(obj) + (
            self._link_view('self', 'display_item_all-detail', [_display_id, obj.id]),
            self._link_view('display', 'display-detail', [_display_id]),
            self._link_view('hit', 'display_item_hit-detail', [_display_id, obj.id]),
            self._link_view('download', 'display_item_all-display_item_all_download', [_display_id, obj.id]),
        ) if _display_id else ()


class RankedItemFrameSerializer(ItemFrameSerializer):
    source = SourceSerializer()

    class Meta:
        model = models.RankedItem
        fields = ItemFrameSerializer.Meta.fields + ('rank', 'source')
        read_only_fields = ItemFrameSerializer.Meta.read_only_fields
        map_fields = ItemFrameSerializer.Meta.map_fields + ('rank',)
        abstract = True

    def map(self, data, validated_data):
        return super().map(data, self.map_fields(data, validated_data, ['source']))


class RankedItemDisplaySerializer(ItemDisplaySerializer):
    source = SourceSerializer()

    class Meta:
        model = models.RankedItem
        fields = ItemDisplaySerializer.Meta.fields + ('rank', 'source')
        read_only_fields = ItemDisplaySerializer.Meta.read_only_fields
        map_fields = ItemDisplaySerializer.Meta.map_fields + ('rank',)
        abstract = True

    def map(self, data, validated_data):
        return super().map(data, self.map_fields(data, validated_data, ['source']))


class DataFieldSerializer(serializers.Field):

    def __init__(self, cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cls = cls

    def to_representation(self, value):
        if value is None:
            return None
        return {
            'mime': value.data_mime,
            'size': value.data_size,
            'data': base64.b64encode(value.data()),
            'meta': value.meta,
        }

    def to_internal_value(self, data, *args, **kwargs):
        if data is None:
            return None
        if type(data) != dict or 'mime' not in data or 'data' not in data:
            raise serializers.ValidationError('not a structure, requires mime and data')
        _mime = data['mime']
        if len(_mime) > 64:
            raise serializers.ValidationError("mime type too long")
        if _mime not in mimetypes.types_map.values():
            raise serializers.ValidationError("unkown mime type")
        _data = base64.b64decode(data['data'])
        if len(_data) > 1*1024*1024:
            raise serializers.ValidationError("maximum size of 1mb exceeded")
        _meta = data['meta'] if 'meta' in data else {}
        return self._cls.create(data=_data, mime=_mime, meta=_meta)


class HitItemDisplaySerializer(BaseSerializer):
    id = serializers.IntegerField()
    thumbnail = DataFieldSerializer(models.DisplayItemThumbnailData, required=False, allow_null=True)

    class Meta:
        model = models.DisplayItem
        fields = BaseSerializer.Meta.fields + ('date_first_seen', 'date_last_seen', 'count_hit', 'thumbnail', 'duration_download', 'duration_finishing')
        read_only_fields = BaseSerializer.Meta.read_only_fields + ('date_first_see', 'date_last_seen', 'count_hit')
        map_fields = BaseSerializer.Meta.fields

    def get_links(self, obj):
        _display_id = self.get_kwargs().get('display_id')
        return super().get_links(obj) + (
            self._link_view('self', 'display_item_hit-detail', [_display_id, obj.id]),
            self._link_view('item', 'display_item_all-detail', [_display_id, obj.id]),
        ) if _display_id else ()

    def _save(self, item_id, validated_data):
        _view = self.context['view']
        _thumbnail = validated_data.get('thumbnail', -1)
        _display_id = _view.kwargs.get('display_id')
        _items = _view.get_queryset().filter(pk=item_id)
        if len(_items) == 0:
            raise serializers.ValidationError({"id": "no such item"})

        _now = utils.DateTime.now()
        _display_items = _view.qs().displayitems.filter(display__id=_display_id, item__id=item_id)
        if len(_display_items) == 0:
            _display_item = models.DisplayItem(
                display=_view.qs().displays.get(pk=_display_id),
                item=_view.qs().items.get(pk=item_id),
                date_first_seen=_now,
                date_last_seen=_now,
                duration_download=validated_data.get('duration_download'),
                duration_finishing=validated_data.get('duration_finishing'),
                count_hit=1)
        else:
            _display_item = _display_items[0]
            _display_item.date_last_seen = _now
            _display_item.duration_download = validated_data.get('duration_download')
            _display_item.duration_finishing = validated_data.get('duration_finishing')
            _display_item.count_hit = _display_item.count_hit + 1

        if _thumbnail != -1:
            if _thumbnail:
                if _display_item.thumbnail:
                    _display_item.thumbnail.update(_thumbnail)
                else:
                    _display_item.thumbnail = _thumbnail
                if 'width' not in _display_item.thumbnail.meta or 'height' not in _display_item.thumbnail.meta:
                    _adapter = finishing.ImageProcessingAdapter.get_default()
                    _image = _adapter.image_open(_display_item.thumbnail.data())
                    _meta = _adapter.image_meta(_image)
                    _adapter.image_close(_image)
                    _display_item.thumbnail.meta['width'] = _meta['width']
                    _display_item.thumbnail.meta['height'] = _meta['height']
                _display_item.thumbnail.save()
            elif _display_item.thumbnail:
                _display_item.thumbnail.data_file.delete(save=False)
                _display_item.thumbnail.delete()
                _display_item.thumbnail = None

        _display_item.save()
        return _display_item

    def create(self, validated_data):
        return self._save(validated_data.get('id'), validated_data)

    def update(self, instance, validated_data):
        return self._save(instance.id, validated_data)

    def to_representation(self, instance):
        _result = super().to_representation(instance)
        _result['id'] = instance.item.id if type(instance) == models.DisplayItem else instance.id
        return _result


class FinishingDisplaySerializer(BaseSerializer):

    class Meta:
        model = models.Finishing
        fields = BaseSerializer.Meta.fields + ('ordering', 'title', 'enabled', 'image_in', 'image_out', 'plugin', 'plugin_config', 'depth')
        read_only_fields = BaseSerializer.Meta.read_only_fields
        map_fields = BaseSerializer.Meta.fields + ('plugin_config',)

    def get_links(self, obj):
        _display_id = self.get_kwargs().get('display_id')
        return super().get_links(obj) + (
            self._link_view('self', 'display_finishing-detail', [_display_id, obj.id]),
            self._link_view('display', 'display-detail', [_display_id]),
            self._link_view('finishing-list', 'display_finishing-list', [_display_id]),
        ) if _display_id else ()


class ContextDisplaySerializer(BaseSerializer):

    class Meta:
        model = models.FrameContext
        fields = BaseSerializer.Meta.fields + ('name', 'enabled', 'plugin', 'plugin_config',)
        read_only_fields = BaseSerializer.Meta.read_only_fields
        map_fields = BaseSerializer.Meta.fields + ('plugin_config',)

    def get_links(self, obj):
        _display_id = self.get_kwargs().get('display_id')
        return super().get_links(obj) + (
            self._link_view('self', 'display_context-detail', [_display_id, obj.id]),
            self._link_view('display', 'display-detail', [_display_id]),
            self._link_view('context-list', 'display_context-list', [_display_id]),
        ) if _display_id else ()


class BaseListView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]


class BaseDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]


class BaseViewSet(BaseListView, BaseQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    pass


class FrameViewSet(BaseViewSet):
    serializer_class = FrameSerializer
    
    def get_queryset(self):
        return self.qs().frames


class FrameItemViewSet(BaseViewSet):
    serializer_class = ItemFrameSerializer
    
    def get_queryset(self):
        _frame_id = self.kwargs.get('frame_id')
        return self.qs().items.filter(frame__id=_frame_id)


class DisplayViewSet(BaseViewSet):
    serializer_class = DisplaySerializer
    
    def get_queryset(self):
        return self.qs().displays

    @decorators.action(detail='frame/detail', methods=['get'])
    def frame(self, request, *args, **kwargs):
        return response.Response(FrameDisplaySerializer(self.get_object().frame, context={'request': request}).data)


class StatusDisplayViewSet(mixins.CreateModelMixin, BaseViewSet):
    serializer_class = DisplayStatusSerializer

    def get_queryset(self):
        _display_id = self.kwargs.get('display_id')
        return self.qs().displaystatus.filter(display_id=_display_id)

    def perform_create(self, serializer):
        _display_id = self.kwargs.get('display_id')
        _displays = list(self.qs().displays.filter(pk=_display_id))
        if len(_displays) == 0:
            raise NotFound()
        serializer.save(display=_displays[0])


class ItemDisplayViewSet(BaseViewSet):
    serializer_class = ItemDisplaySerializer
    
    def get_queryset(self):
        _display_id = self.kwargs.get('display_id')
        return self.qs().items.filter(frame__display__id=_display_id)

    @decorators.action(detail=True, url_path='download', url_name='display_item_all_download')
    def download(self, request, display_id, pk):
        _item = self.get_object()
        _response = utils.Network.get_url(_item.url, utils.Network.METHOD_GET, stream=True)
        return StreamingHttpResponse(
            (_chunk for _chunk in _response.iter_content(1024*64)),
            content_type=_response.headers['content-type'] or 'application/octet-stream')


class HitItemDisplayViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, BaseViewSet):
    serializer_class = HitItemDisplaySerializer

    def get_queryset(self):
        _display_id = self.kwargs.get('display_id')

        # Prepare special filter to be able to return for each Item a DisplayItem
        # object, even if there does not exist one currently (just return None
        # values) - this only works using "Item LEFT OUTER JOIN DisplayItem", which
        # will be generated by "Q(field__isnull=True)|Q(field__isnull=False)"
        # Expected query something like this:
        #   select *
        #   from config_display d, config_frame f, config_item i left outer join config_display_item di on di.item_id=i.id
        #   where d.user_id=1 and d.frame_id=f.id and i.frame_id=f.id
        _filter = self.qs().items.filter(frame__display__id=_display_id)
        _filter = _filter.filter(Q(display__isnull=True)|Q(display__isnull=False))
        _filter = _filter.extra(select={
            'id': 'config_item.id',
            'date_first_seen': 'config_display_item.date_first_seen',
            'date_last_seen': 'config_display_item.date_last_seen',
            'count_hit' : 'config_display_item.count_hit',
            'thumbnail_id': 'config_display_item.thumbnail_id',
        })
        return _filter


class NextItemDisplayViewSet(BaseViewSet):  # BaseDetailView
    serializer_class = RankedItemDisplaySerializer

    def get_queryset(self, *args, **kwargs):
        _display_id = self.kwargs.get('display_id')
        _frames = self.qs().frames.filter(display__id=_display_id)
        if len(_frames) == 0:
            raise NotFound()
        _processor = sorting.Processor(sorting.Context(_frames[0], random_item=True))
        _result = _processor.process()
        _items = list(_result['items'])
        if self.request.query_params.get('hit', '0') == '1' and len(_items) > 0:
            _item = _items[0]
            _display = self.qs().displays.filter(pk=_display_id).get()
            _display_items = list(self.qs().displayitems.filter(item__id=_item.id))
            if len(_display_items):
                _display_item = _display_items[0]
            else:
                _display_item = models.DisplayItem(
                    display=_display,
                    item=_item,
                    date_first_seen=timezone.now(),
                    count_hit=0,
                )
            _display_item.date_last_seen = timezone.now()
            _display_item.count_hit = _display_item.count_hit + 1
            _display_item.save()
        return _items


class FinishingDisplayViewSet(BaseViewSet):
    serializer_class = FinishingDisplaySerializer
    
    def get_queryset(self):
        _display_id = self.kwargs.get('display_id')
        _finishings = self.qs().finishings
        _finishings = _finishings.for_export(True) if 'pk' not in self.kwargs else _finishings
        return _finishings.filter(frame__display__id=_display_id)


class ContextDisplayViewSet(BaseViewSet):
    serializer_class = ContextDisplaySerializer

    def get_queryset(self):
        _display_id = self.kwargs.get('display_id')
        return self.qs().contexts.filter(frame__display__id=_display_id)



