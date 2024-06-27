from django.apps import AppConfig
from django.urls import path, include


class TomTnsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tom_tns'

    def target_detail_buttons(self):
        """
        Integration point for adding buttons to the target detail view.
        This method should return a list of dictionaries, each containing the keys:
        - 'namespace': The namespace of the app that provides the button's view
        - 'title': The title of the button
        - 'class': The CSS class of the button
        - 'text': The text of the button
        """
        return {'namespace': 'tns:report-tns',
                'title': 'TNS',
                'class': 'btn  btn-info',
                'text': 'TNS',
                }

    def include_url_paths(self):
        """
        Integration point for adding URL patterns to the Tom Common URL configuration.
        This method should return a list of URL patterns to be included in the main URL configuration.
        """
        urlpatterns = [
            path('tns/', include('tom_tns.urls', namespace='tns'))
        ]
        return urlpatterns
