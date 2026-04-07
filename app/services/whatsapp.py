from typing import Any, Dict, Optional
import httpx
from app.core.config import settings
from loguru import logger


class WhatsappService:
    """Service to handle communication with the WhatsApp Cloud API.

    This service manages the HTTP client and provides methods to send structured
    messages (text, templates, etc.) to WhatsApp users.

    Attributes:
        base_url (str): The Meta Graph API URL for sending messages.
        headers (Dict[str, str]): The HTTP headers required for authentication.
        client (httpx.AsyncClient): The asynchronous HTTP client for API requests.
    """

    base_url: str
    headers: Dict[str, str]
    client: httpx.AsyncClient

    def __init__(self) -> None:
        """Initializes the service, setting up the API endpoint and standard headers."""
        self.base_url = f'https://graph.facebook.com/v22.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages'
        self.headers = {'Authorization': f'Bearer {settings.WHATSAPP_TOKEN}'}
        self.client = httpx.AsyncClient(headers=self.headers)

    async def send_whatsapp_message(self, to: str, message: str) -> Dict[str, str]:
        """Sends a text message to a WhatsApp user.

        Args:
            to (str): The recipient's phone number in E.164 format.
            message (str): The body text of the message to be sent.

        Returns:
            Dict[str, str]: A dictionary containing the delivery status ('ok' or 'error').
        """
        try:
            payload: Dict[str, Any] = {
                'messaging_product': 'whatsapp',
                'to': to,
                'type': 'text',
                'text': {'body': message},
            }
            response = await self.client.post(self.base_url, json=payload)
            response.raise_for_status()
            logger.info(f'Message sent to {to}')
            return {'status': 'ok'}
        except httpx.HTTPStatusError as e:
            logger.error(f'WhatsApp API HTTP Error: {e.response.text}')
            return {'status': 'error'}
        except Exception as e:
            logger.error(f'Network error sending message to {to}: {e}')
            return {'status': 'error'}


whatsapp_service: WhatsappService = WhatsappService()
