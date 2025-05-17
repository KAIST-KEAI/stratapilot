import os
from typing import Optional


class EnvTuner:
    """
    Centralized utility for managing runtime networking settings.

    Implements a singleton-style instance that modifies environment-level
    proxy variables, offering setter, enabler, and cleaner interfaces.
    
    Attributes:
        _singleton: Internal instance holder.
        _http: HTTP proxy URL.
        _https: HTTPS proxy URL.
    """
    _singleton: Optional['EnvTuner'] = None

    def __new__(cls) -> 'EnvTuner':
        """
        Ensures a single shared instance across the application.
        
        Returns:
            EnvTuner: The globally shared instance.
        """
        if cls._singleton is None:
            cls._singleton = super().__new__(cls)
            cls._singleton._http = "http://127.0.0.1:10809"
            cls._singleton._https = "http://127.0.0.1:10809"
        return cls._singleton

    def configure(self, http: Optional[str], https: Optional[str]) -> None:
        """
        Updates internal proxy routing values.

        Args:
            http (Optional[str]): New HTTP route string.
            https (Optional[str]): New HTTPS route string.
        """
        self._http = http
        self._https = https

    def activate(self) -> None:
        """
        Pushes proxy routing to the process environment.
        """
        if self._http:
            os.environ["http_proxy"] = self._http
        if self._https:
            os.environ["https_proxy"] = self._https

    def reset(self) -> None:
        """
        Clears any routing configurations from the environment.
        """
        os.environ.pop("http_proxy", None)
        os.environ.pop("https_proxy", None)
