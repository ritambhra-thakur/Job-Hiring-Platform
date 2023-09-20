import json

import requests
from django.conf import settings
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from app.memcache_stats import MemcachedStats
from form.models import AppliedPosition, FormData, OfferLetter, SavedPosition

url = "https://typedwebhook.tools/webhook/ea63177a-7020-47e6-b108-dd891d930b70"


@receiver(post_save, sender=FormData)
def update_cache(sender, instance, created, **kwargs):
    if created:
        show_id = instance.company.form_id
        instance.show_id = show_id + 1
        instance.company.form_id = show_id + 1
        instance.save()
        instance.company.save()
    # mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
    # for i in mem.keys():
    #     try:
    #         key = i.partition("/")[-1]
    #         if key.startswith("form/form_data/api/v1/"):
    #             cache.delete("/" + key)
    #     except Exception as e:
    #         print(e)


@receiver(post_delete, sender=FormData)
def update_cache_ondelte_fd(sender, instance, **kwargs):
    # updated the form_id
    mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
    for i in mem.keys():
        key = i.partition("/")[-1]
        try:
            if key.startswith("form/form_data/api/v1/"):
                cache.delete("/" + key)
        except Exception as e:
            payload = json.dumps({"called": "in except1", "key": key, "error": str(e)})
            response = requests.request("POST", url, headers={}, data=payload)


@receiver(post_save, sender=AppliedPosition)
def update_cache(sender, instance, created, **kwargs):
    pass
    # mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
    # for i in mem.keys():
    #     key = i.partition("/")[-1]
    #     try:
    #         if key.startswith("form/applied_position/api/v1/"):
    #             cache.delete("/" + key)
    #         if key.startswith("form/form_data/api/v1/"):
    #             cache.delete("/" + key)
    #         if key.startswith("form/graph/api/v1/"):
    #             cache.delete("/" + key)
    #         if key.startswith("form/op-applied_position/api/v1/"):
    #             cache.delete("/" + key)
    #     except Exception as e:
    #         print(e)


@receiver(post_delete, sender=AppliedPosition)
def update_cache_ondelte_ap(sender, instance, **kwargs):
    mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
    for i in mem.keys():
        try:
            key = i.partition("/")[-1]
            if key.startswith("form/applied_position/api/v1/"):
                cache.delete("/" + key)
            if key.startswith("form/form_data/api/v1/"):
                cache.delete("/" + key)
            if key.startswith("form/graph/api/v1/"):
                cache.delete("/" + key)
            if key.startswith("form/op-applied_position/api/v1/"):
                cache.delete("/" + key)
        except Exception as e:
            print(e)


@receiver(post_save, sender=SavedPosition)
def update_cache_saved_pos(sender, instance, created, **kwargs):
    mem = MemcachedStats(settings.CACHE_BE_LOCATION, settings.CACHE_BE_PORT)
    for i in mem.keys():
        key = i.partition("/")[-1]
        try:
            if key.startswith("form/form_data/api/v1/"):
                cache.delete("/" + key)
        except Exception as e:
            print(e)


@receiver(post_save, sender=OfferLetter)
def update_cache(sender, instance, created, **kwargs):
    if created:
        show_offer_id = instance.offered_to.company.offer_id
        instance.show_offer_id = show_offer_id + 1
        instance.offered_to.company.offer_id = show_offer_id + 1
        instance.save()
        instance.offered_to.company.save()
