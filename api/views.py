import random
import requests

from bs4 import BeautifulSoup

from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import RandoNumbaSerializer
from core.models import RandoNumba



class RandoNumbaView(APIView):
    def get(self, request, format=None):
        numbas = RandoNumba.objects.filter(user=request.user).order_by('-id').all()
        serializer = RandoNumbaSerializer(numbas, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        # fetch and parse quote
        response = requests.get('http://quotes.toscrape.com/random')
        quote_data = {}
        if response.status_code == 200:
            soup = BeautifulSoup(response.text)
            quote = soup.find(class_='quote')
            quote_data['quote'] = quote.find(class_='text').get_text()
            quote_data['author'] = quote.find(class_='author').get_text()

        # create new random number
        rando_numba = RandoNumba.objects.create(
            value=random.randint(settings.RANDO_NUMBA_MIN, settings.RANDO_NUMBA_MAX),
            quote=quote_data,
            user=request.user
        )

        # serialize
        serializer = RandoNumbaSerializer(rando_numba)

        # return result
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

