from django import template
from django.conf import settings

from tom_tns.tns_api import get_tns_values
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
        'ra': target.ra,
        'dec': target.dec,
        'reporter': f"{getattr(context['request'].user, 'get_full_name()', 'Anonymous User')},"
                    f" using {settings.TOM_NAME}",
    }
    # Get photometry if available
    photometry = target.reduceddatum_set.filter(data_type='photometry')
    if photometry.exists():
        reduced_datum = photometry.latest()
        initial['observation_date'] = reduced_datum.timestamp
        initial['flux'] = reduced_datum.value.get('magnitude')
        initial['flux_error'] = reduced_datum.value.get('error')
        filter_name = reduced_datum.value.get('filter')
        if filter_name in TNS_FILTER_IDS:
            initial['filter'] = (TNS_FILTER_IDS[filter_name], filter_name)
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
        'classifier': f"{getattr(context['request'].user, 'get_full_name()', 'Anonymous User')},"
                      f" using {settings.TOM_NAME}",
    }
    # Get spectroscopy if available
    spectra = target.reduceddatum_set.filter(data_type='spectroscopy')
    if spectra.exists():
        reduced_datum = spectra.latest()
        initial['observation_date'] = reduced_datum.timestamp
        initial['ascii_file'] = reduced_datum.data_product.data
        instrument_name = reduced_datum.value.get('instrument')
        if instrument_name in TNS_INSTRUMENT_IDS:
            initial['instrument'] = (TNS_INSTRUMENT_IDS[instrument_name], instrument_name)
    tns_classify_form = TNSClassifyForm(initial=initial)
    return {'target': target,
            'form': tns_classify_form}
