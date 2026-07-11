# Transient Name Server (TNS) Report and Classification plugin for TOM Toolkit
TOMtoolkit module for reporting transients to the TNS 

## Installation

1. Install the package into your TOM environment:
    ```bash
    pip install tom-tns
   ```

2. In your project `settings.py`, add `tom_tns` to your `INSTALLED_APPS` setting:

```python
    INSTALLED_APPS = TOMTOOKIT_INSTALLED_APPS + [
    'custom_code',
    ...
    'tom_TNS',

    ]
```

3. Add TNS account credentials to your `settings.py` to enable TNS submission.
   
   If you don't have access to a TNS Bot for your TOM, you can make one from the [TNS website](https://www.wis-tns.org/bots).

   NOTE: If you are testing on the sandbox, the sandbox is only synced every Sunday, so new bots created using the above link won't show up until after the next update.

   ### Submit to TNS directly
   Add your TNS credentials to your `settings.py` if they don't already exist for the TNS Data Service.
   

   ```python
    DATA_SERVICES = {
        ...
        'TNS': {
            'bot_id': os.getenv('TNS_BOT_ID', ''),  # This is the BOT ID you plan to use to submit to TNS
            'bot_name': os.getenv('TNS_BOT_NAME', ''),  # This is the BOT name associated with the above ID
            'api_key': os.getenv('TNS_API_KEY', ''),  # This is the API key for the associated BOT         
            'base_url': 'https://sandbox.wis-tns.org/',  # This is the sandbox URL. Use https://www.wis-tns.org/ for live submission.
            'group_names': ['bot_group', 'PI_group'],  # Mandatory. You must choose an affiliated Group Name when reporting.
            'internal_name_format': {
               'prefix': 'MyProgramName',
               'year_format': 'YY',
               'postfix': ''
            },  # Optional formatting for internal name used by default if no specific name is given. (ex. MyProgramName24xxx for TNS object 2024xxx)
            'filter_mapping': {
                'o': 'Other',
                'c': 'Clear',
                ...
            },  # Optional mapping from your photometry filter values to TNS filter options.
            'instrument_mapping': {
                'fa20': 'LCO1m - Sinistro',
                ...
            },  # Optional mapping from your reduced datum instrument name to TNS instrument names
            'default_authors': 'Foo Bar <foo@bar.com>, Rando Calrissian, et al.',  # Optional default authors string to populate the author fields for tns submission. If not specified, defaults to saying "<logged in user> using <tom name>".
            'report_max_attempts': 10,  # Optional max number of attempts to make to retrieve a report after submission (Defaults o 10)
            'report_delay_seconds': None, # Optional number of seconds to wait per attempt to retrieve a report (Scales up linearly by default)
        },
    }
    ```

Once configured, a `TNS` button should appear below the Target Name on the default Target Detail page.
