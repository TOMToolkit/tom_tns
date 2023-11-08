from django import forms
from django.conf import settings

from tom_tns.tns_report import get_tns_values, get_tns_credentials, get_reverse_tns_values

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML
from crispy_forms.bootstrap import AppendedText
from datetime import datetime
import json
import os


class TNSReportForm(forms.Form):
    ra = forms.FloatField(label='R.A.')
    dec = forms.FloatField(label='Dec.')
    reporting_group = forms.ChoiceField(choices=[])
    discovery_data_source = forms.ChoiceField(choices=[])
    reporter = forms.CharField(widget=forms.Textarea(attrs={'rows': 1}))
    discovery_date = forms.DateTimeField(initial=datetime.utcnow())
    at_type = forms.ChoiceField(choices=[], label='AT type')
    archive = forms.ChoiceField(choices=[])
    archival_remarks = forms.CharField(initial="CSS")
    observation_date = forms.DateTimeField()
    flux = forms.FloatField()
    flux_error = forms.FloatField()
    flux_units = forms.ChoiceField(choices=[])
    filter = forms.ChoiceField(choices=[])
    instrument = forms.ChoiceField(choices=[])
    limiting_flux = forms.FloatField(required=False)
    exposure_time = forms.FloatField(required=False)
    observer = forms.CharField(required=False)
    discovery_remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 1}))
    photometry_remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 1}))
    nondetection_remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 1}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reporting_group'].choices = get_tns_values('groups')
        self.fields['discovery_data_source'].choices = get_tns_values('groups')
        self.fields['at_type'].choices = get_tns_values('at_types')
        self.fields['at_type'].initial = (1, "PSN")
        self.fields['filter'].choices = get_tns_values('filters')
        self.fields['filter'].initial = (22, "r-Sloan")
        self.fields['archive'].choices = get_tns_values('archives')
        self.fields['instrument'].choices = get_tns_values('instruments')
        self.fields['instrument'].initial = (0, "Other")
        self.fields['flux_units'].choices = get_tns_values('units')
        self.fields['flux_units'].initial = (1, "ABMag")

        # set initial group if tom_name is in the list of tns group names
        tns_group_name = get_tns_credentials().get('group_name', None)
        if not tns_group_name:
            tns_group_name = settings.TOM_NAME
        default_group = get_reverse_tns_values('groups', tns_group_name)
        if default_group:
            self.fields['reporting_group'].initial = default_group
            self.fields['discovery_data_source'].initial = default_group

        self.helper = FormHelper()
        self.helper.layout = Layout(
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
            Row(
                Column('archive'),
                Column('archival_remarks'),
                Column('nondetection_remarks', css_class='col-md-6'),
            ),
            Row(Column(Submit('submit', 'Submit Report'))),
        )

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
                                "comments": self.cleaned_data['comments'],
                            },
                        }
                    },
                }
            }
        }
        return json.dumps(report_data)


class TargetClassifyForm(forms.Form):
    name = forms.CharField()
    classifier = forms.CharField(widget=forms.Textarea(attrs={'rows': 1}))
    classification = forms.ChoiceField(choices=[], initial=(1, "SN"))
    redshift = forms.FloatField(required=False)
    group = forms.ChoiceField(choices=[
        (66, "SAGUARO"),
    ], initial=(66, "SAGUARO"))
    classification_remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 1}))
    observation_date = forms.DateTimeField()
    instrument = forms.ChoiceField(choices=[], initial=(0, "Other"))
    exposure_time = forms.FloatField(required=False)
    observer = forms.CharField()
    reducer = forms.CharField(required=False)
    spectrum_type = forms.ChoiceField(choices=[
        (1, 'Object'),
        (2, 'Host'),
        (3, 'Sky'),
        (4, 'Arcs'),
        (5, 'Synthetic'),
    ])
    ascii_file = forms.FileField(label='ASCII file')
    fits_file = forms.FileField(label='FITS file', required=False)
    spectrum_remarks = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 1}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('classifier', css_class='col-md-8'),
                Column('group'),
            ),
            Row(
                Column('name'),
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
            Row(Column('spectrum_remarks')),
            Row(Column(Submit('submit', 'Submit Report'))),
        )

    def files_to_upload(self):
        files_to_upload = {}
        if self.cleaned_data['ascii_file'] is not None:
            files_to_upload['files[0]'] = (
                os.path.basename(self.cleaned_data['ascii_file'].name),
                self.cleaned_data['ascii_file'].open(),
                'text/plain'
            )
        if self.cleaned_data['fits_file'] is not None:
            files_to_upload['files[1]'] = (
                os.path.basename(self.cleaned_data['fits_file'].name),
                self.cleaned_data['fits_file'].open(),
                'application/fits'
            )
        return files_to_upload

    def generate_tns_report(self, new_filenames=None):
        """
        Generate TNS bulk classification report according to the schema in this manual:
        https://sandbox.wis-tns.org/sites/default/files/api/TNS_bulk_reports_manual.pdf

        Returns the report as a JSON-formatted string
        """
        if new_filenames is None:
            ascii_filename = os.path.basename(self.cleaned_data['ascii_file'].name)
        else:
            ascii_filename = new_filenames[0]
        report_data = {
            "classification_report": {
                "0": {
                    "name": self.cleaned_data['name'],
                    "classifier": self.cleaned_data['classifier'],
                    "objtypeid": self.cleaned_data['classification'],
                    "redshift": self.cleaned_data['redshift'],
                    "groupid": self.cleaned_data['group'],
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
                                "ascii_file": ascii_filename,
                                "remarks": self.cleaned_data['spectrum_remarks'],
                            },
                        }
                    },
                }
            }
        }
        if self.cleaned_data['fits_file'] is not None:
            if new_filenames is None:
                fits_filename = os.path.basename(self.cleaned_data['fits_file'].name)
            else:
                fits_filename = new_filenames[1]
            report_data['classification_report']['0']['spectra']['spectra_group']['0']['fits_file'] = fits_filename
        return json.dumps(report_data)
