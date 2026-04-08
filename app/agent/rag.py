from typing import Any, Dict, List, Optional
from app.core.config import settings
from loguru import logger
from openai import AsyncOpenAI
from app.agent.vector_store import vector_store
from app.agent.document_processor import document_processor
from app.agent.memory import memory_manager


class RagAgent:
    """Agent that handles Retrieval-Augmented Generation (RAG) for user queries.

    This agent initializes a knowledge base in a vector store and provides an asynchronous
    interface for querying the business's information using OpenAI's models.

    Attributes:
        openai_client (AsyncOpenAI): The OpenAI client for asynchronous completions.
    """

    openai_client: AsyncOpenAI

    def __init__(self) -> None:
        """Initializes the RagAgent and the OpenAI client."""
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._initialize_knowledge()

    def _initialize_knowledge(self) -> None:
        """Reads and chunks document knowledge into the vector database."""
        try:
            logger.info('Initializing knowledge base into Vector DB...')
            text = document_processor.read_document(settings.RAG_MD_PATH)
            chunks = document_processor.chunk_text(text)
            vector_store.upsert_documents(chunks)
        except Exception as e:
            logger.error(f'Failed to initialize knowledge base: {e}')

    async def query_rag(self, query: str, user_phone: str) -> str:
        """Queries the RAG system using retrieved context and conversation history.

        Args:
            query (str): The user's input/question.
            user_phone (str): The user's phone number for context and history.

        Returns:
            str: The AI-generated response based on the context and history.
        """
        try:
            retrieved_context = vector_store.semantic_search(query, top_k=3)
            chat_history = memory_manager.get_history(user_phone)
            system_prompt = f'\n            Eres un asistente virtual de atención al cliente.\n            A continuación, se te proporcionará información relevante del negocio ("Contexto").\n            Tu objetivo es responder a la pregunta del usuario utilizando ÚNICAMENTE esta información.\n            Si el usuario hace referencia a algo que dijo antes, usa el historial de la conversación, \n            pero siempre responde enfocado en el Contexto.\n            Si la información en el "Contexto" no es suficiente para responder la pregunta, \n            di amablemente que no lo sabes y pregunta si desean hablar con un agente humano.\n            \n            Contexto:\n            {retrieved_context}\n            '
            messages: List[Dict[str, str]] = [{'role': 'system', 'content': system_prompt}]
            messages.extend(chat_history)
            messages.append({'role': 'user', 'content': query})
            response = await self.openai_client.chat.completions.create(
                model='gpt-4o-mini', messages=messages, temperature=0.2
            )
            result_content = response.choices[0].message.content
            if result_content:
                memory_manager.add_message(
                    phone_number=user_phone, role='user', content=query
                )
                memory_manager.add_message(
                    phone_number=user_phone, role='assistant', content=result_content
                )
                return result_content
            return 'Sorry, an unexpected error occurred while processing your message.'
        except Exception as e:
            logger.error(f'Error querying RAG: {e}')
            return 'Sorry, I'm having technical difficulties right now.'


rag_agent: RagAgent = RagAgent()
