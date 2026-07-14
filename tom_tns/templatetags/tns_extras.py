from django import template
from django.conf import settings

from tom_dataproducts.models import PhotometryReducedDatum, SpectroscopyReducedDatum

from tom_tns.tns_api import (get_tns_values, map_filter_to_tns, map_instrument_to_tns,
                             default_authors)
from tom_tns.forms import TNSReportForm, TNSClassifyForm

register = template.Library()


# Define form Choices from Cached TNS Values
TNS_FILTER_IDS = {name: fid for fid, name in get_tns_values('filters')}
TNS_INSTRUMENT_IDS = {name: iid for iid, name in get_tns_values('instruments')}
TNS_CLASSIFICATION_IDS = {name: cid for cid, name in get_tns_values('objtypes')}
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
        'internal_name': target.name,
        'ra': target.ra,
        'dec': target.dec,
        'submitter': context['request'].user.email,
        'reporter': f"{getattr(context['request'].user, 'get_full_name()', 'Anonymous User')},"
                    f" using {settings.TOM_NAME}",
    }

    reporter = default_authors()
    if reporter:
        initial['reporter'] = reporter

    phot_data = PhotometryReducedDatum.objects.none()
    if 'datum' in context and isinstance(context['datum'], PhotometryReducedDatum):
        phot_data = context['datum']
    else:
        # Get photometry if available
        photometry = target.photometryreduceddatum_set.all()
        if photometry.exists():
            phot_data = photometry.latest("timestamp")

    if phot_data:
        initial['observation_date'] = phot_data.timestamp
        initial['exposure_time'] = phot_data.exposure_time
        instrument_name = map_instrument_to_tns(phot_data.instrument)
        if instrument_name and instrument_name in TNS_INSTRUMENT_IDS:
            initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)
        else:
            instrument_name = map_instrument_to_tns(phot_data.telescope)
            if instrument_name and instrument_name in TNS_INSTRUMENT_IDS:
                initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)
        initial['telescope'] = phot_data.telescope
        mapped_filter = map_filter_to_tns(phot_data.bandpass)
        if mapped_filter and mapped_filter in TNS_FILTER_IDS:
            initial['filter'] = (TNS_FILTER_IDS[mapped_filter], mapped_filter)
        if phot_data.brightness:
            initial['flux'] = phot_data.brightness
        if phot_data.brightness_error:
            initial['flux_error'] = phot_data.brightness_error
        if phot_data.limit:
            initial['limiting_flux'] = phot_data.limit

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
    ascii_files = [(None, '')]
    fits_files = [(None, '')]
    for data_product in target.dataproduct_set.all():
        if data_product.get_file_extension().lower() in ['.ascii', '.txt']:
            ascii_files.append((data_product.pk, data_product.get_file_name()))
        elif data_product.get_file_extension().lower() in ['.fits', '.fits.fz']:
            fits_files.append((data_product.pk, data_product.get_file_name()))
    initial['ascii_file_choices'] = ascii_files
    initial['fits_file_choices'] = fits_files

    # Get the spectra details from the latest spectra reduced datum or one passed in
    spectra_data = SpectroscopyReducedDatum.objects.none()
    if 'datum' in context and isinstance(context['datum'], SpectroscopyReducedDatum):
        spectra_data = context['datum']
    else:
        spectra = target.spectroscopyreduceddatum_set.all()
        if spectra.exists():
            spectra_data = spectra.latest("timestamp")

    if spectra_data:
        initial['observation_date'] = spectra_data.timestamp
        initial['exposure_time'] = spectra_data.exposure_time
        instrument_name = map_instrument_to_tns(spectra_data.instrument)
        if instrument_name and instrument_name in TNS_INSTRUMENT_IDS:
            initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)
        else:
            instrument_name = map_instrument_to_tns(spectra_data.telescope)
            if instrument_name and instrument_name in TNS_INSTRUMENT_IDS:
                initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)
        initial['telescope'] = spectra_data.telescope

        if spectra_data.data_product and spectra_data.data_product.get_file_extension().lower() in ['.ascii', '.txt']:
            initial['ascii_file'] = (spectra_data.data_product.pk, spectra_data.data_product.get_file_name())

    tns_classify_form = TNSClassifyForm(initial=initial)
    return {'target': target,
            'form': tns_classify_form}
