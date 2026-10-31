"""Un adapter per piattaforma: legge i risultati e li restituisce nel formato comune."""

from __future__ import annotations


def get_adapter(name: str):
    if name == "picklebook":
        from live.adapters import picklebook

        return picklebook
    raise ValueError(f"Adapter sconosciuto: {name}")
