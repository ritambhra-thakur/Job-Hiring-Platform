from django.contrib import admin
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

# Register your models here.
admin.site.unregister(BlacklistedToken)
admin.site.unregister(OutstandingToken)
