import json
import os
from typing import Any, Dict, List, Optional
from bson import ObjectId
from mm.repositories.base import MongoRepository


class CategoryRepository(MongoRepository):
    def __init__(self):
        super().__init__("categories")

    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get semua kategori untuk user tertentu"""
        try:
            return self.find_many({"user_id": user_id}, limit=100)
        except Exception:
            return []

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find satu dokumen"""
        try:
            return super().find_one(query)
        except Exception as e:
            print(f"Error in category find_one: {e}")
            return None

    def update_category(self, category_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update category dengan validasi user ownership dan system category protection"""
        try:
            # Check if it's a system category (default category)
            if category_id in ["transfer", "income_general", "expense_general"]:
                return False
            
            # Convert string ID ke ObjectId
            obj_id = ObjectId(category_id)
            
            # Pastikan category milik user yang bersangkutan
            existing_category = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_category:
                return False
            
            # Update dengan ObjectId
            result = self.collection.update_one({"_id": obj_id}, {"$set": updates})
            return result.modified_count > 0
        except Exception:
            return False
    
    def delete_category(self, category_id: str, user_id: str) -> bool:
        """Delete category dengan validasi user ownership dan system category protection"""
        try:
            # Check if it's a system category (default category)
            if category_id in ["transfer", "income_general", "expense_general"]:
                return False
            
            # Convert string ID ke ObjectId
            obj_id = ObjectId(category_id)
            
            # Pastikan category milik user yang bersangkutan
            existing_category = self.collection.find_one({"_id": obj_id, "user_id": user_id})
            if not existing_category:
                return False
            
            # Delete dengan ObjectId
            result = self.collection.delete_one({"_id": obj_id})
            return result.deleted_count > 0
        except Exception:
            return False
    
    def get_default_categories(self) -> List[Dict[str, Any]]:
        """Get default categories dari JSON file"""
        try:
            # Path ke file JSON default categories
            json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   'static', 'data', 'default_categories.json')
            
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    default_categories = json.load(f)
                
                # Convert ke format yang sesuai dengan database
                formatted_categories = []
                for cat in default_categories:
                    formatted_cat = {
                        "_id": cat["id"],  # Use string ID for default categories
                        "name": cat["name"],
                        "type": cat["type"],
                        "description": cat.get("description", ""),
                        "icon": cat.get("icon", "fas fa-tag"),
                        "color": cat.get("color", "#6c757d"),
                        "is_default": cat.get("is_default", True),
                        "is_system": cat.get("is_system", False),
                        "user_id": "system"  # Mark as system category
                    }
                    formatted_categories.append(formatted_cat)
                
                return formatted_categories
            else:
                return []
                
        except Exception as e:
            return []
    
    def list_by_user_with_defaults(self, user_id: str) -> List[Dict[str, Any]]:
        """Get categories untuk user termasuk default categories"""
        try:
            # Get user categories
            user_categories = self.list_by_user(user_id)
            
            # Get default categories
            default_categories = self.get_default_categories()
            
            # Combine both lists
            all_categories = default_categories + user_categories
            
            return all_categories
            
        except Exception as e:
            return []
    
    def get_category_by_id(self, category_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get category by ID (bisa dari default atau user)"""
        try:
            # First check default categories
            default_categories = self.get_default_categories()
            for cat in default_categories:
                if cat["_id"] == category_id:
                    return cat
                    
            # If not found in defaults, check user categories
            if user_id:
                obj_id = ObjectId(category_id)
                return self.collection.find_one({"_id": obj_id, "user_id": user_id})
            
            return None
            
        except Exception as e:
            return None
