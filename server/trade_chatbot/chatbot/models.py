from django.db import models

class TradeData(models.Model):
    country = models.CharField(max_length=255, db_index=True)
    year = models.CharField(max_length=10, db_index=True)
    data_type = models.CharField(max_length=20, db_index=True)
    file = models.TextField(null=True, blank=True)
    
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    status = models.CharField(
        max_length=20,
        default="processing",
        choices=STATUS_CHOICES
    )
    
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Comment out unique_together for now
        # unique_together = ['country', 'year', 'data_type']
        indexes = [
            models.Index(fields=['country', 'data_type', 'year']),
        ]

    def __str__(self):
        return f"{self.country} - {self.year} - {self.data_type}"