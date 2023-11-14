import requests.exceptions
from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic.edit import ProcessFormView, TemplateResponseMixin, FormMixin, FormView
from django.views.generic.base import TemplateView
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.contrib import messages
from guardian.mixins import PermissionListMixin

from tom_tns.forms import TNSReportForm, TNSClassifyForm
from tom_tns.tns_report import get_tns_credentials, get_tns_values, send_tns_report, get_tns_report_reply,\
    BadTnsRequest
from tom_targets.models import Target, TargetName

import json


TNS_URL = 'https://sandbox.wis-tns.org/api'  # TODO: change this to the main site
TNS_credentials = get_tns_credentials()
TNS_MARKER = 'tns_marker' + json.dumps({'tns_id': TNS_credentials['bot_id'],
                                        'type': 'bot',
                                        'name': TNS_credentials['bot_name']})
TNS_FILTER_IDS = {name: fid for fid, name in get_tns_values('filters')}
TNS_INSTRUMENT_IDS = {name: iid for iid, name in get_tns_values('instruments')}
TNS_CLASSIFICATION_IDS = {name: cid for cid, name in get_tns_values('object_types')}


class TNSFormView(PermissionListMixin, TemplateView):
    template_name = 'tom_tns/tns_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target = Target.objects.get(pk=self.kwargs['pk'])
        context['target'] = target
        # We want to establish a default tab to display.
        # by default, we start on report, but change to classify if the target name starts with AT
        # If the target has an SN name, we warn the user that the target has likely been classified already.
        context['default_form'] = 'report'
        for name in target.names:
            if name.upper().startswith('AT'):
                context['default_form'] = 'classify'
            if name.upper().startswith('SN'):
                context['default_form'] = 'supernova'
                break
        return context


class TNSSubmitView(FormView):
    success_url = reverse_lazy('targets:list')

    def form_invalid(self, form):
        messages.error(self.request, 'The following error was encountered when submitting to the TNS: '
                                     f'{form.errors.as_json()}')
        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form):
        try:
            tns_report = form.generate_tns_report()
            report_id = send_tns_report(json.dumps(tns_report))
            iau_name = get_tns_report_reply(report_id, self.request)
            # update the target name
            if iau_name is not None:
                target = Target.objects.get(pk=self.kwargs['pk'])
                old_name = target.name
                target.name = iau_name
                target.save()
                new_alias = TargetName(name=old_name, target=target)
                new_alias.save()
        except (requests.exceptions.HTTPError, BadTnsRequest) as e:
            messages.error(self.request, f'TNS returned an error: {e}')
        return HttpResponseRedirect(self.get_success_url())
