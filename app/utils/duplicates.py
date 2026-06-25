from uuid import UUID


def find_duplicate_of(checksum: str, seen_checksums: dict[str, UUID]) -> UUID | None:
    return seen_checksums.get(checksum)
