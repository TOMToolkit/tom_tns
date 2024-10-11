from django import template
from django.conf import settings

from tom_dataproducts.alertstreams.hermes import get_hermes_data_converter_class
from tom_tns.tns_api import (get_tns_values, map_filter_to_tns, map_instrument_to_tns,
                             default_authors)
from tom_tns.forms import TNSReportForm, TNSClassifyForm

register = template.Library()


# Define form Choices from Cached TNS Values
TNS_FILTER_IDS = {name: fid for fid, name in get_tns_values('filters')}
TNS_INSTRUMENT_IDS = {name: iid for iid, name in get_tns_values('instruments')}
TNS_CLASSIFICATION_IDS = {name: cid for cid, name in get_tns_values('object_types')}
TNS_SPECTRUM_TYPE_IDS = {name: sid for sid, name in get_tns_values('spectra_types')}


@register.inclusion_tag('tom_tns/partials/tns_report_form.html', takes_context=True)
def report_to_tns(context):
    """
    Build context data for TNS AT Report Form.
    Includes the latest Photometry data if available.
    """
    target = context['target']
    initial = {
        'object_name': target.name,
        'ra': target.ra,
        'dec': target.dec,
        'submitter': context['request'].user.email,
        'reporter': f"{getattr(context['request'].user, 'get_full_name()', 'Anonymous User')},"
                    f" using {settings.TOM_NAME}",
    }

    reporter = default_authors()
    if reporter:
        initial['reporter'] = reporter

    reduced_datum = None
    if 'datum' in context and context['datum'].data_type == 'photometry':
        reduced_datum = context['datum']
        preset_datum = True
    else:
        # Get photometry if available
        photometry = target.reduceddatum_set.filter(data_type='photometry')
        if photometry.exists():
            reduced_datum = photometry.latest()
        preset_datum = False

    if reduced_datum:
        hermes_datum_converter = get_hermes_data_converter_class()(validate=False)
        phot_data = hermes_datum_converter.get_hermes_photometry(reduced_datum)
        initial['observation_date'] = phot_data['date_obs']
        if phot_data.get('exposure_time'):
            initial['exposure_time'] = phot_data['exposure_time']
        instrument_name = map_instrument_to_tns(phot_data.get('instrument', ''))
        if instrument_name and instrument_name in TNS_INSTRUMENT_IDS:
            initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)
        else:
            # Try the hermes 'telescope' field if instrument is not present or doesn't match TNS
            instrument_name = map_instrument_to_tns(phot_data.get('telescope', ''))
            if instrument_name and instrument_name in TNS_INSTRUMENT_IDS:
                initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)
        if preset_datum and phot_data.get('telescope'):
            # Only set the telescope if a preset datum was specified in loading the form
            initial['telescope'] = phot_data['telescope']
        mapped_filter = map_filter_to_tns(phot_data.get('bandpass', ''))
        if mapped_filter and mapped_filter in TNS_FILTER_IDS:
            initial['filter'] = (TNS_FILTER_IDS[mapped_filter], mapped_filter)
        if phot_data.get('brightness'):
            initial['flux'] = phot_data['brightness']
        if phot_data.get('brightness_error'):
            initial['flux_error'] = phot_data['brightness_error']
        if phot_data.get('limiting_brightness'):
            initial['limiting_flux'] = phot_data['limiting_brightness']
        if phot_data.get('observer'):
            initial['observer'] = phot_data['observer']
        if phot_data.get('comments'):
            initial['photometry_remarks'] = phot_data['comments']

    tns_report_form = TNSReportForm(initial=initial)
    return {'target': target,
            'form': tns_report_form}


@register.inclusion_tag('tom_tns/partials/tns_classify_form.html', takes_context=True)
def classify_with_tns(context):
    """
    Build context data for TNS Classification Form.
    Includes the latest Spectroscopy data if available.
    """
    target = context['target']
    initial = {
        'object_name': target.name.replace('AT', '').replace('SN', ''),
        'ra': target.ra,
        'dec': target.dec,
        'submitter': context['request'].user.email,
        'classifier': f"{getattr(context['request'].user, 'get_full_name()', 'Anonymous User')},"
                      f" using {settings.TOM_NAME}",
    }

    classifier = default_authors()
    if classifier:
        initial['classifier'] = classifier

    # Get the list of chocies for ascii and fits files for those fields
    ascii_files = []
    fits_files = [(None, '')]
    for data_product in target.dataproduct_set.all():
        if data_product.get_file_extension().lower() in ['.ascii', '.txt']:
            ascii_files.append((data_product.pk, data_product.get_file_name()))
        elif data_product.get_file_extension().lower() in ['.fits', '.fits.fz']:
            fits_files.append((data_product.pk, data_product.get_file_name()))
    initial['ascii_file_choices'] = ascii_files
    initial['fits_file_choices'] = fits_files

    # Get the spectra details from the latest spectra reduced datum or one passed in
    reduced_datum = None
    if 'datum' in context and context['datum'].data_type == 'spectroscopy':
        reduced_datum = context['datum']
        preset_datum = True
    else:
        spectra = target.reduceddatum_set.filter(data_type='spectroscopy')
        if spectra.exists():
            reduced_datum = spectra.latest()
        preset_datum = False
    if reduced_datum:
        hermes_datum_converter = get_hermes_data_converter_class()(validate=False)
        spectra_data = hermes_datum_converter.get_hermes_spectroscopy(reduced_datum)
        initial['observation_date'] = spectra_data['date_obs']
        if spectra_data.get('exposure_time'):
            initial['exposure_time'] = spectra_data['exposure_time']
        instrument_name = map_instrument_to_tns(spectra_data.get('instrument', ''))
        if instrument_name and instrument_name in TNS_INSTRUMENT_IDS:
            initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)
        else:
            # Try the hermes 'telescope' field if instrument is not present or doesn't match TNS
            instrument_name = map_instrument_to_tns(spectra_data.get('telescope', ''))
            if instrument_name and instrument_name in TNS_INSTRUMENT_IDS:
                initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)
        if preset_datum and spectra_data.get('telescope'):
            # Only set the telescope if a preset datum was specified in loading the form
            initial['telescope'] = spectra_data['telescope']
        if spectra_data.get('reducer'):
            initial['reducer'] = spectra_data['reducer']
        if spectra_data.get('observer'):
            initial['observer'] = spectra_data['observer']
        if spectra_data.get('classification', '') in TNS_CLASSIFICATION_IDS:
            initial['classification'] = (
                TNS_CLASSIFICATION_IDS[spectra_data['classification']], spectra_data['classification']
            )
        if spectra_data.get('spec_type') in TNS_SPECTRUM_TYPE_IDS:
            initial['spectrum_type'] = (
                TNS_SPECTRUM_TYPE_IDS[spectra_data['spec_type']], spectra_data['spec_type']
            )
        if spectra_data.get('comments'):
            initial['spectrum_remarks'] = spectra_data['comments']

        if reduced_datum.data_product and reduced_datum.data_product.get_file_extension().lower() in ['.ascii', '.txt']:
            initial['ascii_file'] = (reduced_datum.data_product.pk, reduced_datum.data_product.get_file_name())

    tns_classify_form = TNSClassifyForm(initial=initial)
    return {'target': target,
            'form': tns_classify_form}
