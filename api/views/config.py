import base64
import mimetypes

from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from rest_framework import generics, viewsets, mixins, permissions, serializers, decorators, response
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from framarama.base import utils
from framarama.base.views import BaseQuerySetMixin
from config import models
from config.utils import sorting, finishing
from api import auth


class FrameSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Frame
        fields = ['id', 'name', 'description', 'enabled']


class DisplaySerializer(serializers.HyperlinkedModelSerializer):
    enabled = serializers.SerializerMethodField()
    device_type_name = serializers.SerializerMethodField()
    frame = FrameSerializer()

    class Meta:
        model = models.Display
        fields = ['id', 'name', 'description', 'enabled', 'device_type', 'device_type_name', 'device_width', 'device_height', 'time_on', 'time_off', 'time_change', 'frame']

    def get_enabled(self, obj):
        return obj.enabled and (obj.frame is None or obj.frame.enabled)

    def get_device_type_name(self, obj):
        choice = [value for value in models.DEVICE_CHOICES if value[0] == obj.device_type]
        return choice[0][1] if choice else None


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


class ItemSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Item
        fields = ['id', 'url']


class RankedItemSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.RankedItem
        fields = ['rank', 'id', 'url']
        abstract = True


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
        read_only_fields = ['date_first_see', 'date_last_seen', 'count_hit']

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
                    _thumbnail.update(_display_item.thumbnail)
                else:
                    _display_item.thumbnail = _thumbnail
                if 'width' not in _display_item.thumbnail.meta or 'height' not in _display_item.thumbnail.meta:
                    _adapter = finishing.WandImageProcessingAdapter()
                    _image = _adapter.image_open(_display_item.thumbnail.data_file.path)
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


class FinishingSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Finishing
        fields = ['id', 'ordering', 'title', 'enabled', 'image_in', 'image_out', 'plugin', 'plugin_config']


class ContextSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.FrameContext
        fields = ['id', 'name', 'enabled', 'plugin', 'plugin_config']


class NextItemSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Item
        fields = ['id', 'url']


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
    serializer_class = ItemSerializer
    
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
    def frame(self, *args, **kwargs):
        return response.Response(FrameSerializer(self.get_object().frame).data)


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
    serializer_class = ItemSerializer
    
    def get_queryset(self):
        _display_id = self.kwargs.get('display_id')
        return self.qs().items.filter(frame__display__id=_display_id)


class HitItemDisplayViewSet(mixins.CreateModelMixin, BaseViewSet):
    serializer_class = DisplayItemSerializer

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
    serializer_class = RankedItemSerializer

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



