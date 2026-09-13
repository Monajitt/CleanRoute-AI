from django.contrib import admin
from .models import RouteSearch


@admin.register(RouteSearch)
class RouteSearchAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'origin_name',
        'destination_name',
        'travel_mode',
        'route_preference',
        'created_at'
    )
    list_filter = ('travel_mode', 'route_preference', 'created_at')
    search_fields = ('origin_name', 'destination_name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
