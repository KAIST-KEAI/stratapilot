import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)
SERVICE_ROOT = os.getenv("API_BASE_URL")


class HttpAgent:
    """
    Provides a simplified interface for making outbound HTTP requests using a persistent connection.
    
    Supports both data payloads and file transmissions. Automatically injects headers and constructs
    target URLs from a base service endpoint.
    
    Attributes:
        _client (requests.Session): Persistent HTTP connection handler.
        _base (str): Base URL used for all endpoint requests.
        _default_headers (dict): HTTP headers to send with every request.
    """

    def __init__(self):
        """
        Initialize the HTTP agent with session caching and user agent emulation.
        """
        self._client = requests.Session()
        self._base = SERVICE_ROOT
        self._default_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/52.0.2743.116 Safari/537.36"
            )
        }

    def dispatch(
        self,
        endpoint: str,
        method: str,
        payload: dict = None,
        attachments: dict = None,
        mime: str = "application/json"
    ) -> dict | None:
        """
        Execute a GET or POST request against the composed URL.

        Args:
            endpoint (str): Path suffix appended to the root URL.
            method (str): HTTP method name ('get' or 'post').
            payload (dict): JSON body or form fields depending on context.
            attachments (dict): Files to be included in form-based upload.
            mime (str): Declares content type of the outgoing payload.

        Returns:
            dict | None: Server JSON response, or None on failure.
        """
        full_url = f"{self._base}{endpoint}"
        try:
            action = method.lower()

            if action == "get":
                response = self._client.get(
                    full_url,
                    json=payload if mime == "application/json" else None,
                    params=payload if mime != "application/json" else None,
                    headers=self._default_headers,
                    timeout=60
                )

            elif action == "post":
                if mime == "multipart/form-data":
                    response = self._client.post(
                        full_url,
                        files=attachments,
                        data=payload,
                        headers=self._default_headers,
                        timeout=60
                    )
                elif mime == "application/json":
                    response = self._client.post(
                        full_url,
                        json=payload,
                        headers=self._default_headers,
                        timeout=60
                    )
                else:
                    response = self._client.post(
                        full_url,
                        data=payload,
                        headers=self._default_headers,
                        timeout=60
                    )

            else:
                print("Unsupported HTTP verb specified.")
                return None

            return response.json()

        except Exception as err:
            print(f"[HTTP ERROR] {err}")
            return None
