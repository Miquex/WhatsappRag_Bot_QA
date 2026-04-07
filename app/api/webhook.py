from typing import Dict, Optional
from fastapi import APIRouter, Query, HTTPException, Response, Body
from loguru import logger
from app.core.config import settings
from app.agent.rag import rag_agent
from app.services.whatsapp import whatsapp_service
from app.api.schemas import WhatsAppWebhookPayload
from app.api.deduplication import deduplicator

router: APIRouter = APIRouter()


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
async def receive_message(
    payload: WhatsAppWebhookPayload = Body(...),
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
                    logger.info(f'User {user_phone} sent message: {user_message}')
                    ai_response = await rag_agent.query_rag(
                        query=user_message, user_phone=user_phone
                    )
                    await whatsapp_service.send_whatsapp_message(
                        to=user_phone, message=ai_response
                    )
                    logger.info(f'Response sent to {user_phone}: {ai_response}')
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
