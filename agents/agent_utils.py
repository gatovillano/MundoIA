"""
Utilities to resolve agent identifiers and display names.
These helpers allow APIs and other layers to accept either a unique_id
(e.g., "ag_123abc") or a human-friendly name and consistently
map between them.
"""
from typing import Optional


def resolve_agent_unique_id(sim, identifier: Optional[str]) -> Optional[str]:
    """Given a simulation instance `sim` and an identifier which may be
    either a unique_id or a display name, return the canonical unique_id
    if found, otherwise None.
    """
    if not identifier:
        return None
    # If it's already a unique_id in the simulation
    for a in getattr(sim, "agentes", []):
        if getattr(a, "unique_id", None) == identifier:
            return a.unique_id
    # Match by display name (case-insensitive)
    low = str(identifier).lower()
    for a in getattr(sim, "agentes", []):
        identidad = getattr(a, "identidad", None)
        if identidad and getattr(identidad, "nombre", "").lower() == low:
            return a.unique_id
    return None


def display_name_for(sim, agent_id: Optional[str]) -> Optional[str]:
    """Return a human-friendly display name for an agent given its internal id
    or name. Falls back to the internal id when no name is available.
    """
    if not agent_id:
        return None
    # If agent_id corresponds to a unique id, return its name
    for a in getattr(sim, "agentes", []):
        if getattr(a, "unique_id", None) == agent_id:
            identidad = getattr(a, "identidad", None)
            return getattr(identidad, "nombre", None) or a.unique_id
    # If agent_id is already a name, normalize and return it
    for a in getattr(sim, "agentes", []):
        identidad = getattr(a, "identidad", None)
        if identidad and getattr(identidad, "nombre", None) == agent_id:
            return identidad.nombre
    return agent_id
