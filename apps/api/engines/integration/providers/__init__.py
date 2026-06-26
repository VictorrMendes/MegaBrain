# Import all providers here so they self-register via @IntegrationRegistry.register
from engines.integration.providers.docker import DockerProvider
from engines.integration.providers.weather import WeatherProvider

__all__ = ["DockerProvider", "WeatherProvider"]
