import requests
import os

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from tom_tns.tns_api import (get_tns_values, get_tns_credentials, get_reverse_tns_values,
                             pre_upload_files_to_tns, submit_through_hermes)
from tom_dataproducts.models import DataProduct

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML
from crispy_forms.bootstrap import AppendedText, Alert, Accordion, AccordionGroup
from datetime import datetime


HERMES_FLUX_UNITS = [
    ("AB mag", "AB mag"), ("Vega mag", "Vega mag"),
    ("mJy", "mJy"), ("erg / s / cm² / Å", "erg / s / cm² / Å")
]


class BaseReportForm(forms.Form):
    def is_set(self, field):
        if field in self.cleaned_data and self.cleaned_data[field]:
            return True
        return False


class TNSReportForm(BaseReportForm):
    submitter = forms.CharField(required=True, widget=forms.HiddenInput())
    object_name = forms.CharField(required=True, widget=forms.HiddenInput())
    ra = forms.FloatField(label='R.A.')
    dec = forms.FloatField(label='Dec.')
    reporting_group = forms.ChoiceField(choices=[])
    discovery_data_source = forms.ChoiceField(choices=[])
    reporter = forms.CharField(widget=forms.Textarea(attrs={'rows': 1}), label='Reporter Name(s) / Author List')
    discovery_date = forms.DateTimeField(initial=datetime.utcnow())
    at_type = forms.ChoiceField(choices=[], label='AT type')
    archive = forms.ChoiceField(required=False, choices=[])
    archival_remarks = forms.CharField(required=False)
    nondetection_observation_date = forms.DateTimeField(required=False, label='Observation date')
    nondetection_flux = forms.FloatField(required=False, label='Flux')
    nondetection_flux_units = forms.ChoiceField(choices=[], required=False, label='Flux units')
    nondetection_filter = forms.ChoiceField(choices=[], required=False, label='Filter')
    nondetection_instrument = forms.ChoiceField(choices=[], required=False, label='Instrument')
    nondetection_observer = forms.CharField(required=False, label='Observer')
    nondetection_exposure_time = forms.FloatField(required=False, label='Exposure time')
    observation_date = forms.DateTimeField()
    flux = forms.FloatField()
    flux_error = forms.FloatField()
    flux_units = forms.ChoiceField(choices=[])
    filter = forms.ChoiceField(choices=[])
    instrument = forms.ChoiceField(choices=[])
    limiting_flux = forms.FloatField(required=False)
    exposure_time = forms.FloatField(required=False)
    observer = forms.CharField(required=False)
    discovery_remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))
    photometry_remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))
    nondetection_remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, **kwargs):
        """
        Initialize choices from TNS API values, and set common defaults.
        Also define the form layout using crispy_forms.
        """
        super().__init__(*args, **kwargs)
        self.fields['discovery_data_source'].choices = sorted(get_tns_values('groups'), key=lambda x: x[1])
        self.fields['at_type'].choices = get_tns_values('at_types')
        self.fields['at_type'].initial = (1, "PSN")
        self.fields['filter'].choices = get_tns_values('filters')
        self.fields['filter'].initial = ("22", "r-Sloan")
        self.fields['nondetection_filter'].choices = get_tns_values('filters')
        self.fields['nondetection_filter'].initial = ("22", "r-Sloan")
        self.fields['archive'].choices = get_tns_values('archives')
        self.fields['archive'].initial = ("0", "Other")
        self.fields['instrument'].choices = get_tns_values('instruments')
        self.fields['instrument'].initial = ("0", "Other")
        self.fields['nondetection_instrument'].choices = get_tns_values('instruments')
        self.fields['nondetection_instrument'].initial = ("0", "Other")
        if submit_through_hermes():
            self.fields['flux_units'].choices = HERMES_FLUX_UNITS
            self.fields['flux_units'].initial = ("AB mag", "AB mag")
            self.fields['nondetection_flux_units'].choices = HERMES_FLUX_UNITS
            self.fields['nondetection_flux_units'].initial = ("AB mag", "AB mag")
        else:
            self.fields['flux_units'].choices = get_tns_values('units')
            self.fields['flux_units'].initial = (1, "ABMag")
            self.fields['nondetection_flux_units'].choices = get_tns_values('units')
            self.fields['nondetection_flux_units'].initial = (1, "ABMag")

        # set choices of reporting groups to list set in settings.py
        bot_tns_group_names = get_tns_credentials().get('group_names', [])
        if not bot_tns_group_names:
            bot_tns_group_names = [settings.TOM_NAME]
        tns_group_list = []
        for bot_group_name in bot_tns_group_names:
            if get_reverse_tns_values('groups', bot_group_name):
                tns_group_list.append(get_reverse_tns_values('groups', bot_group_name))
        tns_group_list.append(get_reverse_tns_values('groups', 'None'))
        self.fields['reporting_group'].choices = tns_group_list
        # set initial group for discovery source if tom_name is in the list of tns group names
        default_group = tns_group_list[0]
        if default_group:
            self.fields['discovery_data_source'].initial = default_group

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'submitter', 'object_name',
            Row(
                Column('reporter', css_class='col-md-6'),
                Column('reporting_group'),
                Column('discovery_data_source'),
            ),
            Row(
                Column(AppendedText('ra', 'deg')),
                Column(AppendedText('dec', 'deg')),
                Column('discovery_date'),
                Column('at_type'),
            ),
            Row(Column('discovery_remarks')),
            Row(HTML('<h4>Discovery Photometry</h4>')),
            Row(
                Column('observation_date'),
                Column('instrument'),
                Column('limiting_flux'),
                Column('observer'),
            ),
            Row(
                Column('flux'),
                Column('flux_error'),
                Column('flux_units'),
                Column('filter'),
            ),
            Row(Column('photometry_remarks')),
            Row(HTML('<h4>Last Nondetection</h4>')),
            Alert(
                content="""Fill out either the Archive information,
                           or the Detection information for the last nondetection
                        """,
                css_class='alert-warning'
            ),
            Accordion(
                AccordionGroup('Archive information',
                               Row(
                                    Column('archive'),
                                    Column('archival_remarks'),
                                  ),
                               ),
                AccordionGroup('Detection information',
                               Row(
                                    Column('nondetection_observation_date'),
                                    Column('nondetection_instrument'),
                                    Column('nondetection_exposure_time'),
                                    Column('nondetection_observer'),
                                  ),
                               Row(
                                    Column('nondetection_flux'),
                                    Column('nondetection_flux_units'),
                                    Column('nondetection_filter'),
                                  ),
                               Row(Column('nondetection_remarks', css_class='col-md-12'))
                               )
            ),
            Row(Column(Submit('submit', 'Submit Report'))),
        )

    def clean(self):
        super().clean()
        # Either the archival info or nondetection flux info must be set for a valid TNS submission
        if not self.is_set('archive') or not self.is_set('archival_remarks'):
            if any([not self.is_set(field) for field in [
                'nondetection_flux', 'nondetection_instrument', 'nondetection_filter', 'nondetection_observation_date'
            ]]):
                raise ValidationError(
                    "Must set either last nondetection archival information,"
                    "or last nondetection flux, obsdate, filter and instrument"
                )

    def generate_hermes_report(self):
        """
        Generate Hermes TNS discovery report according to the hermes schema

        Returns the report as a Dict to be sent as JSON
        """
        hermes_report = {
            'topic': 'hermes.test',
            'title': f'{self.cleaned_data["object_name"]} TNS discovery report',
            'submit_to_tns': True,
            'submitter': self.cleaned_data['submitter'],
            'authors': self.cleaned_data['reporter'],  # TODO: Set the initial authors on the field from the settings
            'data': {
                'targets': [{
                    'name': self.cleaned_data['object_name'],
                    'ra': self.cleaned_data['ra'],
                    'dec': self.cleaned_data['dec'],
                    'new_discovery': True,
                    'discovery_info': {
                        'date': self.cleaned_data['discovery_date'].isoformat(),
                        'discovery_source': dict(
                            self.fields['discovery_data_source'].choices)[self.cleaned_data['discovery_data_source']],
                        'reporting_group': dict(
                            self.fields['reporting_group'].choices)[self.cleaned_data['reporting_group']],
                        'transient_type': dict(self.fields['at_type'].choices)[int(self.cleaned_data['at_type'])],
                    }
                }],
                'photometry': [{
                    'target_name': self.cleaned_data['object_name'],
                    'date_obs': self.cleaned_data['observation_date'].isoformat(),
                    'instrument': dict(self.fields['instrument'].choices)[self.cleaned_data['instrument']],
                    'bandpass': dict(self.fields['filter'].choices)[self.cleaned_data['filter']],
                    "brightness": self.cleaned_data['flux'],
                    "brightness_error": self.cleaned_data['flux_error'],
                    "brightness_unit": self.cleaned_data['flux_units'],
                }]
            },
        }
        if self.is_set('discovery_remarks'):
            hermes_report['data']['targets'][0]['comments'] = self.cleaned_data['discovery_remarks']
        if self.is_set('photometry_remarks'):
            hermes_report['data']['photometry'][0]['comments'] = self.cleaned_data['photometry_remarks']
        if self.is_set('exposure_time'):
            hermes_report['data']['photometry'][0]['exposure_time'] = self.cleaned_data['exposure_time']
        if self.is_set('observer'):
            hermes_report['data']['photometry'][0]['observer'] = self.cleaned_data['observer']
        if self.is_set('limiting_flux'):
            hermes_report['data']['photometry'][0]['limiting_brightness'] = self.cleaned_data['limiting_flux']

        if self.is_set('archive') and self.is_set('archival_remarks'):
            discovery_info = hermes_report['data']['targets'][0]['discovery_info']
            discovery_info['nondetection_source'] = dict(
                self.fields['archive'].choices)[self.cleaned_data['archive']]
            discovery_info['nondetection_comments'] = self.cleaned_data['archival_remarks']
        elif all([self.is_set(field) for field in [
            'nondetection_flux', 'nondetection_instrument', 'nondetection_filter', 'nondetection_observation_date'
        ]]):
            nondetection = {
                'limiting_brightness': self.cleaned_data['nondetection_flux'],
                'limiting_brightness_unit': self.cleaned_data['nondetection_flux_units'],
                'date_obs': self.cleaned_data['nondetection_observation_date'],
                'bandpass': self.cleaned_data['nondetection_filter'],
                'instrument': self.cleaned_data['nondetection_instrument'],
            }
            if self.is_set('nondetection_exposure_time'):
                nondetection['exposure_time'] = self.cleaned_data['nondetection_exposure_time']
            if self.is_set('nondetection_observer'):
                nondetection['observer'] = self.cleaned_data['nondetection_observer']
            if self.is_set('nondetection_remarks'):
                nondetection['comments'] = self.cleaned_data['nondetection_remarks']
            hermes_report['data']['photometry'].append(nondetection)

        return hermes_report, []

    def generate_tns_report(self):
        """
        Generate TNS bulk transient report according to the schema in this manual:
        https://sandbox.wis-tns.org/sites/default/files/api/TNS_bulk_reports_manual.pdf

        Returns the report as a JSON-formatted string
        """
        report_data = {
            "at_report": {
                "0": {
                    "ra": {
                        "value": self.cleaned_data['ra'],
                    },
                    "dec": {
                        "value": self.cleaned_data['dec'],
                    },
                    "reporting_group_id": self.cleaned_data['reporting_group'],
                    "discovery_data_source_id": self.cleaned_data['discovery_data_source'],
                    "reporter": self.cleaned_data['reporter'],
                    "discovery_datetime": self.cleaned_data['discovery_date'].strftime('%Y-%m-%d %H:%M:%S'),
                    "at_type": self.cleaned_data['at_type'],
                    "remarks": self.cleaned_data["discovery_remarks"],
                    "non_detection": {
                        "archiveid": self.cleaned_data['archive'],
                        "archival_remarks": self.cleaned_data['archival_remarks'],
                        "comments": self.cleaned_data['nondetection_remarks'],
                    },
                    "photometry": {
                        "photometry_group": {
                            "0": {
                                "obsdate": self.cleaned_data['observation_date'].strftime('%Y-%m-%d %H:%M:%S'),
                                "flux": self.cleaned_data['flux'],
                                "flux_error": self.cleaned_data['flux_error'],
                                "flux_units": self.cleaned_data['flux_units'],
                                "filter_value": self.cleaned_data['filter'],
                                "instrument_value": self.cleaned_data['instrument'],
                                "limiting_flux": self.cleaned_data['limiting_flux'],
                                "exptime": self.cleaned_data['exposure_time'],
                                "observer": self.cleaned_data['observer'],
                                "comments": self.cleaned_data['photometry_remarks'],
                            },
                        }
                    },
                }
            }
        }
        return report_data


