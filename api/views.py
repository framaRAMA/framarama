import random

from django.shortcuts import render
from rest_framework import generics, viewsets, permissions, serializers, decorators, response
from rest_framework.exceptions import NotFound
from rest_framework_extensions import mixins

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


class BaseViewSet(BaseListView, viewsets.ModelViewSet):
    pass


class BaseNestedViewSet(mixins.NestedViewSetMixin, BaseViewSet):
    pass


class FrameViewSet(BaseNestedViewSet):
    serializer_class = FrameSerializer
    
    def get_queryset(self):
        return self.request.user.qs_frames.filter(user=self.request.user)


class FrameItemViewSet(BaseNestedViewSet):
    serializer_class = ItemSerializer
    
    def get_queryset(self):
        return self.request.user.qs_items.filter(frame__user=self.request.user)


class DisplayViewSet(BaseNestedViewSet):
    serializer_class = DisplaySerializer
    
    def get_queryset(self):
        return self.request.user.qs_displays.filter(user=self.request.user)

    @decorators.action(detail='frame', methods=['get'])
    def frame(self, *args, **kwargs):
        return response.Response(FrameSerializer(self.get_object().frame).data)


class ItemDisplayViewSet(BaseNestedViewSet):
    serializer_class = ItemSerializer
    
    def get_queryset(self):
        return self.request.user.qs_items.filter(frame__user=self.request.user)


class NextItemDisplayViewSet(BaseNestedViewSet):  # BaseDetailView
    serializer_class = RankedItemSerializer

    def get_queryset(self, *args, **kwargs):
        _frames = self.request.user.qs_frames.filter(user=self.request.user)
        if len(_frames) == 0:
            raise NotFound()
        _processor = sorting.Processor(sorting.Context(_frames[0], first_ranked=random.randint(0, 4527000)))
        _result = _processor.process()
        return _result['items']


class FinishingDisplayViewSet(BaseNestedViewSet):
    serializer_class = FinishingSerializer
    
    def get_queryset(self):
        return self.request.user.qs_finishings.filter(frame__user=self.request.user)



