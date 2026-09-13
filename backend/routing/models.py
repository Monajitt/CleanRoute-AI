from django.db import models


class TravelMode(models.TextChoices):
    WALKING = 'walking', 'Walking'
    CYCLING = 'cycling', 'Cycling'
    DRIVING = 'driving', 'Driving'


class RoutePreference(models.TextChoices):
    HEALTH_FIRST = 'health_first', 'Health First'
    BALANCED = 'balanced', 'Balanced'
    TIME_FIRST = 'time_first', 'Time First'


class RouteSearch(models.Model):
    """
    Stores historical route search queries submitted by users.
    """
    origin_name = models.CharField(max_length=255, help_text="Origin location query name")
    destination_name = models.CharField(max_length=255, help_text="Destination location query name")
    travel_mode = models.CharField(
        max_length=20,
        choices=TravelMode.choices,
        default=TravelMode.CYCLING,
        help_text="Modal preference (walking, cycling, driving)"
    )
    route_preference = models.CharField(
        max_length=20,
        choices=RoutePreference.choices,
        default=RoutePreference.BALANCED,
        help_text="Optimization priority (health_first, balanced, time_first)"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when search query was initiated")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Route Search'
        verbose_name_plural = 'Route Searches'

    def __str__(self):
        return f"{self.origin_name} -> {self.destination_name} ({self.get_travel_mode_display()} | {self.get_route_preference_display()})"
