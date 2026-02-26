# db_connector.py
# ---------------------------------------------------------
# TinyDB Connector zum Speichern/Laden von Simulationen
# (simpel + effektiv, JSON bleibt sauber).
# ---------------------------------------------------------

from __future__ import annotations
from tinydb import TinyDB
from datetime import datetime
from typing import Any


class DBConnector:
    """
    Kapselt TinyDB, damit app.py keine DB-Details kennen muss.
    """

    def __init__(self, db_path: str = "db.json", table_name: str = "simulations"):
        # Öffnet/erstellt db.json
        self.db = TinyDB(db_path)
        self.table = self.db.table(table_name)

    def save_simulation(self, sim: Any, label: str) -> int:
        """
        Speichert den aktuellen Zustand einer Simulation.
        sim muss to_record_dict(label) bereitstellen.
        """
        record = sim.to_record_dict(label=label)

        # Zeitstempel (für UI-Auswahl)
        record["created_at"] = datetime.now().isoformat(timespec="seconds")

        doc_id = self.table.insert(record)
        return int(doc_id)

    def load_simulation(self, doc_id: int) -> dict:
        """
        Lädt einen Datensatz anhand doc_id.
        """
        record = self.table.get(doc_id=doc_id)
        if record is None:
            raise KeyError(f"Kein Datensatz mit doc_id={doc_id} gefunden.")
        return dict(record)

    def list_simulations(self) -> list[dict]:
        """
        Liste für Dropdown.
        """
        out = []
        for doc in self.table.all():
            out.append(
                {
                    "doc_id": doc.doc_id,
                    "label": doc.get("label", f"run-{doc.doc_id}"),
                    "created_at": doc.get("created_at", ""),
                    "finished": bool(doc.get("finished", False)),
                    "nx": doc.get("nx", None),
                    "ny": doc.get("ny", None),
                    "target_mass_frac": doc.get("target_mass_frac", None),
                }
            )

        # Neueste zuerst
        out.sort(key=lambda d: d.get("created_at", ""), reverse=True)
        return out