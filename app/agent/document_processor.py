"""Module for processing documents and splitting text into chunks.

This module provides the DocumentProcessor class, which handles reading text files
and dividing their content into smaller, manageable pieces for further processing.
"""
from pathlib import Path
from loguru import logger
import tiktoken
from typing import List, Optional


class DocumentProcessor:
    """Handles loading, cleaning, and chunking of document text.

    This class provides tools to read documents from the filesystem and split
    them into logical chunks based on token counts or word counts.

    Attributes:
        chunk_size (int): The target size for each text chunk.
        encoding (Optional[tiktoken.Encoding]): The tiktoken encoding used for
            token counting, if available.
    """

    chunk_size: int
    encoding: Optional[tiktoken.Encoding]

    def __init__(self, chunk_size: int = 500) -> None:
        """Initializes the DocumentProcessor with a specific chunk size.

        Args:
            chunk_size: The maximum size of each text chunk. Defaults to 500.
        """
        self.chunk_size = chunk_size
        try:
            self.encoding = tiktoken.get_encoding('cl100k_base')
        except Exception as e:
            logger.warning(
                f'Could not load tiktoken, falling back to simple word count. Error: {e}'
            )
            self.encoding = None

    def read_document(self, file_path: str) -> str:
        """Reads the content of a document file.

        Args:
            file_path: The path to the file to be read.

        Returns:
            The full text content of the file.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            IOError: If there is an error reading the file.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f'File not found: {path}')
            raise FileNotFoundError(f'File not found: {path}')
        try:
            with open(path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f'Error reading file {path}: {e}')
            raise

    def chunk_text(self, text: str) -> List[str]:
        """Splits a string of text into smaller chunks for processing.

        Chunks are split by paragraphs to maintain context. If tiktoken is
        available, sizes are calculated based on tokens; otherwise, they
        are calculated based on word count.

        Args:
            text: The full text string to be chunked.

        Returns:
            A list of text chunks, each approximately within the target chunk size.
        """
        paragraphs = text.split('\n\n')
        chunks: List[str] = []
        current_chunk = ''
        current_length = 0
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if self.encoding:
                para_len = len(self.encoding.encode(paragraph))
            else:
                para_len = len(paragraph.split())
            if current_length + para_len > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
                current_length = para_len
            else:
                current_chunk += '\n\n' + paragraph if current_chunk else paragraph
                current_length += para_len
        if current_chunk:
            chunks.append(current_chunk.strip())
        logger.info(f'Split document into {len(chunks)} chunks.')
        return chunks


document_processor: DocumentProcessor = DocumentProcessor()