class TNSClassifyForm(BaseReportForm):
    submitter = forms.CharField(required=False, widget=forms.HiddenInput())
    object_name = forms.CharField(required=False)
    ra = forms.FloatField(required=False, widget=forms.HiddenInput())
    dec = forms.FloatField(required=False, widget=forms.HiddenInput())
    classifier = forms.CharField(widget=forms.Textarea(attrs={'rows': 1}), label='Classifier Name(s) / Author List')
    classification = forms.ChoiceField(choices=[])
    redshift = forms.FloatField(required=False, widget=forms.TextInput())
    reporting_group = forms.ChoiceField(choices=[])
    classification_remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))
    observation_date = forms.DateTimeField()
    instrument = forms.ChoiceField(choices=[])
    exposure_time = forms.FloatField(required=False)
    observer = forms.CharField()
    reducer = forms.CharField(required=False)
    spectrum_type = forms.ChoiceField(choices=[])
    ascii_file = forms.ChoiceField(label='ASCII file', choices=[], required=True)
    fits_file = forms.ChoiceField(label='FITS file', choices=[], required=False)
    ascii_file_description = forms.CharField(label='ASCII file description', required=False)
    fits_file_description = forms.CharField(label='FITS file description', required=False)
    ascii_file_override = forms.FileField(label='ASCII file override', required=False, widget=forms.FileInput())
    fits_file_override = forms.FileField(label='FITS file override', required=False, widget=forms.FileInput())
    spectrum_remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, **kwargs):
        """
        Set initial choices for the classification form using the TNS API values and set default values.
        Also define the form layout using crispy-forms.
        """
        super().__init__(*args, **kwargs)
        self.fields['instrument'].choices = get_tns_values('instruments')
        self.fields['instrument'].initial = (0, "Other")
        self.fields['classification'].choices = get_tns_values('object_types')
        self.fields['classification'].initial = (1, "SN")
        self.fields['spectrum_type'].choices = get_tns_values('spectra_types')
        self.fields['ascii_file'].choices = kwargs['initial']['ascii_file_choices']
        self.fields['fits_file'].choices = kwargs['initial']['fits_file_choices']

        # set choices of reporting groups to list set in settings.py
        bot_tns_group_names = get_tns_credentials().get('group_names', [])
        if not bot_tns_group_names:
            bot_tns_group_names = [settings.TOM_NAME]
        tns_group_list = []
        for bot_group_name in bot_tns_group_names:
            if get_reverse_tns_values('groups', bot_group_name):
                tns_group_list.append(get_reverse_tns_values('groups', bot_group_name))
        tns_group_list.append(get_reverse_tns_values('groups', 'None'))
        self.fields['reporting_group'].choices = tns_group_list

        self.helper = FormHelper()
        self.helper.layout = Layout(
            'submitter', 'ra', 'dec',
            Row(
                Column('classifier', css_class='col-md-8'),
                Column('reporting_group'),
            ),
            Row(
                Column('object_name'),
                Column('classification'),
                Column('redshift'),
            ),
            Row(Column('classification_remarks')),
            Row(HTML('<h4>Classification Spectrum</h4>')),
            Row(
                Column('observation_date'),
                Column('observer'),
                Column('reducer'),
            ),
            Row(
                Column('instrument'),
                Column('exposure_time'),
                Column('spectrum_type'),
            ),
            Row(
                Column('ascii_file'),
                Column('fits_file'),
            ),
            Row(
                Column('ascii_file_override'),
                Column('fits_file_override'),
            ),
            Row(
                Column('ascii_file_description'),
                Column('fits_file_description'),
            ),
            Row(Column('spectrum_remarks')),
            Row(Column(Submit('submit', 'Submit Classification'))),
        )

    def generate_hermes_report(self):
        """
        Generate Hermes TNS classification report according to the hermes schema

        Returns the report as a Dict to be sent as JSON
        """
        if self.is_set('ascii_file_override'):
            ascii_file = self.cleaned_data['ascii_file_override']
        else:
            ascii_file = DataProduct.objects.get(pk=self.cleaned_data['ascii_file']).data
        if self.is_set('fits_file_override'):
            fits_file = self.cleaned_data['fits_file_override']
        elif self.is_set('fits_file'):
            fits_file = DataProduct.objects.get(pk=self.cleaned_data['fits_file']).data
        else:
            fits_file = None
        hermes_report = {
            'topic': 'hermes.test',
            'title': f'{self.cleaned_data["object_name"]} TNS classification report',
            'submit_to_tns': True,
            'submitter': self.cleaned_data['submitter'],
            'authors': self.cleaned_data['classifier'],  # TODO: Set the initial authors on the field from the settings
            'data': {
                'targets': [{
                    'name': self.cleaned_data['object_name'],
                    'ra': self.cleaned_data['ra'],
                    'dec': self.cleaned_data['dec'],
                    'new_discovery': False,
                    'discovery_info': {
                        'reporting_group': dict(
                            self.fields['reporting_group'].choices)[self.cleaned_data['reporting_group']]
                    }
                }],
                'spectroscopy': [{
                    'target_name': self.cleaned_data['object_name'],
                    'date_obs': self.cleaned_data['observation_date'].isoformat(),
                    'instrument': dict(self.fields['instrument'].choices)[self.cleaned_data['instrument']],
                    'spec_type': dict(self.fields['spectrum_type'].choices)[self.cleaned_data['spectrum_type']],
                    'classification': dict(self.fields['classification'].choices)[self.cleaned_data['classification']],
                    'observer': self.cleaned_data['observer'],
                    'file_info': [
                        {
                            'name': os.path.basename(ascii_file.name),
                            'description': self.cleaned_data.get('ascii_file_description', '')
                        }
                    ]
                }]
            },
        }
        files = [ascii_file]
        if self.is_set('redshift'):
            hermes_report['data']['targets'][0]['redshift'] = self.cleaned_data['redshift']
        if self.is_set('classification_remarks'):
            hermes_report['data']['targets'][0]['comments'] = self.cleaned_data['classification_remarks']
        if self.is_set('reducer'):
            hermes_report['data']['spectroscopy'][0]['reducer'] = self.cleaned_data['reducer']
        if self.is_set('exposure_time'):
            hermes_report['data']['spectroscopy'][0]['exposure_time'] = self.cleaned_data['exposure_time']
        if fits_file:
            hermes_report['data']['spectroscopy'][0]['file_info'].append({
                'name': os.path.basename(fits_file.name),
                'description': self.cleaned_data.get('fits_file_description', '')
            })
            files.append(fits_file)
        if self.is_set('spectrum_remarks'):
            hermes_report['data']['spectroscopy'][0]['comments'] = self.cleaned_data['spectrum_remarks']

        return hermes_report, files

    def generate_tns_report(self):
        """
        Generate TNS bulk classification report according to the schema in this manual:
        https://sandbox.wis-tns.org/sites/default/files/api/TNS_bulk_reports_manual.pdf

        Returns the report as a JSON-formatted string
        """
        if self.is_set('ascii_file_override'):
            ascii_file = self.cleaned_data['ascii_file_override']
        else:
            ascii_file = DataProduct.objects.get(pk=self.cleaned_data['ascii_file']).data
        if self.is_set('fits_file_override'):
            fits_file = self.cleaned_data['fits_file_override']
        elif self.is_set('fits_file'):
            fits_file = DataProduct.objects.get(pk=self.cleaned_data['fits_file']).data
        else:
            fits_file = None
        file_list = {'ascii_file': ascii_file,
                     'fits_file': fits_file,
                     'other_files': []}
        try:
            tns_filenames = pre_upload_files_to_tns(file_list)
        except requests.exceptions.HTTPError as e:
            return {'message': f"ERROR: {e}"}
        report_data = {
            "classification_report": {
                "0": {
                    "name": self.cleaned_data['object_name'],
                    "classifier": self.cleaned_data['classifier'],
                    "objtypeid": self.cleaned_data['classification'],
                    "redshift": self.cleaned_data['redshift'],
                    "groupid": self.cleaned_data['reporting_group'],
                    "remarks": self.cleaned_data['classification_remarks'],
                    "spectra": {
                        "spectra-group": {
                            "0": {
                                "obsdate": self.cleaned_data['observation_date'].strftime('%Y-%m-%d %H:%M:%S'),
                                "instrumentid": self.cleaned_data['instrument'],
                                "exptime": self.cleaned_data['exposure_time'],
                                "observer": self.cleaned_data['observer'],
                                "reducer": self.cleaned_data['reducer'],
                                "spectypeid": self.cleaned_data['spectrum_type'],
                                "ascii_file": tns_filenames.get('ascii_file', ''),
                                "fits_file": tns_filenames.get('fits_file', ''),
                                "remarks": self.cleaned_data['spectrum_remarks'],
                            },
                        }
                    },
                }
            }
        }
        return report_data
