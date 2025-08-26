from typing import Any, Dict, List

from mm.repositories.base import MongoRepository


class GoalRepository(MongoRepository):
    def __init__(self):
        super().__init__("goals")

    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        return self.find_many({"user_id": user_id}, limit=100)


