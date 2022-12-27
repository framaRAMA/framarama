
from django.shortcuts import render
from rest_framework import generics, viewsets, permissions, serializers, decorators, response
from rest_framework.exceptions import NotFound

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
        return _result['items']


class FinishingDisplayViewSet(BaseViewSet):
    serializer_class = FinishingSerializer
    
    def get_queryset(self):
        _display_id = self.kwargs.get('display_id')
        return self.qs().finishings.filter(frame__display__id=_display_id)



