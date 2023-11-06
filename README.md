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
        'tom_nonlocalizedevents',
    ]
    ```

    Also add your TNS credentials to your `settins.py` if they don't already exist for the TNS Broker.

3. Include the tom_nonlocalizedevent URLconf in your project `urls.py`:
   ```python
   urlpatterns = [
        ...
        path('tns/', include('tom_tns.urls', namespace='tns')),
   ]
   ```
