from django.urls import path

from tom_tns.views import TNSFormView

app_name = 'tom_tns'

urlpatterns = [
    path('<int:pk>/report/', TNSFormView.as_view(), name='report-tns'),
]
