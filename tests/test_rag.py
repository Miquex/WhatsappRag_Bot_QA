import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agent.rag import RagAgent


@pytest.fixture
def mock_openai_client():
    with patch("app.agent.rag.AsyncOpenAI") as mock:
        yield mock


@pytest.fixture
def mock_document_processor():
    with patch("app.agent.rag.document_processor") as mock:
        yield mock


@pytest.fixture
def mock_vector_store():
    with patch("app.agent.rag.vector_store") as mock:
        yield mock


@pytest.fixture
def mock_memory_manager():
    with patch("app.agent.rag.memory_manager") as mock:
        yield mock


# --- Tests for Initialization ---

def test_initialize_knowledge_success(mock_openai_client, mock_document_processor, mock_vector_store):
    # Arrange
    # Mocking read and chunks
    mock_document_processor.read_document.return_value = "raw text"
    mock_document_processor.chunk_text.return_value = ["chunk 1", "chunk 2"]

    # Act
    # Instantiating the agent triggers _initialize_knowledge automatically
    agent = RagAgent()

    # Assert
    mock_document_processor.read_document.assert_called_once()
    mock_document_processor.chunk_text.assert_called_once_with("raw text")
    mock_vector_store.upsert_documents.assert_called_once_with(["chunk 1", "chunk 2"])


@patch("app.agent.rag.logger")
def test_initialize_knowledge_failure(mock_logger, mock_openai_client, mock_document_processor):
    # Arrange
    # Force an exception during initialization
    mock_document_processor.read_document.side_effect = Exception("File missing")

    # Act
    agent = RagAgent()

    # Assert
    mock_logger.error.assert_called_with("Failed to initialize knowledge base: File missing")


# --- Tests for query_rag ---

@pytest.mark.asyncio
async def test_query_rag_success(
    mock_openai_client, 
    mock_document_processor, 
    mock_vector_store, 
    mock_memory_manager
):
    # Arrange: Set up agent
    agent = RagAgent()
    
    query = "What is the price?"
    phone = "123456789"
    retrieved_context = "The price is 100 dollars."
    mock_history = [{"role": "user", "content": "hello"}]
    mock_ai_response = "It costs 100 dollars."

    # Setup mocks
    mock_vector_store.semantic_search.return_value = retrieved_context
    mock_memory_manager.get_history.return_value = mock_history
    
    # Mock the completion create properly for AsyncOpenAI
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = mock_ai_response
    mock_completion.choices = [mock_choice]
    
    # Since agent.openai_client resolves from mock_openai_client.return_value
    mock_openai_instance = mock_openai_client.return_value
    mock_openai_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

    # Act
    result = await agent.query_rag(query, phone)

    # Assert returns
    assert result == mock_ai_response
    
    # Assert Semantic Search called
    mock_vector_store.semantic_search.assert_called_once_with(query, top_k=3)
    
    # Assert Chat History called
    mock_memory_manager.get_history.assert_called_once_with(phone)
    
    # Assert OpenAI API called correctly
    mock_openai_instance.chat.completions.create.assert_awaited_once()
    call_kwargs = mock_openai_instance.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["temperature"] == 0.2
    
    # Verify exactly 3 messages sent: (System Context, History, User Question)
    sent_messages = call_kwargs["messages"]
    assert len(sent_messages) == 3
    assert sent_messages[0]["role"] == "system" 
    assert retrieved_context in sent_messages[0]["content"]
    assert sent_messages[1] == mock_history[0]
    assert sent_messages[2]["role"] == "user"
    assert sent_messages[2]["content"] == query

    # Assert Memory Manager is updated
    assert mock_memory_manager.add_message.call_count == 2
    mock_memory_manager.add_message.assert_any_call(
        phone_number=phone, role="user", content=query
    )
    mock_memory_manager.add_message.assert_any_call(
        phone_number=phone, role="assistant", content=mock_ai_response
    )


@pytest.mark.asyncio
async def test_query_rag_empty_content(
    mock_openai_client, 
    mock_document_processor, 
    mock_vector_store, 
    mock_memory_manager
):
    # Arrange
    agent = RagAgent()
    mock_vector_store.semantic_search.return_value = "info"
    mock_memory_manager.get_history.return_value = []
    
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = None # Ex: OpenAI returns no content
    mock_completion.choices = [mock_choice]
    
    mock_openai_instance = mock_openai_client.return_value
    mock_openai_instance.chat.completions.create = AsyncMock(return_value=mock_completion)

    # Act
    result = await agent.query_rag("query", "phone")

    # Assert
    assert result == "Lo siento, ocurrió un error inesperado al procesar tu mensaje."
    mock_memory_manager.add_message.assert_not_called()


@pytest.mark.asyncio
@patch("app.agent.rag.logger")
async def test_query_rag_exception(
    mock_logger,
    mock_openai_client, 
    mock_document_processor, 
    mock_vector_store, 
    mock_memory_manager
):
    # Arrange
    agent = RagAgent()
    
    # Force generic exception
    mock_vector_store.semantic_search.side_effect = Exception("DB failure")

    # Act
    result = await agent.query_rag("query", "phone")

    # Assert
    assert result == "Lo siento, estoy teniendo dificultades técnicas en este momento."
    mock_logger.error.assert_called_once()
    assert "Error querying RAG:" in mock_logger.error.call_args[0][0]
    mock_memory_manager.add_message.assert_not_called()
