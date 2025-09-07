import os
from typing import List, Dict, Any
from llama_index.core import VectorStoreIndex, Document, StorageContext, Settings
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.openai import OpenAI
import chromadb
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


class LlamaIndexManager:
    def __init__(self):
        # Создаем кастомный клиент OpenAI для вашего провайдера
        self.custom_client = AsyncOpenAI(
            api_key=os.getenv("AI_TOKEN1"),
            base_url="https://api.aitunnel.ru/v1/",
        )

        # Настройка LLM с использованием кастомного клиента
        self.llm = OpenAI(
            api_key=os.getenv("AI_TOKEN1"),
            api_base="https://api.aitunnel.ru/v1/",
            model="gpt-5-chat"
        )

        # Настройка embedding модели с использованием кастомного клиента
        self.embed_model = OpenAIEmbedding(
            api_key=os.getenv("AI_TOKEN1"),
            api_base="https://api.aitunnel.ru/v1/",
            # model="text-embedding-3-small"
            model="text-embedding-3-large"
        )

        # Настройка парсера документов
        self.node_parser = SimpleNodeParser.from_defaults(chunk_size=512)

        # Инициализация ChromaDB
        self.db = chromadb.PersistentClient(path="./chroma_db")

        # Глобальные настройки
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        Settings.node_parser = self.node_parser

    def get_server_collection(self, server_id: int):
        """Получить или создать коллекцию для сервера"""
        collection_name = f"server_{server_id}_messages"
        try:
            collection = self.db.get_collection(collection_name)
        except:
            collection = self.db.create_collection(collection_name)
        return collection

    async def index_messages(self, server_id: int, messages: List[Dict[str, Any]]):
        """Индексировать сообщения сервера"""
        try:
            documents = []
            for msg in messages:
                if msg.get('role') in ['user', 'assistant']:
                    content = f"{msg['role']}: {msg['content']}"
                    documents.append(Document(text=content))

            if not documents:
                return

            collection = self.get_server_collection(server_id)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                show_progress=False
            )
            return index
        except Exception as e:
            print(f"Ошибка индексации сообщений: {e}")
            return None

    async def query_relevant_context(self, server_id: int, query: str, limit: int = 8) -> List[str]:
        """Найти релевантный контекст для запроса на сервере"""
        try:
            collection = self.get_server_collection(server_id)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            index = VectorStoreIndex.from_vector_store(vector_store)

            retriever = index.as_retriever(similarity_top_k=limit)
            nodes = retriever.retrieve(query)

            relevant_contexts = [node.text for node in nodes]
            return relevant_contexts
        except Exception as e:
            print(f"Ошибка поиска контекста: {e}")
            return []