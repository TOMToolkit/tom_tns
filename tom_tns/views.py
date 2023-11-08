from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic.edit import ProcessFormView, TemplateResponseMixin, FormMixin
from django.shortcuts import redirect
from guardian.mixins import PermissionListMixin

from tom_tns.forms import TNSReportForm
from tom_tns.tns_report import get_tns_credentials, get_tns_values
from tom_targets.models import Target

import json


TNS_URL = 'https://sandbox.wis-tns.org/api'  # TODO: change this to the main site
TNS_credentials = get_tns_credentials()
TNS_MARKER = 'tns_marker' + json.dumps({'tns_id': TNS_credentials['bot_id'],
                                        'type': 'bot',
                                        'name': TNS_credentials['bot_name']})
TNS_FILTER_IDS = {name: fid for fid, name in get_tns_values('filters')}
TNS_INSTRUMENT_IDS = {name: iid for iid, name in get_tns_values('instruments')}
TNS_CLASSIFICATION_IDS = {name: cid for cid, name in get_tns_values('object_types')}


class TNSFormView(PermissionListMixin, TemplateResponseMixin, FormMixin, ProcessFormView):
    """
    View that handles reporting a target to the TNS.
    """
    form_class = TNSReportForm
    template_name = 'tom_tns/tns_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target'] = Target.objects.get(pk=self.kwargs['pk'])
        return context

    def get_initial(self):
        target = Target.objects.get(pk=self.kwargs['pk'])
        initial = {
            'ra': target.ra,
            'dec': target.dec,
            'reporter': f'{self.request.user.get_full_name()}, on behalf of SAGUARO',
        }
        photometry = target.reduceddatum_set.filter(data_type='photometry')
        if photometry.exists():
            reduced_datum = photometry.latest()
            initial['observation_date'] = reduced_datum.timestamp
            initial['flux'] = reduced_datum.value['magnitude']
            initial['flux_error'] = reduced_datum.value['error']
            filter_name = reduced_datum.value.get('filter')
            if filter_name in TNS_FILTER_IDS:
                initial['filter'] = (TNS_FILTER_IDS[filter_name], filter_name)
            instrument_name = reduced_datum.value.get('instrument')
            if instrument_name in TNS_INSTRUMENT_IDS:
                initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)
        return initial

    def form_valid(self, form):
        # report_id = send_tns_report(form.generate_tns_report())
        # iau_name = get_tns_report_reply(report_id, self.request)

        # update the target name
        # if iau_name is not None:
        #     target = Target.objects.get(pk=self.kwargs['pk'])
        #     target.name = iau_name
        #     target.save()
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('targets:detail', kwargs=self.kwargs)
