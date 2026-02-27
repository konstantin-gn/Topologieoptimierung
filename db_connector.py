from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from tinydb import TinyDB, Query

# Kapselt die DB-Logik mit TinyDB, damit der Hauptcode in app.py übersichtlich bleibt.
class DBConnector:

    def __init__(self, db_path: str = "db.json", table_name: str = "simulations"):
        # Öffnet die DB-Datei
        self.db = TinyDB(db_path)
        self.table = self.db.table(table_name)

    # Hilfsmethode: Zeitstempel für created_at/updated_at im ISO-Format
    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    # Normalisierung von Labels ("  test  " -> "test")
    @staticmethod
    def _normalize_label(label: str) -> str:
        return label.strip()

    # Liste aller gespeicherten Runs mit Kurzinfos (für Dropdown-Auswahl)
    # Sortiert nach updated_at (neueste zuerst).
    def list_simulations(self) -> list[dict]:
        out: list[dict] = []
        for doc in self.table.all():
            out.append(
                {
                    "doc_id": doc.doc_id,
                    "label": doc.get("label", f"run-{doc.doc_id}"),
                    "created_at": doc.get("created_at", ""),
                    "updated_at": doc.get("updated_at", ""),
                    "finished": bool(doc.get("finished", False)),
                    "nx": doc.get("nx", None),
                    "ny": doc.get("ny", None),
                    "target_mass_frac": doc.get("target_mass_frac", None),
                }
            )

        out.sort(key=lambda d: d.get("updated_at") or d.get("created_at", ""), reverse=True)
        return out

    # Laden anhand doc_id (z.B. aus Dropdown-Auswahl)
    def load_by_doc_id(self, doc_id: int) -> dict:
        doc = self.table.get(doc_id=doc_id)
        if doc is None:
            raise KeyError(f"Kein Datensatz mit doc_id={doc_id} gefunden.")
        return dict(doc)
    
    # Sucht nach einem Dokument mit dem gegebenen Label     
    def get_by_label(self, label: str) -> Optional[dict]:
        Q = Query()
        label_n = self._normalize_label(label)
        doc = self.table.get(Q.label == label_n)
        return dict(doc) if doc is not None else None

    # Laden per Label 
    def load_by_label(self, label: str) -> dict:
        doc = self.get_by_label(label)
        if doc is None:
            raise KeyError(f"Kein Datensatz mit label='{label}' gefunden.")
        return doc

    
    # Speichern: Overwrite (Update oder Insert)
    def save_overwrite(self, sim: Any, label: str) -> int:
        
        # "Speichern" (Update):
        # Existiert label -> überschreiben (kein neuer Eintrag)
        # Existiert label nicht -> neuen Eintrag anlegen
        Q = Query()
        label_n = self._normalize_label(label)
        if not label_n:
            raise ValueError("Label/Name darf nicht leer sein.")

        now = self._now()
        record = sim.to_record_dict(label=label_n)

        # Label erzwingen )
        record["label"] = label_n

        existing = self.table.get(Q.label == label_n)

        if existing is None:
            # Neuer Run
            record["created_at"] = now
            record["updated_at"] = now
            doc_id = self.table.insert(record)
            return int(doc_id)
        else:
            # Bestehenden Run überschreiben, created_at behalten
            record["created_at"] = existing.get("created_at", now)
            record["updated_at"] = now

            # update: überschreibt Felder im Dokument
            self.table.update(record, Q.label == label_n)
            return int(existing.doc_id)

    # neu speichern = Save As (nur wenn Name noch nicht existiert)
    def save_new_unique(self, sim: Any, label: str) -> int:
        
        # "Neu speichern" (Insert):
        # - Existiert label -> Fehler (Name muss eindeutig sein)
        # - Existiert label nicht -> neuen Eintrag anlegen

        Q = Query()
        label_n = self._normalize_label(label)
        if not label_n:
            raise ValueError("Label/Name darf nicht leer sein.")
        
        if self.table.get(Q.label == label_n) is not None:
            raise ValueError(f"Name '{label_n}' existiert bereits. Bitte anderen Namen wählen.")

        now = self._now()
        record = sim.to_record_dict(label=label_n)
        record["label"] = label_n
        record["created_at"] = now
        record["updated_at"] = now

        doc_id = self.table.insert(record)
        return int(doc_id)
    
    # Löschen eines Runs per doc_id
    def delete_by_doc_id(self, doc_id: int) -> None:
        self.table.remove(doc_ids=[doc_id])

    