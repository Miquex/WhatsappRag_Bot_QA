from typing import Optional
import pathlib
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and configuration management.

    This class uses Pydantic Settings to load configuration from environment 
    variables (via a .env file). It manages API keys, project metadata, 
    and filesystem paths for data persistence.

    Attributes:
        PROJECT_NAME (str): The name of the WhatsApp agent project.
        VERSION (str): The current semantic version of the application.
        DEBUG (bool): Boolean flag to enable/disable debug-level logging.
        WHATSAPP_TOKEN (Optional[str]): The access token for the WhatsApp Cloud API.
        WHATSAPP_PHONE_NUMBER_ID (Optional[str]): The unique ID for the 
            WhatsApp sender phone.
        WHATSAPP_VERIFY_TOKEN (Optional[str]): The token used for webhook 
            verification. Defaults to 'WHATSAPP_VERIFY_TOKEN'.
        OPENAI_API_KEY (Optional[str]): The API key for OpenAI services.
        GEMINI_API_KEY (Optional[str]): The API key for Google Gemini services.
        RAG_MD_PATH (str): The absolute path to the RAG knowledge source markdown file.
        CHROMA_DB_DIR (str): The directory where ChromaDB files are stored.
    """

    PROJECT_NAME: str = 'Whatsapp RAG Agent'
    VERSION: str = '0.1.0'
    DEBUG: bool = True
    WHATSAPP_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = 'WHATSAPP_VERIFY_TOKEN'
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    RAG_MD_PATH: str = str(
        pathlib.Path(__file__).resolve().parent.parent / 'data/knowledge/info.md'

    )
    CHROMA_DB_DIR: str = str(
        pathlib.Path(__file__).resolve().parent.parent / 'data/chromadb'
    )

    model_config: SettingsConfigDict = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', extra='ignore'
    )


settings: Settings = Settings()
