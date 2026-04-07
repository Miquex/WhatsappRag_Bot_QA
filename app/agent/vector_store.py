from typing import Any, List, Optional
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from chromadb.api.models.Collection import Collection
from app.core.config import settings
from loguru import logger


class VectorStore:
    """Manages the storage and retrieval of document embeddings in ChromaDB.

    This class provides tools to store, update, and search document chunks using
    OpenAI embeddings for semantic similarity.

    Attributes:
        client (chromadb.PersistentClient): The ChromaDB client instance.
        collection_name (str): The name of the collection being managed.
        openai_ef (embedding_functions.OpenAIEmbeddingFunction): The embedding
            function used for transformations.
        collection (Collection): The ChromaDB collection being used.
    """

    client: chromadb.PersistentClient
    collection_name: str
    openai_ef: embedding_functions.OpenAIEmbeddingFunction
    collection: Collection

    def __init__(self, collection_name: str = 'business_knowledge') -> None:
        """Initializes the VectorStore, loading the persistent client and collection.

        Args:
            collection_name (str): The name of the collection to load or create.
                Defaults to 'business_knowledge'.
        """
        self.client = chromadb.PersistentClient(path=str(settings.CHROMA_DB_DIR))
        self.collection_name = collection_name
        try:
            self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.OPENAI_API_KEY, model_name='text-embedding-3-small'
            )
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name, embedding_function=self.openai_ef
            )
            logger.info(f'VectorStore loaded on {settings.CHROMA_DB_DIR}')
        except Exception as e:
            logger.error(f'Failed to initialize VectorStore: {e}')
            raise e

    def upsert_documents(self, chunks: List[str]) -> None:
        """Adds or updates document chunks in the vector collection.

        Args:
            chunks (List[str]): A list of text strings to store in the database.
        """
        if not chunks:
            return
        ids: List[str] = [f'chunk_{i}' for i in range(len(chunks))]
        try:
            self.collection.upsert(documents=chunks, ids=ids)
            logger.info(f'Upserted {len(chunks)} chunks into ChromaDB.')
        except Exception as e:
            logger.error(f'Error upserting documents: {e}')

    def semantic_search(self, query: str, top_k: int = 3) -> str:
        """Searches the vector store for the most relevant context for a query.

        Args:
            query (str): The user's input string to search for.
            top_k (int): The number of top results to retrieve. Defaults to 3.

        Returns:
            str: A combined string of the retrieved context, or an error message.
        """
        try:
            results = self.collection.query(query_texts=[query], n_results=top_k)
            if not results['documents'] or not results['documents'][0]:
                return 'No relevant information found.'
            combined_context: str = '\n\n---\n\n'.join(results['documents'][0])
            return combined_context
        except Exception as e:
            logger.error(f'Vector search failed: {e}')
            return ''


vector_store: VectorStore = VectorStore()
