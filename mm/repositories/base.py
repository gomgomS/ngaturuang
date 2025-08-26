from typing import Any, Dict, List, Optional

from bson import ObjectId

from config import get_collection


class MongoRepository:
    def __init__(self, collection_name: str):
        self.collection = get_collection(collection_name)

    def insert_one(self, data: Dict[str, Any]) -> str:
        """Insert satu dokumen dan return ID"""
        result = self.collection.insert_one(data)
        return str(result.inserted_id)

    def find_by_id(self, id_str: str) -> Optional[Dict[str, Any]]:
        """Find dokumen berdasarkan ID"""
        try:
            obj_id = ObjectId(id_str)
        except Exception:
            return None
        
        doc = self.collection.find_one({"_id": obj_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    def find_many(self, query: Dict[str, Any], limit: int = 100, sort: Optional[List] = None) -> List[Dict[str, Any]]:
        """Find banyak dokumen dengan query sederhana"""
        try:
            print(f"🔍 [BASE] find_many called with query: {query}, limit: {limit}, sort: {sort}")
            print(f"🔍 [BASE] Collection name: {self.collection.name}")
            
            cursor = self.collection.find(query)
            print(f"🔍 [BASE] Cursor created successfully")
            
            if sort:
                cursor = cursor.sort(sort)
                print(f"🔍 [BASE] Applied sort: {sort}")
            if limit:
                cursor = cursor.limit(limit)
                print(f"🔍 [BASE] Applied limit: {limit}")
            
            docs = list(cursor)
            print(f"🔍 [BASE] Converted cursor to list, got {len(docs)} documents")
            
            # Convert ObjectId ke string untuk JSON
            for doc in docs:
                doc["_id"] = str(doc["_id"])
            
            print(f"🔍 [BASE] Converted ObjectIds to strings")
            print(f"🔍 [BASE] Returning {len(docs)} documents")
            return docs
        except Exception as e:
            print(f"❌ [BASE] Error in find_many: {e}")
            print(f"❌ [BASE] Error type: {type(e)}")
            import traceback
            print(f"❌ [BASE] Error traceback: {traceback.format_exc()}")
            return []

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find satu dokumen"""
        doc = self.collection.find_one(query)
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    def update_by_id(self, id_str: str, updates: Dict[str, Any]) -> bool:
        """Update dokumen berdasarkan ID"""
        try:
            obj_id = ObjectId(id_str)
        except Exception:
            return False
        
        result = self.collection.update_one({"_id": obj_id}, {"$set": updates})
        return result.modified_count > 0

    def delete_by_id(self, id_str: str) -> bool:
        """Delete dokumen berdasarkan ID"""
        try:
            obj_id = ObjectId(id_str)
        except Exception:
            return False
        
        result = self.collection.delete_one({"_id": obj_id})
        return result.deleted_count > 0

    def count(self, query: Dict[str, Any] = None) -> int:
        """Count dokumen"""
        if query is None:
            query = {}
        return self.collection.count_documents(query)


