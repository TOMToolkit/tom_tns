from django import template
from django.conf import settings

from tom_tns.tns_api import get_tns_values, map_filter_to_tns, default_authors
from tom_tns.forms import TNSReportForm, TNSClassifyForm

register = template.Library()


# Define form Choices from Cached TNS Values
TNS_FILTER_IDS = {name: fid for fid, name in get_tns_values('filters')}
TNS_INSTRUMENT_IDS = {name: iid for iid, name in get_tns_values('instruments')}
TNS_CLASSIFICATION_IDS = {name: cid for cid, name in get_tns_values('object_types')}


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
    if 'datum' in context:
        reduced_datum = context['datum']
    else:
        # Get photometry if available
        photometry = target.reduceddatum_set.filter(data_type='photometry')
        if photometry.exists():
            reduced_datum = photometry.latest()
    if reduced_datum:
        initial['observation_date'] = reduced_datum.timestamp
        initial['flux'] = reduced_datum.value.get('magnitude')
        initial['flux_error'] = reduced_datum.value.get('error')
        filter_name = reduced_datum.value.get('filter')
        mapped_filter = map_filter_to_tns(filter_name)
        if mapped_filter in TNS_FILTER_IDS:
            initial['filter'] = (TNS_FILTER_IDS[mapped_filter], mapped_filter)
        instrument_name = reduced_datum.value.get('instrument')
        if instrument_name in TNS_INSTRUMENT_IDS:
            initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)
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
    if 'datum' in context:
        reduced_datum = context['datum']
    else:
        spectra = target.reduceddatum_set.filter(data_type='spectroscopy')
        if spectra.exists():
            reduced_datum = spectra.latest()
    if reduced_datum:
        initial['observation_date'] = reduced_datum.timestamp
        if reduced_datum.data_product.get_file_extension().lower() in ['.ascii', '.txt']:
            initial['ascii_file'] = (reduced_datum.data_product.pk, reduced_datum.data_product.get_file_name())
        instrument_name = reduced_datum.value.get('instrument')
        if instrument_name in TNS_INSTRUMENT_IDS:
            initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)

    tns_classify_form = TNSClassifyForm(initial=initial)
    return {'target': target,
            'form': tns_classify_form}
