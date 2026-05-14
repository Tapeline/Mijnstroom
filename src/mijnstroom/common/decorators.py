from dataclasses import dataclass
from typing import dataclass_transform


@dataclass_transform(frozen_default=True)
def entity[T](cls: type[T]) -> type[T]:
    """Domain entity: frozen, slotted dataclass."""
    return dataclass(frozen=True, slots=True)(cls)


@dataclass_transform(frozen_default=True)
def value_object[T](cls: type[T]) -> type[T]:
    """Domain value object: frozen, slotted dataclass."""
    return dataclass(frozen=True, slots=True)(cls)


@dataclass_transform()
def interactor[T](cls: type[T]) -> type[T]:
    """Application interactor: slotted dataclass (mutable for DI)."""
    return dataclass(slots=True)(cls)


@dataclass_transform(frozen_default=True)
def dto[T](cls: type[T]) -> type[T]:
    """Immutable transfer object."""
    return dataclass(frozen=True, slots=True)(cls)


