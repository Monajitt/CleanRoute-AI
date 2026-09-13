from rest_framework import serializers
from .models import RouteSearch, TravelMode, RoutePreference


class RouteSearchSerializer(serializers.ModelSerializer):
    origin_latitude = serializers.FloatField(required=False, allow_null=True)
    origin_longitude = serializers.FloatField(required=False, allow_null=True)
    destination_latitude = serializers.FloatField(required=False, allow_null=True)
    destination_longitude = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = RouteSearch
        fields = [
            'id',
            'origin_name',
            'destination_name',
            'origin_latitude',
            'origin_longitude',
            'destination_latitude',
            'destination_longitude',
            'travel_mode',
            'route_preference',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def to_internal_value(self, data):
        data_copy = data.copy() if hasattr(data, 'copy') else dict(data)

        # Support nested origin { name, latitude, longitude }
        if isinstance(data_copy.get('origin'), dict):
            orig = data_copy['origin']
            if 'name' in orig:
                data_copy['origin_name'] = orig['name']
            if 'latitude' in orig and orig['latitude'] is not None:
                data_copy['origin_latitude'] = orig['latitude']
            if 'longitude' in orig and orig['longitude'] is not None:
                data_copy['origin_longitude'] = orig['longitude']

        # Support nested destination { name, latitude, longitude }
        if isinstance(data_copy.get('destination'), dict):
            dest = data_copy['destination']
            if 'name' in dest:
                data_copy['destination_name'] = dest['name']
            if 'latitude' in dest and dest['latitude'] is not None:
                data_copy['destination_latitude'] = dest['latitude']
            if 'longitude' in dest and dest['longitude'] is not None:
                data_copy['destination_longitude'] = dest['longitude']

        # Support 'priority' alias for 'route_preference'
        if 'priority' in data_copy and 'route_preference' not in data_copy:
            data_copy['route_preference'] = data_copy['priority']

        # Normalize priority/preference aliases
        prio = str(data_copy.get('route_preference', '')).lower()
        if prio in ('health', 'health first', 'health-first'):
            data_copy['route_preference'] = RoutePreference.HEALTH_FIRST
        elif prio in ('time', 'time first', 'time-first'):
            data_copy['route_preference'] = RoutePreference.TIME_FIRST
        elif prio in ('balanced', 'balance'):
            data_copy['route_preference'] = RoutePreference.BALANCED

        return super().to_internal_value(data_copy)

    def validate_travel_mode(self, value):
        if value not in TravelMode.values:
            valid_modes = ", ".join(TravelMode.values)
            raise serializers.ValidationError(f"Invalid travel mode '{value}'. Must be one of: {valid_modes}.")
        return value

    def validate_route_preference(self, value):
        if value not in RoutePreference.values:
            valid_prefs = ", ".join(RoutePreference.values)
            raise serializers.ValidationError(f"Invalid route preference '{value}'. Must be one of: {valid_prefs}.")
        return value

    def validate(self, attrs):
        origin = attrs.get('origin_name', '').strip()
        dest = attrs.get('destination_name', '').strip()

        if not origin:
            raise serializers.ValidationError({"origin_name": "Origin location cannot be empty."})
        if not dest:
            raise serializers.ValidationError({"destination_name": "Destination location cannot be empty."})
        if origin.lower() == dest.lower():
            raise serializers.ValidationError("Origin and destination cannot be identical.")

        # Coordinate range checks
        for prefix in ['origin', 'destination']:
            lat = attrs.get(f'{prefix}_latitude')
            lon = attrs.get(f'{prefix}_longitude')
            if lat is not None and not (-90.0 <= lat <= 90.0):
                raise serializers.ValidationError({f'{prefix}_latitude': f"Latitude must be between -90 and 90 degrees."})
            if lon is not None and not (-180.0 <= lon <= 180.0):
                raise serializers.ValidationError({f'{prefix}_longitude': f"Longitude must be between -180 and 180 degrees."})

        return attrs

    def create(self, validated_data):
        # Exclude transient coordinate parameters before creating database record
        model_data = {
            'origin_name': validated_data.get('origin_name'),
            'destination_name': validated_data.get('destination_name'),
            'travel_mode': validated_data.get('travel_mode', TravelMode.CYCLING),
            'route_preference': validated_data.get('route_preference', RoutePreference.BALANCED),
        }
        return RouteSearch.objects.create(**model_data)
