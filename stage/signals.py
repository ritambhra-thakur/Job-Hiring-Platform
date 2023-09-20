from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from app.memcache_stats import MemcachedStats
from stage.models import PositionStage

# stage/positionstage/api/v1/list/?domain=infer&position=871&sort_field=sort_order&sort_dir=asc


@receiver(post_save, sender=PositionStage)
def update_cache_create(sender, instance, created, **kwargs):
    mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
    for i in mem.keys():
        try:
            key = i.partition("/")[-1]
            if key.startswith("stage/positionstage/api/v1/list/") and str(instance.position.id) in key:
                resp = cache.delete("/" + key)
                continue
        except Exception as e:
            print(e)


@receiver(post_delete, sender=PositionStage)
@receiver(post_save, sender=PositionStage)
def update_cache_save(sender, instance, **kwargs):
    mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
    for i in mem.keys():
        try:
            key = i.partition("/")[-1]
            if key.startswith("stage/positionstage/api/v1/list/") and str(instance.position.id) in key:
                cache.delete("/" + key)
                continue
        except Exception as e:
            print(e)
