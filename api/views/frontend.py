
from rest_framework import generics, viewsets, serializers
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from framarama.base import frontend, device
from frontend import models


class ItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    url = serializers.CharField(max_length=1024)
    mime = serializers.CharField(max_length=255)


class SetupStatusView(viewsets.ViewSet):

    def list(self, request, format=None):
        try:
            _frontend = frontend.Frontend.get()
            if _frontend.is_initialized():
                return Response({
                    'status': 'success',
                    'message': 'Configuration setup completed',
                    'init': _frontend.get_init_status()
                })
            return Response({
                'status': 'testing',
                'message': 'Configuration setup not available',
                'init': _frontend.get_init_status()
            })
        except Exception as e:
            return Response({
               'status': 'error',
               'message': 'Error checking setup status: ' + str(e)
            })


class DatabaseStatusView(viewsets.ViewSet):

    def list(self, request, format=None):
        try:
            if frontend.Frontend.get().db_access():
                return Response({
                    'status': 'success',
                    'message': 'Database access successful'
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'No database access possible'
                })
        except Exception as e:
            return Response({
               'status': 'error',
               'message': 'Error accessing database: ' + str(e)
            })


class DisplayStatusView(viewsets.ViewSet):

    def list(self, request, format=None):
        try:
            if frontend.Frontend.get().api_access():
                _display = frontend.Frontend.get().get_display()
                return Response({
                    'status': 'success',
                    'message': 'Successful API access',
                    'data': {
                      'display': {
                        'id': _display.get_id(),
                        'name': _display.get_name(),
                        'enabled': _display.get_enabled(),
                        'device_type': _display.get_device_type(),
                        'device_type_name': _display.get_device_type_name(),
                        'device_width': _display.get_device_width(),
                        'device_height': _display.get_device_height()
                      }
                    }
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'No display configured',
                })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': 'Error accessing API: ' + str(e)
            })


class OverviewDisplayView(viewsets.ViewSet):

    def list(self, request, format=None):
        _frontend = frontend.Frontend.get()
        _config = _frontend.get_config().get_config()
        _display = _frontend.get_display()
        _data = {
            'mode': _config.mode,
            'server': _config.cloud_server if _config.mode == 'cloud' else None,
            'database': (_config.local_db_user + '@' + _config.local_db_host + '/' + _config.local_db_name) if _config.mode != 'cloud' else None,
            'name': _display.get_name(),
            'type': _display.get_device_type(),
            'geometry': {
                'width': _display.get_device_width(),
                'height': _display.get_device_height(),
            }
        }
        return Response(_data)


class StatusDisplayView(viewsets.ViewSet):

    def list(self, request, format=None):
        _status = frontend.Frontend.get().get_status()
        return Response(_status)


class ItemsDisplayView(viewsets.GenericViewSet):
    serializer_class = ItemSerializer

    def _items(self):
        _frontend_device = frontend.Frontend.get().get_device()
        _items = _frontend_device.get_items()
        _items = [{
            'id': _no,
            'url': _item.item().url,
            'mime': _item.mime(),
        } for _no, _item in enumerate(_items)]
        return _items

    def list(self, request, format=None):
        _serializer = self.get_serializer(instance=self._items(), many=True)
        return Response(_serializer.data)

    def retrieve(self, request, pk):
        _pk = int(pk)
        _files = self._files()
        if len(_files) <= _pk:
            raise NotFound()
        _serializer = self.get_serializer(instance=_files[_pk])
        return Response(_serializer.data)


class ScreenDisplayView(viewsets.ViewSet):

    def list(self, request):
        _frontend_device = frontend.Frontend.get()
        return Response(_frontend_device.get_screen())


class SwitchScreenDisplayView(viewsets.ViewSet):

    def list(self, request, state):
        _frontend = frontend.Frontend.get()
        _frontend_device = _frontend.get_device()
        if state == 'toggle':
            _frontend_device.display_toggle()
        elif state == 'on':
            _frontend_device.display_toggle(True)
        elif state == 'off':
            _frontend_device.display_toggle(False)
        return Response(_frontend.get_screen())

