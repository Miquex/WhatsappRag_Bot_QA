import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Try importing the router; adjust the import path if your app structure differs.
from app.api.webhook import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# --- Fixtures ---

@pytest.fixture
def mock_settings():
    with patch("app.api.webhook.settings") as mock:
        mock.WHATSAPP_VERIFY_TOKEN = "valid_token"
        yield mock

@pytest.fixture
def mock_deduplicator():
    with patch("app.api.webhook.deduplicator.is_duplicate") as mock:
        mock.return_value = False
        yield mock

@pytest.fixture
def mock_rag_agent():
    mock = AsyncMock()
    mock.query_rag.return_value = "Mocked AI Response"
    with patch("app.api.webhook.rag_agent", new=mock):
        yield mock

@pytest.fixture
def mock_whatsapp_service():
    mock = AsyncMock()
    with patch("app.api.webhook.whatsapp_service", new=mock):
        yield mock

def get_sample_payload(msg_id="wa_msg_1", text="Hello bot", phone="1112223333"):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "12345",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": phone,
                                    "id": msg_id,
                                    "type": "text",
                                    "text": {"body": text}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


# --- Tests for GET /webhook (Verification) ---

def test_webhook_verify_success(mock_settings):
    # Arrange
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "valid_token",
        "hub.challenge": "challenge_123"
    }
    
    # Act
    response = client.get("/webhook", params=params)
    
    # Assert
    assert response.status_code == 200
    assert response.text == "challenge_123"


def test_webhook_verify_failure_wrong_token(mock_settings):
    # Arrange
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong_token",
        "hub.challenge": "challenge_123"
    }
    
    # Act
    response = client.get("/webhook", params=params)
    
    # Assert
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid verification token"}


def test_webhook_verify_failure_wrong_mode(mock_settings):
    # Arrange
    params = {
        "hub.mode": "unsubscribe",
        "hub.verify_token": "valid_token",
        "hub.challenge": "challenge_123"
    }
    
    # Act
    response = client.get("/webhook", params=params)
    
    # Assert
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid verification token"}


# --- Tests for POST /webhook (Message Processing) ---

def test_webhook_receive_text_message(
    mock_deduplicator, 
    mock_rag_agent, 
    mock_whatsapp_service
):
    # Arrange
    payload = get_sample_payload(msg_id="msg_text_01", text="Hi there", phone="9988776655")
    
    # Act
    response = client.post("/webhook", json=payload)
    
    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
    mock_deduplicator.assert_called_once_with("msg_text_01")
    mock_rag_agent.query_rag.assert_awaited_once_with(
        query="Hi there", user_phone="9988776655"
    )
    mock_whatsapp_service.send_whatsapp_message.assert_awaited_once_with(
        to="9988776655", message="Mocked AI Response"
    )


def test_webhook_receive_duplicate_message(
    mock_deduplicator, 
    mock_rag_agent, 
    mock_whatsapp_service
):
    # Arrange
    mock_deduplicator.return_value = True
    payload = get_sample_payload(msg_id="duplicate_msg")
    
    # Act
    response = client.post("/webhook", json=payload)
    
    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
    mock_deduplicator.assert_called_once_with("duplicate_msg")
    # Agents shouldn't be queried on duplicate message
    mock_rag_agent.query_rag.assert_not_called()
    mock_whatsapp_service.send_whatsapp_message.assert_not_called()


def test_webhook_receive_non_text_message(
    mock_deduplicator, 
    mock_rag_agent, 
    mock_whatsapp_service
):
    # Arrange
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "111",
                                    "id": "wa_msg_img",
                                    "type": "image",
                                    # no text payload
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    # Act
    response = client.post("/webhook", json=payload)
    
    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
    # Deduplicator shouldn't be checked for non-text messages based on current code 
    # (checking message.type happens before checking duplicates)
    mock_deduplicator.assert_not_called()
    mock_rag_agent.query_rag.assert_not_called()


def test_webhook_receive_status_update():
    # Arrange
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [
                                {
                                    "id": "wa_msg_st",
                                    "status": "delivered"
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    # Act
    response = client.post("/webhook", json=payload)
    
    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.api.webhook.logger")
def test_webhook_exception_handling(mock_logger):
    # Arrange
    # Force an exception by sending an invalid payload form that triggers KeyError or explicitly patching component to throw Exception
    with patch("app.api.webhook.deduplicator.is_duplicate", side_effect=Exception("Database error!")):
        payload = get_sample_payload()
        
        # Act
        response = client.post("/webhook", json=payload)
        
        # Assert
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_logger.error.assert_called_once()
        assert "Critical error processing message" in mock_logger.error.call_args[0][0]
