import streamlit as st

from main import Simulation
from plotter import StreamlitPlotter


st.title("2D Topologieoptimierung")


<<<<<<< HEAD
# --- Sidebar Inputs ---
st.sidebar.header("Struktur")
=======
# Session State initialisieren
# Speichert Simulation dauerhaft zwischen Interaktionen
if "sim" not in st.session_state:
    st.session_state.sim = None

if "ran" not in st.session_state:
    st.session_state.ran = False


# SIDEBAR INPUTS
st.sidebar.header("Struktur: Settings")

>>>>>>> überarbeitung-optimierung
nx = st.sidebar.number_input("Breite (Knoten)", 2, 100, 10)
ny = st.sidebar.number_input("Höhe (Knoten)", 2, 100, 4)
mass_frac = st.sidebar.slider("Verbleibende Masse (%)", 1, 100, 40) / 100.0

st.sidebar.header("Kraft")
load_ix = st.sidebar.number_input("Knoten x", 0, nx - 1, 0)
load_iy = st.sidebar.number_input("Knoten y", 0, ny - 1, 0)
Fx = st.sidebar.number_input("Fx", value=0)
Fy = st.sidebar.number_input("Fy", value=0)

# --- Simulation starten ---
if st.button("Simulation starten"):
    sim = Simulation(nx, ny, mass_frac, load_ix, load_iy, Fx, Fy)
    sim.run()

    # --- Ganze Struktur plotten ---
    fig_full = sim.plot_structure(u=sim.u, remaining_nodes=sim.remaining_nodes)
    st.pyplot(fig_full)

<<<<<<< HEAD
    # --- Optimierungsschritte ---
=======

# AUSGABE (nur wenn Simulation bereits lief)
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
>>>>>>> überarbeitung-optimierung
    st.subheader("Optimierungs-Schritte")
    if hasattr(sim, "optim_steps") and len(sim.optim_steps) > 0:
        max_step = len(sim.optim_steps) - 1
        step = st.slider(
            "Schritt wählen",
            min_value=0,
            max_value=max_step,
            value=max_step,
            step=1,
        )
        remaining_nodes_step = sim.optim_steps[step]
        fig_step = sim.plot_nodes(remaining_nodes_step, u=sim.u)
        st.pyplot(fig_step)
    else:
        st.write("Keine Optimierungsschritte vorhanden.")

<<<<<<< HEAD
    # --- Verformte Struktur (letzter Schritt) ---
    st.subheader("Verformte Struktur (letzter Schritt)")
    fig2 = sim.plot_nodes(sim.remaining_nodes, u=sim.u, scale=10)
    st.pyplot(fig2)
=======
    # VERFORMTE STRUKTUR 
    st.subheader("Verformte Struktur")

    scale = st.slider(
        "Verformung skalieren",
        min_value=0.01,
        max_value=1.0,
        value=0.1,
        step=0.01
    )

    fig_deformed = sim.plot_structure(
        u=sim.u,
        remaining_nodes=sim.remaining_nodes,
        scale=scale
    )
    st.pyplot(fig_deformed)
>>>>>>> überarbeitung-optimierung
