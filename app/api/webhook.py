import hashlib
import hmac
from typing import Dict, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request, Response, Body
from loguru import logger
from cachetools import TTLCache
from app.core.config import settings
from app.agent.rag import rag_agent
from app.services.whatsapp import whatsapp_service
from app.api.schemas import WhatsAppWebhookPayload
from app.api.deduplication import deduplicator
from slowapi import Limiter
from slowapi.util import get_remote_address

router: APIRouter = APIRouter()

limiter = Limiter(key_func=get_remote_address)

MAX_MESSAGES_PER_USER: int = 10
phone_rate_limiter: TTLCache = TTLCache(maxsize=100, ttl=60)


def is_rate_limited(phone_number: str) -> bool:
    """Checks if a phone number has exceeded the message rate limit.

    Args:
        phone_number (str): The user's phone number.

    Returns:
        bool: True if the user has exceeded the limit, False otherwise.
    """
    count = phone_rate_limiter.get(phone_number, 0)
    if count >= MAX_MESSAGES_PER_USER:
        return True
    phone_rate_limiter[phone_number] = count + 1
    return False

async def verify_meta_signature(request:Request)-> bytes:
    """Dependency that validates Meta's HMAC-SH256 signature"""
    signature = request.headers.get("X-Hub-Signature-256","")
    body =await request.body()
    expected = "sha256=" + hmac.new(
        settings.META_APP_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        logger.error("Invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")
    return body

@router.get('/webhook')
def webhook(
    hub_mode: Optional[str] = Query(None, alias='hub.mode'),
    hub_verify_token: Optional[str] = Query(None, alias='hub.verify_token'),
    hub_challenge: Optional[str] = Query(None, alias='hub.challenge'),
) -> Response:
    """Verifies the WhatsApp webhook subscription.

    This endpoint is called by Meta to verify that the webhook is valid.
    It expects a specific hub.mode ('subscribe') and a matching verification token.

    Args:
        hub_mode (Optional[str]): The subscription mode sent by Meta.
        hub_verify_token (Optional[str]): The verification token sent by Meta.
        hub_challenge (Optional[str]): The challenge string to be returned on success.

    Returns:
        Response: A plain text response containing the hub_challenge if verified.

    Raises:
        HTTPException: If verification fails with a 403 status code.
    """
    if hub_mode == 'subscribe' and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info('Webhook verified successfully')
        return Response(content=hub_challenge, media_type='text/plain')
    else:
        logger.warning('Webhook verification failed')
        raise HTTPException(status_code=403, detail='Invalid verification token')


@router.post('/webhook')
@limiter.limit("30/minute")
async def receive_message(
    request: Request,
    payload: WhatsAppWebhookPayload = Body(...),
    _signature: bytes = Depends(verify_meta_signature),
) -> Dict[str, str]:
    """Processes incoming WhatsApp messages received via the webhook.

    Extracts the user's message, detects duplicates, retrieves relevant context
    using RAG, and sends an automated response back via WhatsApp.

    Args:
        payload (WhatsAppWebhookPayload): The structured webhook payload from Meta.

    Returns:
        Dict[str, str]: A status dictionary indicating the result of the processing.
    """
    try:
        if payload.entry and payload.entry[0].changes:
            change_value = payload.entry[0].changes[0].value
            if change_value.messages:
                message = change_value.messages[0]
                if message.type == 'text' and message.text:
                    message_id = message.id
                    if deduplicator.is_duplicate(message_id):
                        return {'status': 'ok'}
                    user_message = message.text.body
                    user_phone = message.from_number
                    masked_phone = user_phone[:5] + '****' + user_phone[-4:] if len(user_phone) > 8 else '****'
                    if is_rate_limited(user_phone):
                        logger.warning(f'Rate limited user {masked_phone}')
                        await whatsapp_service.send_whatsapp_message(
                            to=user_phone,
                            message='You are sending too many messages. Please wait a moment before trying again.'
                        )
                        return {'status': 'ok'}
                    logger.info(f'User {masked_phone} sent message ({len(user_message)} chars)')
                    ai_response = await rag_agent.query_rag(
                        query=user_message, user_phone=user_phone
                    )
                    await whatsapp_service.send_whatsapp_message(
                        to=user_phone, message=ai_response
                    )
                    logger.info(f'Response sent to {masked_phone} ({len(ai_response)} chars)')
                
                else:
                    logger.info(f'Ignored non-text message of type: {message.type}')
            
            elif change_value.statuses:
                status = change_value.statuses[0]
                logger.debug(f"Message {status.id} changed to '{status.status}'")
            else:
                logger.debug('Received unhandled webhook event')
        return {'status': 'ok'}
    except Exception as e:
        logger.error(f'Critical error processing message: {e}')
        return {'status': 'ok'}
