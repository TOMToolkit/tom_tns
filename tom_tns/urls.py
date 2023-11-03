from django.urls import path

from tom_tns.views import TNSFormView

app_name = 'tom_tns'

urlpatterns = [
    path('report/', TNSFormView.as_view(), name='report-tns'),
]
