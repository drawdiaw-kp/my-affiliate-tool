from django.db import models

class ContentHistory(models.Model):
    product_name = models.CharField(max_length=255)
    caption = models.TextField()
    script = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"