# db_connector.py
# ---------------------------------------------------------
# TinyDB Connector (simpel, aber effektiv) mit:
# - eindeutigen Namen/Labels (jedes Label nur einmal)
# - "Speichern" = Überschreiben (Update) statt immer Insert
# - "Neu speichern" = Insert nur wenn Label noch nicht existiert
# - Laden per doc_id (aus Dropdown) und optional per Label
# ---------------------------------------------------------

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from tinydb import TinyDB, Query


class DBConnector:
    """
    Kapselt TinyDB und stellt eine stabile API für die App bereit.

    Wichtige Idee:
    - label ist bei dir die eindeutige "Projekt-/Run-ID" (Unique Constraint).
    - Speichern überschreibt immer denselben Run (update).
    - Neu speichern ist bewusst "Save As" und verlangt einen neuen Namen.
    """

    def __init__(self, db_path: str = "db.json", table_name: str = "simulations"):
        # Öffnet/erstellt die DB-Datei
        self.db = TinyDB(db_path)
        # Nutzung einer Table ist sauberer als Default-Table
        self.table = self.db.table(table_name)

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    @staticmethod
    def _now() -> str:
        """ISO-Zeitstempel für created_at/updated_at."""
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _normalize_label(label: str) -> str:
        """
        Normalisiert Labels (verhindert z.B. 'Run' vs ' run ' als unterschiedliche Namen).
        Wenn du Case-Sensitivity willst, entferne .lower().
        """
        return label.strip()

    # ---------------------------------------------------------
    # Listing (für Dropdown)
    # ---------------------------------------------------------
    def list_simulations(self) -> list[dict]:
        """
        Gibt Kurzinfos aller gespeicherten Runs zurück (für UI-Auswahl).
        Sortiert nach updated_at (neueste zuerst).
        """
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

    # ---------------------------------------------------------
    # Load
    # ---------------------------------------------------------
    def load_by_doc_id(self, doc_id: int) -> dict:
        """
        Lädt einen Run anhand der TinyDB doc_id (kommt aus dem Dropdown).
        """
        doc = self.table.get(doc_id=doc_id)
        if doc is None:
            raise KeyError(f"Kein Datensatz mit doc_id={doc_id} gefunden.")
        return dict(doc)

    def get_by_label(self, label: str) -> Optional[dict]:
        """
        Holt Datensatz per Label (optional nützlich, z.B. für Debugging).
        """
        Q = Query()
        label_n = self._normalize_label(label)
        doc = self.table.get(Q.label == label_n)
        return dict(doc) if doc is not None else None

    def load_by_label(self, label: str) -> dict:
        """
        Lädt per Label (wirft Fehler, wenn nicht gefunden).
        """
        doc = self.get_by_label(label)
        if doc is None:
            raise KeyError(f"Kein Datensatz mit label='{label}' gefunden.")
        return doc

    # ---------------------------------------------------------
    # Save: Overwrite (Update oder Insert)
    # ---------------------------------------------------------
    def save_overwrite(self, sim: Any, label: str) -> int:
        """
        "Speichern" (Update):
        - Existiert label -> überschreiben (kein neuer Eintrag)
        - Existiert label nicht -> neuen Eintrag anlegen

        Rückgabe: doc_id des Eintrags.
        """
        Q = Query()
        label_n = self._normalize_label(label)
        if not label_n:
            raise ValueError("Label/Name darf nicht leer sein.")

        now = self._now()
        record = sim.to_record_dict(label=label_n)

        # Label erzwingen (damit DB konsistent bleibt)
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

            # TinyDB update: überschreibt Felder im Dokument
            self.table.update(record, Q.label == label_n)
            return int(existing.doc_id)

    # ---------------------------------------------------------
    # Save: New Unique (Insert only)
    # ---------------------------------------------------------
    def save_new_unique(self, sim: Any, label: str) -> int:
        """
        "Neu speichern" (Save As):
        - Legt IMMER einen neuen Run an
        - Name muss eindeutig sein, sonst ValueError
        """
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

    # ---------------------------------------------------------
    # Optional: Delete (wenn du später willst)
    # ---------------------------------------------------------
    def delete_by_doc_id(self, doc_id: int) -> None:
        """Löscht einen Run per doc_id."""
        self.table.remove(doc_ids=[doc_id])