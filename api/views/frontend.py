
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
            if frontend.Frontend.get().is_initialized():
                return Response({
                    'status': 'success',
                    'message': 'Configuration setup completed'
                })
            return Response({
                'status': 'testing',
                'message': 'Configuration setup not available'
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

    def _files(self):
        _frontend_device = frontend.Frontend.get().get_device()
        _files = list(_frontend_device.get_files().values())
        _files = [{
            'id': _no,
            'url': _file['json']['item'].url,
            'mime': _file['json']['mime'],
        } for _no, _file in enumerate(_files)]
        return _files

    def list(self, request, format=None):
        _serializer = self.get_serializer(instance=self._files(), many=True)
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
        _status = _frontend_device.run_capability(device.Capability.DISPLAY_STATUS)
        if state == 'toggle':
            state = 'off' if _status else 'on'
        if state == 'on' and not _status:
            _frontend_device.run_capability(device.Capability.DISPLAY_ON)
        elif state == 'off' and _status:
            _frontend_device.run_capability(device.Capability.DISPLAY_OFF)
        return Response(_frontend.get_screen())

