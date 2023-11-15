import requests
from urllib.parse import urljoin

from django.core.cache import cache
from django.conf import settings
from django.contrib import messages

import json
import time
import logging
logger = logging.getLogger(__name__)


class BadTnsRequest(Exception):
    """ This Exception will be raised by errors during the TNS submission process """
    pass


def get_tns_credentials():
    """
    Get the TNS credentials from settings.py.
    """
    tns_info = settings.BROKERS['TNS']
    tns_info['marker'] = 'tns_marker' + json.dumps({'tns_id': tns_info['bot_id'],
                                                    'type': 'bot',
                                                    'name': tns_info['bot_name']})
    return tns_info


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
        tuple_list = [(i, v) for i, v in enumerate(selected_values)]
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
    new_files = {}
    file_load = {}
    i = 0
    if files['ascii_file']:
        file_load[f'files[{i}]'] = (files['ascii_file'].name, files['ascii_file'].open(), 'text/plain')
        new_files['ascii_file'] = i
        i += 1
    if files['fits_file']:
        file_load[f'files[{i}]'] = (files['fits_file'].name, files['fits_file'].open('rb'), 'application/fits')
        new_files['fits_file'] = i
        i += 1
    return file_load, new_files


def pre_upload_files_to_tns(files):
    """
    Upload files to the Transient Name Server according to this manual:
    https://sandbox.wis-tns.org/sites/default/files/api/TNS_bulk_reports_manual.pdf
    """
    tns_credentials = get_tns_credentials()
    file_load, new_files = build_file_dict(files)
    if not file_load:
        return None
    tns_marker = tns_credentials['marker']
    json_data = {'api_key': tns_credentials['api_key']}
    response = requests.post(tns_credentials['tns_base_url'] + '/file-upload', headers={'User-Agent': tns_marker},
                             data=json_data, files=file_load)
    response.raise_for_status()
    new_filenames = response.json().get('data', {})
    logger.info(f"Uploaded {', '.join(new_filenames)} to the TNS")
    if not new_filenames:
        return None
    for file in new_files:
        try:
            new_files[file] = new_filenames[new_files[file]]
        except IndexError:
            new_files[file] = ''
    return new_files


def send_tns_report(data):
    """
    Send a JSON bulk report to the Transient Name Server according to this manual:
    https://sandbox.wis-tns.org/sites/default/files/api/TNS_bulk_reports_manual.pdf
    """
    tns_info = get_tns_credentials()
    json_data = {'api_key': tns_info['api_key'], 'data': data}
    response = requests.post(tns_info['tns_base_url'] + '/bulk-report',
                             headers={'User-Agent': tns_info['marker']},
                             data=json_data)
    response.raise_for_status()
    report_id = response.json()['data']['report_id']
    logger.info(f'Sent TNS report ID {report_id:d}')
    return report_id


def parse_object_from_tns_response(response_json, request):
    feedback_section = response_json['data']['feedback']
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


def get_tns_report_reply(report_id, request):
    """
    Get feedback from the Transient Name Server in response to a bulk report according to this manual:
    https://sandbox.wis-tns.org/sites/default/files/api/TNS_bulk_reports_manual.pdf

    Posts an informational message in a banner on the page using ``request``
    """
    tns_info = get_tns_credentials()
    reply_data = {'api_key': tns_info['api_key'], 'report_id': report_id}
    attempts = 0
    # TNS Submissions return immediately with an id, which you must then check to see if the message
    # was processed, and if it was accepted or rejected. Here we check up to 10 times, waiting 1s
    # between checks. Under normal circumstances, it should be processed within a few seconds.
    while attempts < 10:
        response = requests.post(tns_info['tns_base_url'] + '/bulk-report-reply',
                                 headers={'User-Agent': tns_info['marker']}, data=reply_data)
        attempts += 1
        # A 404 response means the report has not been processed yet
        if response.status_code == 404:
            time.sleep(1)
        # A 400 response means the report failed with certain errors
        elif response.status_code == 400:
            raise BadTnsRequest(f"TNS submission failed with feedback: "
                                f"{response.json().get('data', {}).get('feedback', {})}")
        # A 200 response means the report was successful, and we can parse out the object name
        elif response.status_code == 200:
            iau_name = parse_object_from_tns_response(response.json(), request)
            break
        else:
            raise BadTnsRequest(f"TNS submission failed with status code {response.status_code}")
    return iau_name