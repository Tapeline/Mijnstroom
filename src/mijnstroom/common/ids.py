import uuid


def generate_id[T: str](tag: type[T]) -> T:
    """Generate a UUID4-based identifier of the given NewType string tag."""
    return tag(uuid.uuid4().hex)
