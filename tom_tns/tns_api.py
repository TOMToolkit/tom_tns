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


def submit_through_hermes():
    """ Check if hermes credentials exist and are setup so TNS messages should be sent through hermes
        Returns True if it should go through hermes, False if it should go directly to TNS
    """
    if hasattr(settings, 'DATA_SHARING') and settings.DATA_SHARING.get('hermes', {}).get('ENABLE_TNS', False):
        return True
    return False


def map_filter_to_tns(filter):
    """ Checks if a filter mapping was set in the settings, and if so returns the mapped value for the filter passed in
    """
    if submit_through_hermes():
        return settings.DATA_SHARING.get('hermes', {}).get('FILTER_MAPPING', {}).get(filter)
    else:
        return settings.BROKERS.get('TNS', {}).get('filter_mapping', {}).get(filter)


def default_authors():
    """ Returns default authors if set in the settings, otherwise empty string.
    """
    if submit_through_hermes():
        return settings.DATA_SHARING.get('hermes', {}).get('DEFAULT_AUTHORS', '')
    else:
        return settings.BROKERS.get('TNS', {}).get('default_authors', '')


def get_tns_credentials():
    """
    Get the TNS credentials from settings.py.
    This should include the bot_id, bot_name, api_key, tns_base_url, and possibly group_name.
    """
    try:
        tns_info = settings.BROKERS['TNS']

        # Build TNS Marker using Bot info if API key is present
        if tns_info.get('api_key', None):
            tns_info['marker'] = 'tns_marker' + json.dumps({'tns_id': tns_info.get('bot_id', None),
                                                            'type': 'bot',
                                                            'name': tns_info.get('bot_name', None)})
        else:
            logger.error("TNS API key not found in settings.py")
            tns_info = {}
    except (KeyError, AttributeError):
        logger.error("TNS credentials not found in settings.py")
        tns_info = {}
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


def get_reverse_tns_values(option_list, value):
    """
    Retrieve the reverse mapping of TNS options. Used to go from option to value for a specific list of options.
    Returns a tuple of the option value and the option label.
    """
    reversed_tns_values = cache.get("reverse_tns_values", {})
    if not reversed_tns_values:
        _, reversed_tns_values = populate_tns_values()
    try:
        return reversed_tns_values[option_list][value], value
    except KeyError:
        return None


def populate_tns_values():
    """pull all the values from the TNS API and Cache for an hour"""

    # Need to spoof a web based user agent or TNS will block the request :(
    SPOOF_USER_AGENT = 'Mozilla/5.0 (X11; Linux i686; rv:110.0) Gecko/20100101 Firefox/110.0.'

    # Use sandbox URL if no url found in settings.py
    tns_base_url = get_tns_credentials().get('tns_base_url', 'https://sandbox.wis-tns.org/api')
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
    """reverse the values from the TNS API"""
    reversed_tns_values = {}
    for key, values in all_tns_values.items():
        if isinstance(values, list):
            reversed_tns_values[key] = {value: index for index, value in enumerate(values)}
        elif isinstance(values, dict):
            reversed_tns_values[key] = {v: k for k, v in values.items()}
    return reversed_tns_values


def build_file_dict(files):
    """
    Build a dictionary of files to upload to the TNS as well as a dictionary connecting the uploaded name to the new
    name returned from TNS.
    TNS requires a specific format for the file upload:
    https://www.wis-tns.org/sites/default/files/api/TNS_bulk_reports_manual.pdf
    file_Load: {files[0]: Filename, files[1]: Filename2, ...}
    new_files: {ascii_file: <<index for ascii file>>, fits_file: <<index for fits file>>, ...}
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
    # build request parameters
    tns_marker = tns_credentials['marker']
    upload_data = {'api_key': tns_credentials['api_key']}
    response = requests.post(tns_credentials['tns_base_url'] + '/file-upload', headers={'User-Agent': tns_marker},
                             data=upload_data, files=file_load)
    response.raise_for_status()
    # If successful, TNS returns a list of new filenames
    new_filenames = response.json().get('data', {})
    logger.info(f"Uploaded {', '.join(new_filenames)} to the TNS")
    if not new_filenames:
        return None
    # Return dictionary of updated TNS names for each uploaded file_type
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
    Returns a report ID if successful.
    This ID can be used to retrieve the report from the TNS.
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
    iau_name = None
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
    else:  # If neither 'classification_report', nor 'at_report' were in the feedback section
        log_message = 'No recognized feedback in the TNS response.'
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
    iau_name = None
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
    if not iau_name:
        raise BadTnsRequest(f"TNS submission failed to be processed within 10 seconds. The report_id = {report_id}")
    return iau_name
