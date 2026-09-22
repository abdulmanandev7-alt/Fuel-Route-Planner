from django.db import models


class FuelStation(models.Model):
    opis_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=200)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=2)
    rack_id = models.PositiveIntegerField()
    retail_price = models.DecimalField(max_digits=12, decimal_places=8, help_text="USD per gallon")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["opis_id"]
        indexes = [models.Index(fields=["state", "city"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.city}, {self.state})"

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None
