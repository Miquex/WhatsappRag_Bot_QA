import os
import pytest
from unittest.mock import patch, mock_open

from app.agent.document_processor import DocumentProcessor

# --- Initialization Tests ---

def test_document_processor_init_success():
    # Arrange & Act
    processor = DocumentProcessor(chunk_size=100)
    
    # Assert
    assert processor.chunk_size == 100
    assert processor.encoding is not None
    assert processor.encoding.name == "cl100k_base"


@patch("app.agent.document_processor.tiktoken.get_encoding")
@patch("app.agent.document_processor.logger")
def test_document_processor_init_fallback(mock_logger, mock_get_encoding):
    # Arrange
    # Force tiktoken to raise an exception
    mock_get_encoding.side_effect = Exception("Tiktoken error")
    
    # Act
    processor = DocumentProcessor()
    
    # Assert
    assert processor.encoding is None
    mock_logger.warning.assert_called_once()
    assert "Could not load tiktoken" in mock_logger.warning.call_args[0][0]


# --- read_document Tests ---

def test_read_document_success(tmp_path):
    # Arrange
    temp_file = tmp_path / "test_doc.txt"
    temp_file.write_text("This is test data.", encoding="utf-8")
    processor = DocumentProcessor()
    
    # Act
    content = processor.read_document(str(temp_file))
    
    # Assert
    assert content == "This is test data."


def test_read_document_file_not_found():
    # Arrange
    processor = DocumentProcessor()
    fake_path = "non_existent_file.txt"
    
    # Act & Assert
    with pytest.raises(FileNotFoundError, match="File not found"):
        processor.read_document(fake_path)


@patch("app.agent.document_processor.Path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open)
@patch("app.agent.document_processor.logger")
def test_read_document_io_error(mock_logger, mock_file, mock_exists):
    # Arrange
    processor = DocumentProcessor()
    mock_file.side_effect = IOError("Permission denied")
    
    # Act & Assert
    with pytest.raises(IOError):
        processor.read_document("some_file.txt")
        
    mock_logger.error.assert_called_with("Error reading file some_file.txt: Permission denied")


# --- chunk_text Tests ---

def test_chunk_text_with_tiktoken():
    # Arrange
    # A chunk size of 10 tokens. 
    processor = DocumentProcessor(chunk_size=10)
    text = "Word word word.\n\n" * 5  # "Word word word." is about 4 tokens ("Word", " word", " word", ".")
    
    # Act
    chunks = processor.chunk_text(text)
    
    # Assert
    # We expect multiple chunks since 20 tokens > 10
    assert len(chunks) > 1
    # Check that it split on paragraphs
    assert "Word word word." in chunks[0]


def test_chunk_text_without_tiktoken():
    # Arrange
    processor = DocumentProcessor(chunk_size=5)
    # Force fallback to word count
    processor.encoding = None 
    
    # Create text: 3 paragraphs, 4 words each. Total 12 words.
    text = (
        "One two three four\n\n"
        "Five six seven eight\n\n"
        "Nine ten eleven twelve"
    )
    
    # Length of a paragraph is 4 words. Chunk size is 5 words.
    # So P1 (4) fits. Next P2 (4) makes 8 > 5, so P1 gets its own chunk.
    # Ultimately 3 chunks.
    
    # Act
    chunks = processor.chunk_text(text)
    
    # Assert
    assert len(chunks) == 3
    assert chunks[0] == "One two three four"
    assert chunks[1] == "Five six seven eight"
    assert chunks[2] == "Nine ten eleven twelve"


def test_chunk_text_empty_input():
    # Arrange
    processor = DocumentProcessor()
    
    # Act
    chunks = processor.chunk_text("")
    
    # Assert
    assert chunks == []


def test_chunk_text_skips_empty_paragraphs():
    # Arrange
    processor = DocumentProcessor(chunk_size=100)
    text = "Paragraph 1\n\n\n\nParagraph 2"  # Contains empty paragraphs inside
    
    # Act
    chunks = processor.chunk_text(text)
    
    # Assert
    assert len(chunks) == 1
    assert chunks[0] == "Paragraph 1\n\nParagraph 2"
