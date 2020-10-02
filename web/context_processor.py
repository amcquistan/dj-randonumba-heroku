from django.conf import settings as dj_settings


def settings(request):
    template_settings = {
      'ENV': dj_settings.ENV,
      'PRODUCTION': dj_settings.PRODUCTION,
      'DEVELOPMENT': dj_settings.DEVELOPMENT
    }
    return {
      'settings': template_settings
    }
