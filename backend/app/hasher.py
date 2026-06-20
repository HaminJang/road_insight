import hashlib

def generate_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()

def is_duplicate(image_bytes: bytes, existing_hashes: set) -> bool:
    hash_value = generate_hash(image_bytes)
    return hash_value in existing_hashes
