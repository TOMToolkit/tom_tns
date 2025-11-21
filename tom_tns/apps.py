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
    def target_detail_buttons(self):
        """
        Integration point for adding buttons to the target detail view.
        This method should return a list of dictionaries that include a `partial` key pointing to the path of the html
        profile partial. The `context` key is optional and should point to the dot separated string path to the
        templatetag that will return a dictionary containing new context for the accompanying partial.
        Typically, this partial will be a button or link referencing the current target.
        """
        return [{'partial': f'{self.name}/partials/tns_button.html'}]

    def include_url_paths(self):
        """
        Integration point for adding URL patterns to the Tom Common URL configuration.
        This method should return a list of URL patterns to be included in the main URL configuration.
        """
        urlpatterns = [
            path('tns/', include('tom_tns.urls', namespace='tns'))
        ]
        return urlpatterns
