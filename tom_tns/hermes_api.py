from django.conf import settings
from django.contrib import messages
from urllib.parse import urljoin

import requests
import json
import logging
import os

logger = logging.getLogger(__name__)


def get_object_from_response(response_json):
    # If the submission is successful, then pull out the tns_object name from the references and return it
    references = response_json.get('data', {}).get('references', [])
    for reference in references:
        if reference.get('source') == 'tns_object':
            return reference.get('citation')
    return None


def submit_to_hermes(hermes_message, files, request):
    hermes_submit_url = urljoin(settings.DATA_SHARING.get('hermes', {}).get('BASE_URL', ''), 'api/v0/submit_message/')
    headers = {'Authorization': f"Token {settings.DATA_SHARING.get('hermes', {}).get('HERMES_API_KEY', '')}"}
    response_json = {}
    try:
        if not files:
            # Can submit simple json payload to hermes, and this assumed to be a new discovery
            response = requests.post(url=hermes_submit_url, json=hermes_message, headers=headers)
            response_json = response.json()
            response.raise_for_status()
            logger.info(f"Sent TNS discovery message through Hermes with uuid {response_json.get('uuid')}")
            return get_object_from_response(response_json)
        else:
            # There are files, so this must be a classification submission
            data = {'data': json.dumps(hermes_message)}
            files_to_submit = []
            for file in files:
                content_type = 'text/plain'
                if file.name.endswith('fits') or file.name.endswith('fits.fz'):
                    content_type = 'application/fits'
                files_to_submit.append(('files', (os.path.basename(file.name), file.open('rb'), content_type)))
            response = requests.post(url=hermes_submit_url, data=data, files=files_to_submit, headers=headers)
            response_json = response.json()
            response.raise_for_status()
            logger.info(f"Sent TNS classification message through Hermes with uuid {response_json.get('uuid')}")
            return get_object_from_response(response_json)
    except Exception as e:
        error_msg = 'Failed to Submit message to Hermes/TNS'
        if response_json:
            error_msg += f': {response_json}'
        else:
            error_msg += f': {repr(e)}'
        logger.error(error_msg)
        messages.error(request, error_msg)
    return None
