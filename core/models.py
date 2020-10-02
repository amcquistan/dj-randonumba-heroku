from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import HStoreField

class RandoNumba(models.Model):
    value = models.IntegerField(default=0, null=False, blank=False)
    quote = HStoreField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

