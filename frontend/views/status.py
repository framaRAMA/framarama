from framarama.base import frontend
from frontend.views import base


class SetupStatusView(base.BaseStatusView):

    def _status(self, context):
        try:
            if frontend.Frontend.get().is_initialized():
                return {
                    'status': 'success',
                    'message': 'Configuration setup completed'
                }
            return {
                'status': 'testing',
                'message': 'Configuration setup not available'
            }
        except Exception as e:
            return {
               'status': 'error',
               'message': 'Error checking setup status: ' + str(e)
            }
 

class DatabaseStatusView(base.BaseStatusView):

    def _status(self, context):
        try:
            if frontend.Frontend.get().db_access():
                return {
                    'status': 'success',
                    'message': 'Database access successful'
                }
            else:
                return {
                    'status': 'error',
                    'message': 'No database access possible'
                }
        except Exception as e:
            return {
               'status': 'error',
               'message': 'Error accessing database: ' + str(e)
            }
 

class DisplayStatusView(base.BaseStatusView):

    def _status(self, context):
        try:
            if frontend.Frontend.get().api_access():
                _display = frontend.Frontend.get().get_display()
                return {
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
                }
            else:
                return {
                    'status': 'error',
                    'message': 'No display configured',
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': 'Error accessing API: ' + str(e)
            }
 


