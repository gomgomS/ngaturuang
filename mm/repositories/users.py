from typing import Any, Dict, Optional

from mm.repositories.base import MongoRepository


class UserRepository(MongoRepository):
    def __init__(self):
        super().__init__("users")

    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        docs = self.find_many({"username": username}, limit=1)
        return docs[0] if docs else None


