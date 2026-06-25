import hashlib


def sha256_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
