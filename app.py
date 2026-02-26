import streamlit as st

from main import Simulation
from db_connector import DBConnector  # TinyDB Wrapper-Klasse

st.title("2D Topologieoptimierung")

# ------------------------------------------------------------
# Session State initialisieren
# -> hält Simulation zwischen Streamlit-Interaktionen stabil
# ------------------------------------------------------------
if "sim" not in st.session_state:
    st.session_state.sim = None

if "ran" not in st.session_state:
    st.session_state.ran = False

if "loaded_doc_id" not in st.session_state:
    st.session_state.loaded_doc_id = None

# ------------------------------------------------------------
# DB Connector (db.json muss im Projekt liegen)
# ------------------------------------------------------------
db = DBConnector("db.json")

# --- Sidebar Inputs ---
st.sidebar.header("Struktur: Settings")

nx = st.sidebar.number_input("Breite (Knoten)", 2, 100, 10, key="nx")
ny = st.sidebar.number_input("Höhe (Knoten)", 2, 100, 4, key="ny")
mass_frac = st.sidebar.slider("Verbleibende Masse (%)", 1, 100, 40, key="mass_pct") / 100.0

st.sidebar.header("Kraft")

load_ix = st.sidebar.number_input("Knoten x", 0, st.session_state.nx - 1, 0, key="load_ix")
load_iy = st.sidebar.number_input("Knoten y", 0, st.session_state.ny - 1, 0, key="load_iy")
Fx = st.sidebar.number_input("Fx", value=0.0, key="Fx")
Fy = st.sidebar.number_input("Fy", value=0.0, key="Fy")

# ------------------------------------------------------------
# SPEICHERN / LADEN / FORTSETZEN (minimaler UI-Block)
# ------------------------------------------------------------
st.sidebar.header("Speichern / Laden")

# DB-Einträge laden und für Dropdown hübsch formatieren
saved = db.list_simulations()
options = ["(keine)"] + [
    f'#{r["doc_id"]} | {r["label"]} | {r["created_at"]} | finished={r["finished"]}'
    for r in saved
]

selected = st.sidebar.selectbox("Gespeicherte Simulationen", options, index=0)

# Label für Save
save_label = st.sidebar.text_input("Save-Name", value="run")

colA, colB, colC = st.sidebar.columns(3)

with colA:
    if st.button("Speichern"):
        # Speichern geht nur, wenn eine Simulation im Speicher ist
        if st.session_state.sim is None:
            st.sidebar.warning("Keine Simulation im Speicher (erst starten oder laden).")
        else:
            try:
                # Speichert den aktuellen Stand (inkl. remaining_nodes, optim_steps, u, etc.)
                doc_id = db.save_simulation(st.session_state.sim, label=save_label)
                st.session_state.loaded_doc_id = doc_id
                st.sidebar.success(f"Gespeichert als #{doc_id}")
            except Exception as e:
                st.sidebar.error(f"Speichern fehlgeschlagen: {e}")

with colB:
    if st.button("Laden"):
        # Laden nur, wenn ein Eintrag ausgewählt ist
        if selected == "(keine)":
            st.sidebar.warning("Bitte einen Eintrag auswählen.")
        else:
            try:
                doc_id = int(selected.split("|")[0].strip().lstrip("#"))
                record = db.load_simulation(doc_id)

                # Simulation aus Record wiederherstellen
                if not hasattr(Simulation, "from_record_dict"):
                    st.sidebar.error("Simulation.from_record_dict(...) fehlt in main.py")
                else:
                    sim = Simulation.from_record_dict(record)

                    st.session_state.sim = sim
                    st.session_state.ran = True
                    st.session_state.loaded_doc_id = doc_id

                    st.sidebar.success(f"Geladen: #{doc_id}")

            except Exception as e:
                st.sidebar.error(f"Laden fehlgeschlagen: {e}")

with colC:
    if st.button("Fortsetzen"):
        # Fortsetzen nur, wenn Simulation vorhanden
        if st.session_state.sim is None:
            st.sidebar.warning("Keine Simulation geladen/gestartet.")
        else:
            try:
                # Fortsetzen, falls implementiert – sonst fallback auf run()
                if hasattr(st.session_state.sim, "resume"):
                    st.session_state.sim.resume(max_iters=None)
                else:
                    # Fallback: startet neu (nicht ideal, aber verhindert Crash)
                    st.session_state.sim.run()

                st.session_state.ran = True
                st.sidebar.success("Optimierung fortgesetzt.")
            except Exception as e:
                st.sidebar.error(f"Fortsetzen fehlgeschlagen: {e}")

# ------------------------------------------------------------
# SIMULATION STARTEN (wie bisher)
# ------------------------------------------------------------
if st.button("Simulation starten"):
    # Neue Simulation erzeugen + komplett laufen lassen
    sim = Simulation(nx, ny, mass_frac, load_ix, load_iy, Fx, Fy)
    sim.run()

    # Im Session State speichern
    st.session_state.sim = sim
    st.session_state.ran = True
    st.session_state.loaded_doc_id = None

# ------------------------------------------------------------
# AUSGABE (nur wenn Simulation bereits lief)
# ------------------------------------------------------------
if st.session_state.ran and st.session_state.sim is not None:
    sim = st.session_state.sim

    # Einheitliches Nodeset für "Original" (alle Knoten)
    all_nodes = set(range(sim.grid.n_nodes))

    st.subheader("Originalstruktur")
    fig_original = sim.plot_structure(
        u=None,
        remaining_nodes=all_nodes,
        scale=1.0
    )
    st.pyplot(fig_original)

    # Optimierungsschritte
    st.subheader("Optimierungs-Schritte")

    if hasattr(sim, "optim_steps") and sim.optim_steps is not None and len(sim.optim_steps) > 0:
        max_step = len(sim.optim_steps) - 1

        step = st.slider(
            "Schritt wählen",
            min_value=0,
            max_value=max_step,
            value=max_step,
            step=1,
        )

        remaining_nodes_step = sim.optim_steps[step]

        fig_step = sim.plot_structure(
            u=None,
            remaining_nodes=remaining_nodes_step,
            scale=1.0
        )
        st.pyplot(fig_step)
    else:
        st.write("Keine Optimierungsschritte vorhanden.")

    # Verformte Struktur
    st.subheader("Verformte Struktur")

    scale = st.slider(
        "Verformung skalieren",
        min_value=0.01,
        max_value=1.0,
        value=0.1,
        step=0.01
    )

    # Falls remaining_nodes noch nicht existiert (z.B. bei alten Ständen), fallback auf all_nodes
    remaining_nodes_for_plot = sim.remaining_nodes if hasattr(sim, "remaining_nodes") else all_nodes

    fig_deformed = sim.plot_structure(
        u=getattr(sim, "u", None),
        remaining_nodes=remaining_nodes_for_plot,
        scale=scale
    )
    st.pyplot(fig_deformed)
    