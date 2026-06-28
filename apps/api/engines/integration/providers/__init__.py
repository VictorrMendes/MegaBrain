# Import all providers here so they self-register via @IntegrationRegistry.register
from .docker import DockerProvider
from .weather import WeatherProvider
from .mock_provider import MockProvider
from .google_workspace import GoogleWorkspaceProvider

__all__ = [
    "DockerProvider",
    "WeatherProvider", 
    "MockProvider",
    "GoogleWorkspaceProvider"
]
