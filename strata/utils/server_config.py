import os
from typing import Optional

class ConfigManager:
    """
    Singleton class designed to manage application-wide configuration settings.
    Manages HTTP/HTTPS proxy configurations and environment variable interactions.

    Maintains a single instance throughout the application lifecycle.
    Handles proxy setup, teardown, and environment variable management.

    Attributes:
        _instance: Private static reference to the singleton instance.
        http_proxy: HTTP proxy URL configuration.
        https_proxy: HTTPS proxy URL configuration.
    """
    _instance: Optional['ConfigManager'] = None

    def __new__(cls) -> 'ConfigManager':
        """
        Creates and returns the singleton instance, initializing default proxy settings.
        
        Returns:
            The singleton instance of ConfigManager.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Default proxy configuration - override with set_proxies()
            cls._instance.http_proxy = "http://127.0.0.1:10809"
            cls._instance.https_proxy = "http://127.0.0.1:10809"
        return cls._instance

    def set_proxies(self, http_proxy: Optional[str], https_proxy: Optional[str]) -> None:
        """
        Configures HTTP and HTTPS proxy settings.
        
        Args:
            http_proxy: HTTP proxy URL (e.g., "http://proxy.example.com:8080").
            https_proxy: HTTPS proxy URL (e.g., "http://proxy.example.com:8080").
        """
        self.http_proxy = http_proxy
        self.https_proxy = https_proxy

    def apply_proxies(self) -> None:
        """
        Applies configured proxy settings to environment variables.
        Updates 'http_proxy' and 'https_proxy' environment variables based on current configuration.
        Does not modify environment variables if proxy is set to None.
        """
        if self.http_proxy is not None:
            os.environ["http_proxy"] = self.http_proxy
        if self.https_proxy is not None:
            os.environ["https_proxy"] = self.https_proxy

    def clear_proxies(self) -> None:
        """
        Removes proxy configurations from environment variables.
        Safely removes 'http_proxy' and 'https_proxy' from environment variables if they exist.
        """
        os.environ.pop("http_proxy", None)
        os.environ.pop("https_proxy", None)