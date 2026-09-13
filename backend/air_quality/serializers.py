from rest_framework import serializers


class AirQualityQuerySerializer(serializers.Serializer):
    latitude = serializers.FloatField(required=True, min_value=-90.0, max_value=90.0)
    longitude = serializers.FloatField(required=True, min_value=-180.0, max_value=180.0)


class AirQualityDataSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    aqi = serializers.FloatField()
    pm25 = serializers.FloatField()
    pm10 = serializers.FloatField()
    no2 = serializers.FloatField()
    ozone = serializers.FloatField()
    aqi_category = serializers.CharField()
    estimated_pollution_exposure = serializers.CharField()
    source = serializers.CharField()


class AirQualityResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    data = AirQualityDataSerializer()
