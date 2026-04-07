import pytest
from pydantic import ValidationError
from app.api.schemas import (
    TextPayload,
    MessageItem,
    StatusItem,
    ValueItem,
    ChangeItem,
    EntryItem,
    WhatsAppWebhookPayload,
)


def test_text_payload_creation():
    # Arrange
    data = {"body": "Hello bot"}
    # Act
    payload = TextPayload(**data)
    # Assert
    assert payload.body == "Hello bot"


def test_message_item_creation_with_alias():
    # Arrange
    data = {"from": "1234567890", "id": "msg_001", "type": "text", "text": {"body": "Hi!"}}
    # Act
    message = MessageItem(**data)
    # Assert
    assert message.from_number == "1234567890"  # alias should populate this
    assert message.id == "msg_001"
    assert message.type == "text"
    assert message.text is not None
    assert message.text.body == "Hi!"


def test_message_item_missing_required_from():
    # Arrange
    # Missing 'from'
    data = {"id": "msg_001", "type": "text"}
    
    # Act & Assert
    with pytest.raises(ValidationError) as exc:
        MessageItem(**data)
    
    assert "from" in str(exc.value)


def test_status_item_creation():
    # Arrange
    data = {"id": "msg_001", "status": "delivered"}
    # Act
    status_item = StatusItem(**data)
    # Assert
    assert status_item.id == "msg_001"
    assert status_item.status == "delivered"


def test_value_item_optional_lists():
    # Arrange
    data_only_product = {"messaging_product": "whatsapp"}
    
    # Act
    value = ValueItem(**data_only_product)
    
    # Assert
    assert value.messaging_product == "whatsapp"
    assert value.messages is None
    assert value.statuses is None


def test_full_webhook_payload_parsing_text_message():
    # Arrange
    payload_dict = {
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
                                    "from": "1112223333",
                                    "id": "wa_msg_1",
                                    "type": "text",
                                    "text": {"body": "Hello bot"}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    # Act
    payload_obj = WhatsAppWebhookPayload(**payload_dict)
    
    # Assert
    assert payload_obj.object == "whatsapp_business_account"
    assert len(payload_obj.entry) == 1
    
    entry = payload_obj.entry[0]
    assert entry.id == "12345"
    assert len(entry.changes) == 1
    
    change = entry.changes[0]
    assert change.field == "messages"
    assert change.value.messaging_product == "whatsapp"
    
    assert change.value.messages is not None
    assert len(change.value.messages) == 1
    
    message = change.value.messages[0]
    assert message.from_number == "1112223333"
    assert message.id == "wa_msg_1"
    assert message.type == "text"
    assert message.text is not None
    assert message.text.body == "Hello bot"


def test_full_webhook_payload_parsing_status_update():
    # Arrange
    payload_dict = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "12345",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [
                                {
                                    "id": "wa_msg_1",
                                    "status": "read"
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    
    # Act
    payload_obj = WhatsAppWebhookPayload(**payload_dict)
    
    # Assert
    assert payload_obj.object == "whatsapp_business_account"
    entry = payload_obj.entry[0]
    change = entry.changes[0]
    
    assert change.value.statuses is not None
    assert len(change.value.statuses) == 1
    
    status = change.value.statuses[0]
    assert status.id == "wa_msg_1"
    assert status.status == "read"


@pytest.mark.parametrize("invalid_payload", [
    {"entry": []}, # Missing 'object'
    {"object": "whatsapp_business_account"}, # Missing 'entry'
    {
        "object": "whatsapp_business_account",
        "entry": [{"changes": []}] # Missing 'id' inside entry
    }
])
def test_webhook_payload_validation_errors(invalid_payload):
    # Act & Assert
    with pytest.raises(ValidationError):
        WhatsAppWebhookPayload(**invalid_payload)
