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


class BaseSerializer:

    def get_request(self):
        return self.context.get('request')

    def get_kwargs(self):
        return self.get_request().parser_context['kwargs']

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
                validated_data[_name] = serializer.map(data.get(_name, None), serializer.validated_data)
            else:
                validated_data[_name] = data.get(_name, None)
        return validated_data


class FrameSerializer(BaseSerializer, serializers.HyperlinkedModelSerializer):
    url_items = serializers.SerializerMethodField()
    class Meta:
        model = models.Frame
        fields = ['id', 'name', 'description', 'enabled', 'url', 'url_items']
        map_fields = ['id']

    def get_url_items(self, obj):
        return self.reverse('frame_item-list', [obj.id])


class SourceSerializer(BaseSerializer, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Source
        fields = ['id', 'name']
        map_fields = ['id']


class DisplaySerializer(BaseSerializer, serializers.HyperlinkedModelSerializer):
    enabled = serializers.SerializerMethodField()
    device_type_name = serializers.SerializerMethodField()
    frame = FrameSerializer()
    url_items_all = serializers.SerializerMethodField()
    url_items_next = serializers.SerializerMethodField()
    url_finishings = serializers.SerializerMethodField()
    url_contexts = serializers.SerializerMethodField()
    url_status = serializers.SerializerMethodField()

    class Meta:
        model = models.Display
        fields = ['id', 'name', 'description', 'enabled', 'device_type', 'device_type_name', 'device_width', 'device_height', 'time_on', 'time_off', 'time_change', 'frame', 'url', 'url_items_all', 'url_items_next', 'url_finishings', 'url_contexts', 'url_status']
        map_fields = ['id', 'enabled']

    def get_enabled(self, obj):
        return obj.enabled and (obj.frame is None or obj.frame.enabled)

    def get_device_type_name(self, obj):
        choice = [value for value in models.DEVICE_CHOICES if value[0] == obj.device_type]
        return choice[0][1] if choice else None

    def get_url_items_all(self, obj):
        return self.reverse('display_item_all-list', args=[obj.id])

    def get_url_items_next(self, obj):
        return self.reverse('display_item_next-list', args=[obj.id])

    def get_url_finishings(self, obj):
        return self.reverse('display_finishing-list', [obj.id])

    def get_url_contexts(self, obj):
        return self.reverse('display_context-list', [obj.id])

    def get_url_status(self, obj):
        return self.reverse('display_status-list', [obj.id])

    def map(self, data, validated_data):
        return super().map(data, self.map_fields(data, validated_data, ['frame']))


class DisplayStatusSerializer(serializers.HyperlinkedModelSerializer):
    _json_renderer = JSONRenderer()
    _json_parser = JSONParser()

    class Meta:
        model = models.DisplayStatus
        fields = [
            'id',
            'uptime',
            'memory_used', 'memory_free',
            'cpu_load', 'cpu_temp',
            'disk_data_free', 'disk_tmp_free',
            'network_profile', 'network_connected', 'network_address_ip', 'network_address_gateway',
            'screen_on', 'screen_width', 'screen_height',
            'items_total', 'items_shown', 'items_error', 'items_updated',
            'app_date', 'app_branch', 'app_hash',
        ]

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


class ItemFrameSerializer(BaseSerializer, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Item
        fields = ('id', 'date_creation', 'url')
        map_fields = ['id']


class ItemDisplaySerializer(BaseSerializer, serializers.HyperlinkedModelSerializer):
    url_download = serializers.SerializerMethodField()
    class Meta:
        model = models.Item
        fields = ('id', 'date_creation', 'url', 'url_download')
        map_fields = ['id']

    def get_url_download(self, obj):
        _kwargs = self.get_kwargs()
        return self.reverse('display_item_all-display_item_all_download', [_kwargs['display_id'], obj.id])


class RankedItemFrameSerializer(ItemFrameSerializer):
    source = SourceSerializer()
    class Meta:
        model = models.RankedItem
        fields = ItemFrameSerializer.Meta.fields + ('rank', 'source')
        map_fields = ItemFrameSerializer.Meta.map_fields
        abstract = True

    def map(self, data, validated_data):
        return super().map(data, self.map_fields(data, validated_data, ['source']))


class RankedItemDisplaySerializer(ItemDisplaySerializer):
    source = SourceSerializer()
    class Meta:
        model = models.RankedItem
        fields = ItemDisplaySerializer.Meta.fields + ('rank', 'source')
        map_fields = ItemFrameSerializer.Meta.map_fields
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


class DisplayItemSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField()
    thumbnail = DataFieldSerializer(models.DisplayItemThumbnailData, required=False, allow_null=True)

    class Meta:
        model = models.DisplayItem
        fields = ['id', 'date_first_seen', 'date_last_seen', 'count_hit', 'thumbnail']
        read_only_fields = ['date_first_see', 'date_last_seen', 'count_hit', 'url']

    def create(self, validated_data):
        _view = self.context['view']
        _item_id = validated_data.get('id')
        _thumbnail = validated_data.get('thumbnail', -1)
        _display_id = _view.kwargs.get('display_id')
        _items = _view.get_queryset().filter(pk=_item_id)
        if len(_items) == 0:
            raise serializers.ValidationError({"id": "no such item"})

        _now = utils.DateTime.now()
        _display_items = _view.qs().displayitems.filter(display__id=_display_id, item__id=_item_id)
        if len(_display_items) == 0:
            _display_item = models.DisplayItem(
                display=_view.qs().displays.get(pk=_display_id),
                item=_view.qs().items.get(pk=_item_id),
                date_first_seen=_now,
                date_last_seen=_now,
                count_hit=1)
        else:
            _display_item = _display_items[0]
            _display_item.date_last_seen = _now
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

    def to_representation(self, instance):
        _result = super().to_representation(instance)
        _result['id'] = instance.item.id if type(instance) == models.DisplayItem else instance.id
        return _result


class FinishingSerializer(BaseSerializer, serializers.HyperlinkedModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = models.Finishing
        fields = ['id', 'ordering', 'title', 'enabled', 'image_in', 'image_out', 'plugin', 'plugin_config', 'url']
        map_fields = ['id']

    def get_url(self, obj):
        _kwargs = self.get_kwargs()
        return self.reverse('display_finishing-detail', [_kwargs['display_id'], obj.id])


class ContextSerializer(BaseSerializer, serializers.HyperlinkedModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = models.FrameContext
        fields = ['id', 'name', 'enabled', 'plugin', 'plugin_config', 'url']
        map_fields = ['id']

    def get_url(self, obj):
        _kwargs = self.get_kwargs()
        return self.reverse('display_context-detail', [_kwargs['display_id'], obj.id])


class NextItemSerializer(RankedItemDisplaySerializer):
    pass


class BaseListView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]


class BaseDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]


class BaseViewSet(BaseListView, BaseQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    pass


class FrameViewSet(BaseViewSet):
    serializer_class = FrameSerializer
    
    def get_queryset(self):
        _pk = self.kwargs.get('pk', None)
        if _pk:
            return self.qs().frames.filter(pk=_pk)
        return self.qs().frames


class FrameItemViewSet(BaseViewSet):
    serializer_class = ItemFrameSerializer
    
    def get_queryset(self):
        _frame_id = self.kwargs.get('frame_id')
        return self.qs().items.filter(frame__id=_frame_id)


class DisplayViewSet(BaseViewSet):
    serializer_class = DisplaySerializer
    
    def get_queryset(self):
        _pk = self.kwargs.get('pk', None)
        if _pk:
            return self.qs().displays.filter(pk=_pk)
        return self.qs().displays

    @decorators.action(detail='frame/detail', methods=['get'])
    def frame(self, request, *args, **kwargs):
        return response.Response(FrameSerializer(self.get_object().frame, context={'request': request}).data)


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


class HitItemDisplayViewSet(mixins.CreateModelMixin, BaseViewSet):
    serializer_class = ItemDisplaySerializer

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
    serializer_class = FinishingSerializer
    
    def get_queryset(self):
        _display_id = self.kwargs.get('display_id')
        return self.qs().finishings.filter(frame__display__id=_display_id)


class ContextDisplayViewSet(BaseViewSet):
    serializer_class = ContextSerializer

    def get_queryset(self):
        _display_id = self.kwargs.get('display_id')
        return self.qs().contexts.filter(frame__display__id=_display_id)



