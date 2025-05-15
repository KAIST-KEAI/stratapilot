import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env', override=True)
API_BASE_URL = os.getenv('API_BASE_URL') 

import requests
from some_config_module import API_BASE_URL


class ToolRequestUtil:
    """
    Simplifies making HTTP requests to external APIs with session management and configurable headers.

    This utility wraps a persistent `requests.Session` to send GET or POST requests,
    including JSON payloads and multipart file uploads. It automatically prepends a base URL
    to each endpoint path and applies standard headers (e.g., User-Agent) for compatibility.

    Attributes:
        session (requests.Session): Reusable HTTP session for connection pooling.
        headers (dict): Default headers sent with every request.
        base_url (str): Root URL prepended to all API paths.
    """

    def __init__(self):
        """
        Initialize the HTTP session and default request settings.
        """
        self.session = requests.Session()
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/52.0.2743.116 Safari/537.36'
            )
        }
        self.base_url = API_BASE_URL

    def request(
        self,
        api_path: str,
        method: str,
        params: dict = None,
        files: dict = None,
        content_type: str = "application/json"
    ) -> dict | None:
        """
        Send an HTTP request to a specific API endpoint and return its JSON response.

        Constructs the full URL by joining `base_url` with `api_path`, then issues
        either a GET or POST request using the given parameters or file attachments.

        Args:
            api_path (str): Endpoint path, appended to the base URL.
            method (str): HTTP method to use ('get' or 'post').
            params (dict, optional): Request parameters or JSON body.
            files (dict, optional): Files for multipart/form-data POST requests.
            content_type (str, optional): MIME type header (e.g., 'application/json',
                'multipart/form-data'). Defaults to 'application/json'.

        Returns:
            dict: Parsed JSON response on success.
            None: If the method is unsupported or an exception occurs.
        """
        url = f"{self.base_url}{api_path}"
        try:
            method_lower = method.lower()
            if method_lower == "get":
                if content_type == "application/json":
                    response = self.session.get(
                        url,
                        json=params,
                        headers=self.headers,
                        timeout=60
                    )
                else:
                    response = self.session.get(
                        url,
                        params=params,
                        headers=self.headers,
                        timeout=60
                    )

            elif method_lower == "post":
                if content_type == "multipart/form-data":
                    response = self.session.post(
                        url,
                        files=files,
                        data=params,
                        headers=self.headers,
                        timeout=60
                    )
                elif content_type == "application/json":
                    response = self.session.post(
                        url,
                        json=params,
                        headers=self.headers,
                        timeout=60
                    )
                else:
                    response = self.session.post(
                        url,
                        data=params,
                        headers=self.headers,
                        timeout=60
                    )

            else:
                print("Error: Unsupported HTTP method")
                return None

            return response.json()

        except Exception as e:
            print(f"HTTP request error: {e}")
            return None
