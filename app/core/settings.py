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


class CorsSettings(BaseSettings):
    """
    CORS settings for the application.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_prefix="CORS_",
        extra="ignore")

    ALLOWED_ORIGINS: list[str] = Field(
        ["http://localhost:5173", "http://localhost:3000"],
        description="Allowed origins for CORS"
    )


class AgentSettings(BaseSettings):
    """
    Settings for downstream agent integration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_prefix="AGENT_",
        extra="ignore")

    SERVICE_URL: str = Field("http://localhost:8002", description="Agent service URL")
    TIMEOUT_SECONDS: int = Field(120, description="Agent service execution timeout")
    MAX_CONCURRENT: int = Field(5, description="Max concurrent agents")
    SESSION_TTL_SECONDS: int = Field(86400, description="Session TTL in seconds")


class LlmSettings(BaseSettings):
    """
    LLM and Embedding settings for the application.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_prefix="LLM_",
        extra="ignore")

    PROVIDER: str = Field("stub", description="Active LLM provider (stub, ollama, openai, anthropic, gemini)")
    OLLAMA_BASE_URL: str = Field("http://localhost:11434", description="Ollama base URL")
    OLLAMA_MODEL: str = Field("llama3.2", description="Ollama model")
    OPENAI_API_KEY: str = Field("", description="OpenAI API key")
    OPENAI_MODEL: str = Field("gpt-4o", description="OpenAI model")
    OPENAI_BASE_URL: str = Field("", description="OpenAI base URL override")
    ANTHROPIC_API_KEY: str = Field("", description="Anthropic API key")
    ANTHROPIC_MODEL: str = Field("claude-3-5-sonnet-20241022", description="Anthropic model")
    GEMINI_API_KEY: str = Field("", description="Gemini API key")
    GEMINI_MODEL: str = Field("gemini-2.0-flash", description="Gemini model")
    EXTERNAL_LLM_URL: str = Field("", description="External LLM service URL")
    EXTERNAL_LLM_API_KEY: str = Field("", description="External LLM service API key")
    EMBEDDING_PROVIDER: str = Field("stub", description="Active embedding provider")
    EMBEDDING_MODEL: str = Field("text-embedding-3-small", description="Embedding model")


class UploadSettings(BaseSettings):
    """
    File upload settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        env_prefix="UPLOAD_",
        extra="ignore")

    DIR: str = Field("./data/uploads", description="File upload directory")
    MAX_SIZE_MB: int = Field(50, description="Maximum file upload size in MB")


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

    cors_settings: CorsSettings = CorsSettings(
        default_factory=CorsSettings,
        description="CORS settings for the application"
    )

    agent_settings: AgentSettings = AgentSettings(
        default_factory=AgentSettings,
        description="Agent settings for the application"
    )

    llm_settings: LlmSettings = LlmSettings(
        default_factory=LlmSettings,
        description="LLM settings for the application"
    )

    upload_settings: UploadSettings = UploadSettings(
        default_factory=UploadSettings,
        description="Upload settings for the application"
    )


app_settings = AppSettings()