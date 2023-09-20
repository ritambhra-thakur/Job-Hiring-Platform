from django.db import models


class ShortURL(models.Model):
    long_url = models.CharField(max_length=512)
    short_url = models.CharField(max_length=512, unique=True)
    internal = models.BooleanField(default=None, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ShortURL"
        verbose_name_plural = "ShortURLs"

    def __str__(self):
        return self.short_url
