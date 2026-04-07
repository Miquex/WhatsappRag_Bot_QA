from pydantic import BaseModel, Field
from typing import List, Optional


class TextPayload(BaseModel):
    """Represents the text content within a message.

    Attributes:
        body (str): The actual text content of the message.
    """

    body: str


class MessageItem(BaseModel):
    """Represents a single message received via the webhook.

    Attributes:
        from_number (str): The sender's phone number, aliased from 'from'.
        id (str): The unique ID of the message.
        type (str): The type of message (e.g., 'text').
        text (Optional[TextPayload]): The text payload, if available.
    """

    from_number: str = Field(alias='from')
    id: str
    type: str
    text: Optional[TextPayload] = None


class StatusItem(BaseModel):
    """Represents a message status update.

    Attributes:
        id (str): The ID of the message whose status changed.
        status (str): The new status (e.g., 'sent', 'delivered', 'read').
    """

    id: str
    status: str


class ValueItem(BaseModel):
    """Represents the value object within a webhook change.

    Attributes:
        messaging_product (str): The WhatsApp product (usually 'whatsapp').
        messages (Optional[List[MessageItem]]): A list of messages, if any.
        statuses (Optional[List[StatusItem]]): A list of status updates, if any.
    """

    messaging_product: str
    messages: Optional[List[MessageItem]] = None
    statuses: Optional[List[StatusItem]] = None


class ChangeItem(BaseModel):
    """Represents a single change within an entry.

    Attributes:
        field (str): The field that changed (usually 'messages').
        value (ValueItem): The value containing messages or status updates.
    """

    field: str
    value: ValueItem


class EntryItem(BaseModel):
    """Represents an entry in the webhook payload.

    Attributes:
        id (str): The WhatsApp business account ID.
        changes (List[ChangeItem]): A list of changes included in this entry.
    """

    id: str
    changes: List[ChangeItem]


class WhatsAppWebhookPayload(BaseModel):
    """The root payload for an incoming WhatsApp Cloud API webhook.

    Attributes:
        object (str): The type of object (always 'whatsapp_business_account').
        entry (List[EntryItem]): A list of entries containing the updates.
    """

    object: str
    entry: List[EntryItem]
