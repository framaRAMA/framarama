import io

from django.shortcuts import render
from django.utils import timezone
from rest_framework import generics, viewsets, mixins, permissions, serializers, decorators, response
from rest_framework.exceptions import NotFound
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from framarama.base import utils
from framarama.base.views import BaseQuerySetMixin
from config import models
from config.utils import sorting
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
            'items_total', 'items_shown', 'items_error', 'items_updated'
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


class FinishingSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Finishing
        fields = ['id', 'ordering', 'title', 'enabled', 'image_in', 'image_out', 'color_stroke', 'color_fill', 'color_alpha', 'stroke_width', 'plugin', 'plugin_config']


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



