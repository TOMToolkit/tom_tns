import requests
from urllib.parse import urljoin

from django.core.cache import cache
from django.conf import settings

import json
import logging
logger = logging.getLogger(__name__)


def get_tns_credentials():
    """
    Get the TNS credentials from settings.py.
    """
    return settings.BROKERS['TNS']


def get_tns_values(option_list):
    """ Retrieve the TNS options. These are cached for one hour.
    Returns a list of tuples, each tuple containing the option value and the option label.
    """
    all_tns_values = cache.get("all_tns_values", {})
    if not all_tns_values:
        all_tns_values, _ = populate_tns_values()
    selected_values = all_tns_values[option_list]
    tuple_list = []
    if isinstance(selected_values, list):
        tuple_list = [(v, v) for v in selected_values]
    if isinstance(selected_values, dict):
        tuple_list = [(k, v) for k, v in selected_values.items()]
    return tuple_list


def get_reverse_tns_values(option_list, value=None):
    """ Retrieve the reverse mapping of TNS options used to go from option to value.
        I.e. reversed_tns_values['groups'] = {
            'group name 1': 1,
            'group name 2': 4,
            'group whatever': 129
        }
    """
    reversed_tns_values = cache.get("reverse_tns_values", {})
    if not reversed_tns_values:
        _, reversed_tns_values = populate_tns_values()
    if not value:
        return reversed_tns_values[option_list]
    try:
        return reversed_tns_values[option_list][value], value
    except KeyError:
        return None


def populate_tns_values():
    """pull all the values from the TNS API"""

    # Need to spoof a web based user agent or TNS will block the request :(
    SPOOF_USER_AGENT = 'Mozilla/5.0 (X11; Linux i686; rv:110.0) Gecko/20100101 Firefox/110.0.'

    tns_base_url = get_tns_credentials()['tns_base_url']
    all_tns_values = {}
    reversed_tns_values = {}
    try:
        resp = requests.get(urljoin(tns_base_url, 'api/values/'),
                            headers={'user-agent': SPOOF_USER_AGENT})
        resp.raise_for_status()
        all_tns_values = resp.json().get('data', {})
        reversed_tns_values = reverse_tns_values(all_tns_values)
        cache.set("all_tns_values", all_tns_values, 3600)
        cache.set("reverse_tns_values", reversed_tns_values, 3600)
    except Exception as e:
        logging.warning(f"Failed to retrieve tns values: {repr(e)}")
    return all_tns_values, reversed_tns_values


def reverse_tns_values(all_tns_values):
    reversed_tns_values = {}
    for key, values in all_tns_values.items():
        if isinstance(values, list):
            reversed_tns_values[key] = {value: index for index, value in enumerate(values)}
        elif isinstance(values, dict):
            reversed_tns_values[key] = {v: k for k, v in values.items()}
    return reversed_tns_values


def build_file_dict(files):
    """
    Build a dictionary of files to upload to the TNS.
    """
    file_load = {}
    i = 0
    for file in files:
        if files[file]:
            file_load[f'file[{i}]'] = (files[file].name, files[file].open(), files[file].content_type)
            files[file] = f'file[{i}]'
            i += 1
    return file_load, files


def pre_upload_files_to_tns(files):
    """
    Upload files to the Transient Name Server according to this manual:
    https://sandbox.wis-tns.org/sites/default/files/api/TNS_bulk_reports_manual.pdf
    """
    tns_credentials = get_tns_credentials()
    file_load, files = build_file_dict(files)
    tns_marker = 'tns_marker' + json.dumps({'tns_id': tns_credentials['bot_id'],
                                            'type': 'bot',
                                            'name': tns_credentials['bot_name']})
    json_data = {'api_key': tns_credentials['api_key']}
    response = requests.post(tns_credentials['tns_base_url'] + '/file-upload', headers={'User-Agent': tns_marker},
                             data=json_data, files=file_load)
    response.raise_for_status()
    new_filenames = response.json()['data']
    logger.info(f"Uploaded {', '.join(new_filenames)} to the TNS")

    return new_filenames


def send_tns_report(data):
    """
    Send a JSON bulk report to the Transient Name Server according to this manual:
    https://sandbox.wis-tns.org/sites/default/files/api/TNS_bulk_reports_manual.pdf
    """
    json_data = {'api_key': TNS['api_key'], 'data': data}
    response = requests.post(TNS_URL + '/bulk-report', headers={'User-Agent': TNS_MARKER}, data=json_data)
    response.raise_for_status()
    report_id = response.json()['data']['report_id']
    logger.info(f'Sent TNS report ID {report_id:d}')
    return report_id


def get_tns_report_reply(report_id, request):
    """
    Get feedback from the Transient Name Server in response to a bulk report according to this manual:
    https://sandbox.wis-tns.org/sites/default/files/api/TNS_bulk_reports_manual.pdf

    Posts an informational message in a banner on the page using ``request``
    """
    json_data = {'api_key': TNS['api_key'], 'report_id': report_id}
    for _ in range(6):
        time.sleep(5)
        response = requests.post(TNS_URL + '/bulk-report-reply', headers={'User-Agent': TNS_MARKER}, data=json_data)
        if response.ok:
            break
    response.raise_for_status()
    feedback_section = response.json()['data']['feedback']
    feedbacks = []
    if 'at_report' in feedback_section:
        feedbacks += feedback_section['at_report']
    if 'classification_report' in feedback_section:
        feedbacks += feedback_section['classification_report'][0]['classification_messages']
    for feedback in feedbacks:
        if '100' in feedback:  # transient object was inserted
            iau_name = 'AT' + feedback['100']['objname']
            log_message = f'New transient {iau_name} was created'
            logger.info(log_message)
            messages.success(request, log_message)
            break
        elif '101' in feedback:  # transient object exists
            iau_name = feedback['101']['prefix'] + feedback['101']['objname']
            log_message = f'Existing transient {iau_name} was reported'
            logger.info(log_message)
            messages.info(request, log_message)
            break
        elif '121' in feedback:  # object name prefix has changed
            iau_name = feedback['121']['new_object_name']
            log_message = f'Transient name changed to {iau_name}'
            logger.info(log_message)
            messages.success(request, log_message)
            break
    else:  # this should never happen
        iau_name = None
        log_message = 'Problem getting response from TNS'
        logger.error(log_message)
        messages.error(request, log_message)
    return iau_name