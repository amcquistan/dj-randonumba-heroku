from django import template

from rest_framework.authtoken.models import Token

register = template.Library()

@register.simple_tag(takes_context=True, name='authtoken')
def authtoken(context):
    token_key = ''
    if context['request'].user.is_autheticated:
        token, _ = Token.objects.get_or_create(user=context['request'].user)
        token_key = token.key

    return token_key
