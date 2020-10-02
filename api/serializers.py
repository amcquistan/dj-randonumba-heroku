
from rest_framework import serializers

from core.models import RandoNumba


class RandoNumbaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RandoNumba
        fields = ('id', 'value', 'quote')
