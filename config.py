import os
from typing import Optional, Dict, List, Tuple, Any

from pymongo import MongoClient


# Database names and connection strings (LOCAL ONLY defaults)
mainDB: str = "moneymagementdb"
mainDB_string: str = "mongodb://127.0.0.1:27017/" + mainDB


_mongo_client: Optional[MongoClient] = None


def get_mongo_client() -> MongoClient:
    """Return a singleton MongoClient using env vars when provided.

    Env:
      - MONGODB_URI: e.g. mongodb://127.0.0.1:27017
    """
    global _mongo_client
    if _mongo_client is None:
        uri = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
        _mongo_client = MongoClient(uri, appname="moneymanagement.ai")
    return _mongo_client


def get_db(db_name: Optional[str] = None):
    """Return a Database handle. Defaults to mainDB or env DB_NAME."""
    client = get_mongo_client()
    name = db_name or os.getenv("DB_NAME", mainDB)
    return client[name]


def get_collection(collection_name: str):
    """Convenience accessor for a collection in the default database."""
    return get_db()[collection_name]


def ensure_indexes(index_specs: Dict[str, List[Tuple]]):
    """Create indexes based on {collection: [(keys, options_dict), ...]} specs.

    Example:
        ensure_indexes({
            "transactions": [
                (("user_id", 1), {"name": "idx_tx_user"}),
                (("timestamp", -1), {"name": "idx_tx_time"}),
            ]
        })
    """
    db = get_db()
    for collection_name, index_list in index_specs.items():
        coll = db[collection_name]
        for keys, options in index_list:
            coll.create_index([keys] if isinstance(keys[0], str) else keys, **(options or {}))



