from frontend.views import base


class HelpSystemView(base.BaseFrontendView):
    template_name = 'frontend/system.help.html'


class UsbSystemView(base.BaseFrontendView):
    template_name = 'frontend/system.usb.html'


class LabelSystemView(base.BaseFrontendView):
    template_name = 'frontend/system.label.html'


