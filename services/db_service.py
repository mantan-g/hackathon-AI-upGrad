# db_service.py

from typing import Any, Dict, List, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

uri = "mongodb+srv://upgrad-AI-hackathon:EaTobcg6VKAT5iY4@cluster0.5y9bri6.mongodb.net/"

client: MongoClient = MongoClient(uri)
db_name = "glimseAI"
db: Database = client[db_name]


class DBService:
    def _get_collection(self, collection_name: str) -> Collection:
        """Helper to get a collection by name."""
        return db[collection_name]

    # Create
    def insert_one(self, collection_name: str, data: Dict[str, Any]) -> str:
        result = self._get_collection(collection_name).insert_one(data)
        return str(result.inserted_id)

    def insert_many(self, collection_name: str, data_list: List[Dict[str, Any]]) -> List[str]:
        result = self._get_collection(collection_name).insert_many(data_list)
        return [str(_id) for _id in result.inserted_ids]

    # Read
    def find_one(self, collection_name: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._get_collection(collection_name).find_one(query)

    def find_many(self, collection_name: str, query: Dict[str, Any] = {}, limit: int = 0) -> List[Dict[str, Any]]:
        cursor = self._get_collection(collection_name).find(query).limit(limit)
        return list(cursor)

    # Update
    def update_one(self, collection_name: str, query: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        result = self._get_collection(collection_name).update_one(query, {"$set": update_data})
        return result.modified_count

    def update_many(self, collection_name: str, query: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        result = self._get_collection(collection_name).update_many(query, {"$set": update_data})
        return result.modified_count

    # Delete
    def delete_one(self, collection_name: str, query: Dict[str, Any]) -> int:
        result = self._get_collection(collection_name).delete_one(query)
        return result.deleted_count

    def delete_many(self, collection_name: str, query: Dict[str, Any]) -> int:
        result = self._get_collection(collection_name).delete_many(query)
        return result.deleted_count

    # Utility
    def count_documents(self, collection_name: str, query: Dict[str, Any] = {}) -> int:
        return self._get_collection(collection_name).count_documents(query)

    def drop_collection(self, collection_name: str) -> None:
        self._get_collection(collection_name).drop()

    def close_connection(self) -> None:
        self.client.close()
