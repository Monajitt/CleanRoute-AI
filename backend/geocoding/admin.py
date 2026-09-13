from django.contrib import admin
from .models import GeocodeCache


@admin.register(GeocodeCache)
class GeocodeCacheAdmin(admin.ModelAdmin):
    list_display = ('query', 'latitude', 'longitude', 'created_at')
    search_fields = ('query', 'display_name')
    readonly_fields = ('created_at',)
