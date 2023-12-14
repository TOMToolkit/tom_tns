from django.apps import AppConfig


class TomTnsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tom_tns'
    integration_points = {'target_detail_button': {'namespace': 'tns:report-tns',
                                                   'title': 'TNS',
                                                   'class': 'btn  btn-info',
                                                   'text': 'TNS',
                                                   }
                          }
