from django.contrib import admin

# Register your models here.
from . import models

admin.site.register(models.Frame)
admin.site.register(models.Source)
admin.site.register(models.SourceStep)
admin.site.register(models.Sorting)
admin.site.register(models.Finishing)
admin.site.register(models.FrameContext)
admin.site.register(models.Item)
admin.site.register(models.Display)
admin.site.register(models.DisplayStatus)
admin.site.register(models.DisplayItem)

