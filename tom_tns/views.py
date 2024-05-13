import requests.exceptions

from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.views.generic.base import TemplateView
from django.http import HttpResponseRedirect
from django.contrib import messages
from guardian.mixins import PermissionListMixin

from tom_tns import __version__
from tom_tns.tns_api import (send_tns_report, get_tns_report_reply, get_tns_credentials,
                             submit_through_hermes, BadTnsRequest)
from tom_tns.hermes_api import submit_to_hermes
from tom_targets.models import Target, TargetName
from tom_dataproducts.models import ReducedDatum

import json


class TNSFormView(PermissionListMixin, TemplateView):
    """
    This view is used to display the TNS report forms.
    The default form is the report form, but if the target name starts with AT, we switch to the classification form.
    """
    template_name = 'tom_tns/tns_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['default_form'] = 'report'
        target = Target.objects.get(pk=self.kwargs['pk'])
        if 'datum_pk' in self.kwargs:
            try:
                context['datum'] = ReducedDatum.objects.get(pk=self.kwargs['datum_pk'])
                if context['datum'].data_type == 'spectroscopy':
                    context['default_form'] = 'classify'
            except ReducedDatum.DoesNotExist:
                pass
        context['tns_configured'] = bool(get_tns_credentials())
        context['target'] = target
        context['version'] = __version__  # from tom_tns.__init__.py
        # We want to establish a default tab to display.
        # by default, we start on report, but change to classify if the target name starts with AT.
        # If the target has an SN name, we warn the user that the target has likely been classified already.
        for name in target.names:
            if name.upper().startswith('AT'):
                context['default_form'] = 'classify'
            if name.upper().startswith('SN'):
                context['default_form'] = 'supernova'
                break
        return context


class TNSSubmitView(FormView):
    """
    This View is used to submit the TNS report forms.
    """
    def get_initial(self):
        # Must override get_initial to pass in the file choice options or it will fail validation
        initial = super().get_initial()
        target = Target.objects.get(pk=self.kwargs['pk'])
        ascii_files = []
        fits_files = [(None, '')]
        for data_product in target.dataproduct_set.all():
            if data_product.get_file_extension().lower() in ['.ascii', '.txt']:
                ascii_files.append((data_product.pk, data_product.get_file_name()))
            elif data_product.get_file_extension().lower() in ['.fits', '.fits.fz']:
                fits_files.append((data_product.pk, data_product.get_file_name()))
        initial['ascii_file_choices'] = ascii_files
        initial['fits_file_choices'] = fits_files
        return initial

    def get_success_url(self):
        return reverse_lazy('targets:detail', kwargs=self.kwargs)

    def form_invalid(self, form):
        messages.error(self.request, 'The following error was encountered when submitting to the TNS: '
                                     f'{form.errors.as_json()}')
        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form):
        """
        If the Form is successfully constructed, we generate the TNS report and submit it to the TNS.
        """
        try:
            iau_name = None
            if submit_through_hermes():
                hermes_report, files = form.generate_hermes_report()
                iau_name = submit_to_hermes(hermes_report, files, self.request)
            else:
                # Build TNS Report
                tns_report = form.generate_tns_report()
                # Submit TNS Report
                report_id = send_tns_report(json.dumps(tns_report))
                # Get IAU name from Report Reply
                iau_name = get_tns_report_reply(report_id, self.request)

            if iau_name:
                # update the target name in Tom DB
                target = Target.objects.get(pk=self.kwargs['pk'])
                if target.name != iau_name:
                    old_name = target.name
                    target.name = iau_name
                    target.save()
                    # Save old name as alias
                    new_alias = TargetName(name=old_name, target=target)
                    new_alias.save()
        except (requests.exceptions.HTTPError, BadTnsRequest) as e:
            messages.error(self.request, f'TNS returned an error: {e}')
        return HttpResponseRedirect(self.get_success_url())
