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

3. Add TNS or Hermes account credentials to your `settings.py` to enable different methods of sharing.
   
   If you don't have access to a TNS Bot for your TOM, you can make one from the [TNS website](https://www.wis-tns.org/bots).

   NOTE: If you are testing on the sandbox, the sandbox is only synced every Sunday, so new bots created using the above link won't show up until after the next update.

   ### Submit to TNS directly (no hermes)
   Add your TNS credentials to your `settings.py` if they don't already exist for the TNS Broker.
   

   ```python
    BROKERS = {
        ...
        'TNS': {
            'bot_id': os.getenv('TNS_BOT_ID', ''),  # This is the BOT ID you plan to use to submit to TNS
            'bot_name': os.getenv('TNS_BOT_NAME', ''),  # This is the BOT name associated with the above ID
            'api_key': os.getenv('TNS_API_KEY', ''),  # This is the API key for the associated BOT         
            'tns_base_url': 'https://sandbox.wis-tns.org/api',  # This is the sandbox URL. Use https://www.wis-tns.org/api for live submission.
            'group_names': ['bot_group', 'PI_group'],  # Optional List. Include if you wish to use any affiliated Group Names when reporting.
            'filter_mapping': {
                'o': 'Other',
                'c': 'Clear',
                ...
            },  # Optional mapping from your reduced datum filter values to TNS filter options.
            'default_authors': 'Foo Bar <foo@bar.com>, Rando Calrissian, et al.'  # Optional default authors string to populate the author fields for tns submission. If not specified, defaults to saying "<logged in user> using <tom name>".
        },
    }
    ```

    ### Submit to TNS through Hermes
    If you want to submit to the TNS through [HERMES](https://hermes.lco.global), then you must first configure your [hermes account profile](https://hermes.lco.global/profile) to have your TNS credentials associated with your account. Then you must add your hermes credentials you `settings.py` in the `DATA_SHARING` section. This method of TNS submission will take precedence if `ENABLE_TNS` is set to True in your hermes `DATA_SHARING` details.

    NOTE: If you don't set TNS credentials in your hermes account profile, TNS submission will still work but use the default Hermes_Bot account for TNS submission.


   ```python
    DATA_SHARING = {
        ...
        'hermes': {
            'DISPLAY_NAME': 'hermes',
            'BASE_URL': 'https://hermes-dev.lco.global/',
            'HERMES_API_KEY': 'YourHermesAPITokenHere',
            'DEFAULT_AUTHORS': 'Foo Bar <foo@bar.com>, Rando Calrissian, et al.',  # Optional default authors string to populate the author fields for tns submission. If not specified, defaults to saying "<logged in user> using <tom name>".
            'USER_TOPICS': ['hermes.discovery', 'hermes.classification', ...]  # This is a list of hermes topics you will be allowed to share on. hermes.discovery and hermes.classification are automatically used for TNS submissions of those types.
            'TNS_GROUP_NAMES': ['bot_group', 'PI_group'],  # Optional List. Include if you wish to use any affiliated Group Names when reporting to TNS.
            'FILTER_MAPPING': {
                'o': 'Other',
                'c': 'Clear',
                ...
            },  # Optional mapping from your reduced datum filter values to TNS filter options.
            'ENABLE_TNS': False  # Set to True to enable TNS submissions through Hermes
        },
    }
    ```


4. Include the tom_tns URLconf in your project `urls.py` if you are using a tomtoolkit version <= 2.18:
   ```python
   urlpatterns = [
        ...
        path('tns/', include('tom_tns.urls', namespace='tns')),
   ]
   ```

Once configured, a `TNS` button should appear below the Target Name on the default Target Detail page.

If you have customized the Target Details page of your TOM, or if you would like to add entrypoints to the tom_tns form from other TOM pages, including those referencing a specific data product or reduced datum's values, then you can do that by including the code below somewhere in your templates:

```html
 <a href="{% url tns:report-tns pk=target.id datum_pk=datum.pk %}" title=TNS class="btn  btn-info">Submit to TNS</a>
```

The datum_pk is optional. If it is not specified, the latest photometry reduced datum will be used to pre-fill the discovery report form, and the latest spectroscopy reduced datum will be used to pre-fill the classification report form. If you specifiy a datum pk, then that datum and associated data product will be used to pre-fill the proper forms.

For example, if you want to add a link next to each data product to submit it to TNS, then you could just use the dataproducts first datum id for the `datum_pk`.


NOTE: Users who are using `tomtoolkit<2.15.12` will have to add the TNS button manually.
