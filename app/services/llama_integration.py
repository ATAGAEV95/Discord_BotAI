import os
from typing import Any

import chromadb
from dotenv import load_dotenv
from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from openai import AsyncOpenAI

load_dotenv()


class LlamaIndexManager:
    def __init__(self):
        self.custom_client = AsyncOpenAI(
            api_key=os.getenv("AI_TOKEN1"),
            base_url="https://api.aitunnel.ru/v1/",
        )

        self.embed_model = OpenAIEmbedding(
            api_key=os.getenv("AI_TOKEN1"),
            api_base="https://api.aitunnel.ru/v1/",
            model="text-embedding-3-large",
        )

        self.node_parser = SimpleNodeParser.from_defaults(chunk_size=512)
        self.db = chromadb.PersistentClient(path="./chroma_db")

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

    async def index_messages(self, server_id: int, messages: list[dict[str, Any]]):
        """Индексировать сообщения сервера"""
        try:
            documents = []
            for msg in messages:
                if msg.get("role") in ["user", "assistant"]:
                    content = f"{msg['role']}: {msg['content']}"
                    documents.append(Document(
                        text=content,
                        metadata={"document_type": "message", "server_id": server_id}
                    ))

            if not documents:
                return

            collection = self.get_server_collection(server_id)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            index = VectorStoreIndex.from_documents(
                documents, storage_context=storage_context, show_progress=False
            )
            return index
        except Exception as e:
            print(f"Ошибка индексации сообщений: {e}")
            return None

    async def query_relevant_context(self, server_id: int, query: str, limit: int = 8) -> list[str]:
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

    async def index_server_users(self, server_id: int, users: list[str]):
        """Индексировать список пользователей сервера с использованием метаданных"""
        try:
            collection = self.get_server_collection(server_id)
            collection.delete(where={"document_type": "server_users"})
            users_text = f"Список пользователей сервера: {', '.join(users)}"
            document = Document(
                text=users_text, metadata={"document_type": "server_users", "server_id": server_id}
            )

            vector_store = ChromaVectorStore(chroma_collection=collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            index = VectorStoreIndex.from_documents(
                [document], storage_context=storage_context, show_progress=False
            )

            print(f"Обновлен список пользователей сервера {server_id}: {len(users)} пользователей")
            return index
        except Exception as e:
            print(f"Ошибка индексации пользователей сервера: {e}")
            return None
