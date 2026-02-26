import streamlit as st

from main import Simulation
from db_connector import DBConnector

st.title("2D Topologieoptimierung")

# ============================================================
# Session State Defaults (vor Widgets!)
# ============================================================
defaults = {
    "sim": None,
    "ran": False,
    "loaded_doc_id": None,

    # aktiver Run (wird beim Laden gesetzt)
    "current_label": None,

    # Widget-Keys
    "nx": 10,
    "ny": 4,
    "mass_pct": 40,
    "load_ix": 0,
    "load_iy": 0,
    "Fx": 0.0,
    "Fy": 0.0,

    # Pending-Mechanismus, um Widget-Keys sicher zu setzen (vor Widgets)
    "pending_record": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# Pending Settings anwenden (GANZ FRÜH, vor Widgets!)
# -> Dadurch springen Slider/Inputs nach dem Laden korrekt
# ============================================================
if st.session_state.pending_record is not None:
    record = st.session_state.pending_record

    st.session_state.nx = int(record["nx"])
    st.session_state.ny = int(record["ny"])
    st.session_state.mass_pct = int(round(float(record["target_mass_frac"]) * 100))

    st.session_state.load_ix = int(record["load_ix"])
    st.session_state.load_iy = int(record["load_iy"])
    st.session_state.Fx = float(record["Fx"])
    st.session_state.Fy = float(record["Fy"])

    # clamp falls nx/ny kleiner geworden sind
    st.session_state.load_ix = min(st.session_state.load_ix, st.session_state.nx - 1)
    st.session_state.load_iy = min(st.session_state.load_iy, st.session_state.ny - 1)

    st.session_state.pending_record = None

# ============================================================
# DB Connector
# ============================================================
db = DBConnector("db.json")

# ============================================================
# SIDEBAR INPUTS (mit Keys)
# ============================================================
st.sidebar.header("Struktur: Settings")

nx = st.sidebar.number_input("Breite (Knoten)", 2, 100, key="nx")
ny = st.sidebar.number_input("Höhe (Knoten)", 2, 100, key="ny")

mass_frac = st.sidebar.slider("Verbleibende Masse (%)", 1, 100, key="mass_pct") / 100.0

st.sidebar.header("Kraft")

# clamp damit Werte im gültigen Bereich bleiben
st.session_state.load_ix = min(int(st.session_state.load_ix), int(nx) - 1)
st.session_state.load_iy = min(int(st.session_state.load_iy), int(ny) - 1)

load_ix = st.sidebar.number_input("Knoten x", 0, int(nx) - 1, key="load_ix")
load_iy = st.sidebar.number_input("Knoten y", 0, int(ny) - 1, key="load_iy")

Fx = st.sidebar.number_input("Fx", key="Fx")
Fy = st.sidebar.number_input("Fy", key="Fy")

# ============================================================
# SPEICHERN / LADEN
# (Buttons untereinander)
# ============================================================
st.sidebar.header("Speichern / Laden")

saved = db.list_simulations()
options = ["(keine)"] + [
    f'#{r["doc_id"]} | {r["label"]} | {r["created_at"]} | finished={r["finished"]}'
    for r in saved
]
selected = st.sidebar.selectbox("Gespeicherte Simulationen", options, index=0)

# Name: wenn ein Run geladen ist, zeige den aktuellen Namen, sonst "run"
default_name = st.session_state.current_label or "run"
save_label = st.sidebar.text_input("Name", value=default_name)

# ------------------------------------------------------------
# Speichern = Update (überschreibt bestehenden Run)
# ------------------------------------------------------------
if st.sidebar.button("Speichern"):
    if st.session_state.sim is None:
        st.sidebar.warning("Keine Simulation im Speicher (erst starten oder laden).")
    else:
        label = (st.session_state.current_label or save_label).strip()
        if not label:
            st.sidebar.warning("Bitte einen Namen eingeben.")
        else:
            try:
                doc_id = db.save_overwrite(st.session_state.sim, label=label)
                st.session_state.loaded_doc_id = doc_id
                st.session_state.current_label = label
                st.sidebar.success(f"Gespeichert (überschrieben): {label}")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Speichern fehlgeschlagen: {e}")

# ------------------------------------------------------------
# Neu speichern = Insert (nur wenn Name noch nicht existiert)
# ------------------------------------------------------------
if st.sidebar.button("Neu speichern"):
    if st.session_state.sim is None:
        st.sidebar.warning("Keine Simulation im Speicher (erst starten oder laden).")
    else:
        label = save_label.strip()
        if not label:
            st.sidebar.warning("Bitte einen Namen eingeben.")
        else:
            try:
                doc_id = db.save_new_unique(st.session_state.sim, label=label)
                st.session_state.loaded_doc_id = doc_id
                st.session_state.current_label = label
                st.sidebar.success(f"Neu gespeichert: {label}")
                st.rerun()
            except Exception as e:
                st.sidebar.error(str(e))

# ------------------------------------------------------------
# Laden
# ------------------------------------------------------------
if st.sidebar.button("Laden"):
    if selected == "(keine)":
        st.sidebar.warning("Bitte einen Eintrag auswählen.")
    else:
        try:
            doc_id = int(selected.split("|")[0].strip().lstrip("#"))
            record = db.load_by_doc_id(doc_id)

            # Simulation rekonstruieren
            sim = Simulation.from_record_dict(record)
            st.session_state.sim = sim
            st.session_state.ran = True
            st.session_state.loaded_doc_id = doc_id
            st.session_state.current_label = record.get("label", None)

            # UI-Werte in pending_record -> werden vor Widgets angewendet
            st.session_state.pending_record = record
            st.rerun()

        except Exception as e:
            st.sidebar.error(f"Laden fehlgeschlagen: {e}")

# ============================================================
# SIMULATION STARTEN (neuer Run -> current_label reset)
# ============================================================
if st.button("Simulation starten"):
    sim = Simulation(nx, ny, mass_frac, load_ix, load_iy, Fx, Fy)
    sim.run()

    st.session_state.sim = sim
    st.session_state.ran = True
    st.session_state.loaded_doc_id = None

    # neuer Run -> nicht an alten Namen gebunden
    st.session_state.current_label = None

# ============================================================
# AUSGABE / PLOTS
# ============================================================
if st.session_state.ran and st.session_state.sim is not None:
    sim = st.session_state.sim

    # Statusanzeige
    if st.session_state.current_label:
        st.caption(f"Aktive Simulation: **{st.session_state.current_label}**")
    else:
        st.caption("Aktive Simulation: (noch nicht gespeichert)")

    all_nodes = set(range(sim.grid.n_nodes))

    st.subheader("Originalstruktur")
    fig_original = sim.plot_structure(u=None, remaining_nodes=all_nodes, scale=1.0)
    st.pyplot(fig_original)

    st.subheader("Optimierungs-Schritte")
    if hasattr(sim, "optim_steps") and sim.optim_steps and len(sim.optim_steps) > 0:
        max_step = len(sim.optim_steps) - 1
        step = st.slider("Schritt wählen", 0, max_step, max_step, 1)
        remaining_nodes_step = sim.optim_steps[step]
        fig_step = sim.plot_structure(u=None, remaining_nodes=remaining_nodes_step, scale=1.0)
        st.pyplot(fig_step)
    else:
        st.write("Keine Optimierungsschritte vorhanden.")

    st.subheader("Verformte Struktur")
    scale = st.slider("Verformung skalieren", 0.01, 1.0, 0.1, 0.01)

    remaining_nodes_for_plot = getattr(sim, "remaining_nodes", None)
    if remaining_nodes_for_plot is None:
        remaining_nodes_for_plot = all_nodes

    fig_deformed = sim.plot_structure(
        u=getattr(sim, "u", None),
        remaining_nodes=remaining_nodes_for_plot,
        scale=scale
    )
    st.pyplot(fig_deformed)