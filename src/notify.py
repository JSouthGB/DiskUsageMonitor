import logging
from typing import List
from urllib.parse import urlunparse, urlparse, urlencode

import requests

from src.config_loader import ConfigLoader


def send_notification(data: List[str]) -> None:
    """
    Gotify notification

    Arguments:
    - data (list): List of strings to send.
    - url (str): Gotify server URL.
    - token (str): Gotify application token.
    """

    config_loader = ConfigLoader()
    gotify = config_loader.get_gotify()

    gotify_url: str = gotify[0]
    gotify_token: str = gotify[1]

    if gotify_url is None or gotify_token is None:
        return
    else:
        api_endpoint = 'message'  # Gotify API endpoint
        params = {'token': gotify_token}
        url = urlunparse(
            urlparse(gotify_url)._replace(
                path=api_endpoint, query=urlencode(params))
        )

        message = '\n\n'.join(data)  # for readability
        params = {
            'title': 'Disk Usage Monitor Alert',
            'message': message,
            'priority': 5,
        }

        response = requests.post(url, data=params)
        try:
            response.raise_for_status()
        except requests.HTTPError as http_err:
            logging.exception(f'HTTP error occurred: {http_err}', stack_info=True)
        except Exception as err:
            logging.exception(f'HTTP exception occurred: {err}', stack_info=True)
