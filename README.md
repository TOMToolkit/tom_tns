# Transient Name Server (TNS) Report and Classification plugin for TOM Toolkit
TOMtoolkit module for reporting transients to the TNS 

## Installation

1. Install the package into your TOM environment:
    ```bash
    pip install tom-tns
   ```

2. In your project `settings.py`, add `tom_tns` to your `INSTALLED_APPS` setting:

    ```python
    INSTALLED_APPS = [
        ...
        'tom_tns',
    ]
    ```

3. Add your TNS credentials to your `settings.py` if they don't already exist for the TNS Broker.
   
   If you don't have access to a TNS Bot for your TOM, you can make one from the [TNS website](https://www.wis-tns.org/bots).
   
   NOTE: If you are testing on the sandbox, the sandbox is only synced every Sunday, so new bots created using the above link 
won't show up until after the next update.

   ```python
    BROKERS = {
        ...
        'TNS': {
            'bot_id': os.getenv('TNS_BOT_ID', ''),  # This is the BOT ID you plan to use to submit to TNS
            'bot_name': os.getenv('TNS_BOT_NAME', ''),  # This is the BOT name associated with the above ID
            'api_key': os.getenv('TNS_API_KEY', ''),  # This is the API key for the associated BOT         
            'tns_base_url': 'https://sandbox.wis-tns.org/api',  # This is the sandbox URL. Use https://www.wis-tns.org/api for live submission.
            'group_name': os.getenv('TNS_GROUP_NAME', ''),  # Optional. Include if you wish to use an affiliated Group Name.
        },
    }
    ```

5. Include the tom_tns URLconf in your project `urls.py`:
   ```python
   urlpatterns = [
        ...
        path('tns/', include('tom_tns.urls', namespace='tns')),
   ]
   ```

Once configured, a `TNS` button should appear below the Target Name.

NOTE: Users who are using `tomtoolkit<2.15.12` will have to add the TNS button manually.
