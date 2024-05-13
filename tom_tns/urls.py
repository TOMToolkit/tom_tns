from django.urls import path

from tom_tns.views import TNSFormView, TNSSubmitView
from tom_tns.forms import TNSReportForm, TNSClassifyForm

app_name = 'tom_tns'

urlpatterns = [
    path('<int:pk>/', TNSFormView.as_view(), name='report-tns'),
    path('<int:pk>/<int:datum_pk>', TNSFormView.as_view(), name='report-tns'),
    path('<int:pk>/report', TNSSubmitView.as_view(form_class=TNSReportForm), name='submit-report'),
    path('<int:pk>/classify', TNSSubmitView.as_view(form_class=TNSClassifyForm), name='submit-classify'),
]
