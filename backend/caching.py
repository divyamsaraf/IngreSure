import json
import os
import hashlib

CACHE_FILE = "verification_cache.json"

def get_cache_key(item_data):
    """Generates a unique key for the item data."""
    serialized = json.dumps(item_data, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def get_cached_verification(item_data):
    key = get_cache_key(item_data)
    cache = load_cache()
    return cache.get(key)

def cache_verification(item_data, result):
    key = get_cache_key(item_data)
    cache = load_cache()
    cache[key] = result
    save_cache(cache)
