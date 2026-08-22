from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .distribution import APP_DISTRIBUTION, APP_VERSION

class LoggingSettings(BaseSettings):
    """
    Logging settings for the application.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_prefix="LOGGING_",
        extra="ignore")

    LEVEL: str = Field("INFO", description="Logging level (e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    
    LEVELS: str | None = Field(None, description="Comma-separated list of logging levels for different modules (e.g., 'module1=DEBUG,module2=INFO')")
    
    JSON_FORMAT_ENABLED: bool = Field(False, description="Enable JSON logging format")
    
    @property
    def logger_levels_dict(self) -> dict[str, str]:
        """
        Returns a dictionary of logger levels for different modules.
        """
        if not self.LEVELS:
            return {}
        return dict(item.split("=") for item in self.LEVELS.split(",") if "=" in item)
    

class DatabaseSettings(BaseSettings):
    """
    Database settings for the application.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_prefix="DB_",
        extra="ignore")

    URL: str = Field("sqlite:///./app.db", description="Database connection URL")
    ECHO: bool = Field(False, description="Enable SQLAlchemy echo for debugging")
    
    POOL_SIZE: int = Field(5, description="Database connection pool size")
    
    MAX_OVERFLOW: int = Field(10, description="Maximum number of connections to allow in connection pool overflow")
    
    POOL_PRE_PING: bool = Field(True, description="Enable connection pool pre-ping to check if connections are alive")
    
    AUTO_COMMIT: bool = Field(True, description="Enable automatic commit of transactions")
    AUTO_FLUSH: bool = Field(True, description="Enable automatic flush of transactions")
    EXPIRE_ON_COMMIT: bool = Field(False, description="Expire objects on commit")
    
    
class TelemetrySettings(BaseSettings):
    """
    Telemetry settings for the application.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_prefix="TELEMETRY_",
        extra="ignore")

    ENABLED: bool = Field(False, description="Enable telemetry")
    
    SERVICE_NAME: str = Field(APP_DISTRIBUTION.name, description="Telemetry service name")
    
    SERVICE_VERSION: str = Field(APP_VERSION, description="Telemetry service version")
    
    OTLP_ENDPOINT: str | None = Field(None, description="OTLP endpoint for telemetry data")
    
    
class EndpointSettings(BaseSettings):
    """
    Endpoint settings for the application.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_prefix="ENDPOINT_",
        extra="ignore")

    HOST: str = Field("localhost", description="Endpoint host") 
    PORT: int = Field(8000, description="Endpoint port")    
    

class AppSettings(BaseSettings):
    """
    Application settings for the FastAPI application.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_prefix="APP_",
        extra="ignore")

    NAME: str = Field(APP_DISTRIBUTION.name, description="Application name")
    
    VERSION: str = Field(APP_VERSION, description="Application version")
    
    DESCRIPTION: str = Field(APP_DISTRIBUTION.description, description="Application description")
    
    logging_settings: LoggingSettings = LoggingSettings(
        default_factory=LoggingSettings,
        description="Logging settings for the application"
    )
    
    database_settings: DatabaseSettings = DatabaseSettings(
        default_factory=DatabaseSettings,
        description="Database settings for the application"
    )
    
    telemetry_settings: TelemetrySettings = TelemetrySettings(
        default_factory=TelemetrySettings,
        description="Telemetry settings for the application"
    )
    
    endpoint_settings: EndpointSettings = EndpointSettings(
        default_factory=EndpointSettings,
        description="Endpoint settings for the application"
    )


app_settings = AppSettings()