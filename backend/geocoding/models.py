from django.db import models


class GeocodeCache(models.Model):
    """
    Caches forward geocoding query results from Nominatim to respect rate limits.
    """
    query = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    display_name = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Geocode Cache'
        verbose_name_plural = 'Geocode Caches'

    def __str__(self):
        return f"{self.query} -> ({self.latitude}, {self.longitude})"
