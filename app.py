import streamlit as st
from main import Simulation

st.title("2D Topologieoptimierung")

# Session State initialisieren
# Speichert Simulation dauerhaft zwischen Interaktionen
if "sim" not in st.session_state:
    st.session_state.sim = None

if "ran" not in st.session_state:
    st.session_state.ran = False


# SIDEBAR INPUTS
st.sidebar.header("Struktur")

nx = st.sidebar.number_input("Breite (Knoten)", 2, 100, 10)
ny = st.sidebar.number_input("Höhe (Knoten)", 2, 100, 4)
mass_frac = st.sidebar.slider("Verbleibende Masse (%)", 1, 100, 40) / 100.0

st.sidebar.header("Kraft")

load_ix = st.sidebar.number_input("Knoten x", 0, nx - 1, 0)
load_iy = st.sidebar.number_input("Knoten y", 0, ny - 1, 0)
Fx = st.sidebar.number_input("Fx", value=0.0)
Fy = st.sidebar.number_input("Fy", value=0.0)


# SIMULATION STARTEN
if st.button("Simulation starten"):
    # Neue Simulation erzeugen
    sim = Simulation(nx, ny, mass_frac, load_ix, load_iy, Fx, Fy)
    sim.run()

    # Im Session State speichern
    st.session_state.sim = sim
    st.session_state.ran = True



# AUSGABE (nur wenn Simulation bereits lief)
if st.session_state.ran and st.session_state.sim is not None:

    sim = st.session_state.sim

    st.subheader("Originalstruktur")

    # ORIGINALSTRUKTUR (keine Verformung)
    fig_original = sim.plot_structure(
        u=None,
        remaining_nodes=sim.optim_steps[0] if len(sim.optim_steps) > 0 else sim.remaining_nodes
    )

    st.pyplot(fig_original)


    # OPTIMIERUNGSSCHRITTE
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

        fig_step = sim.plot_nodes(
            remaining_nodes_step,
            u=None
        )

        st.pyplot(fig_step)

    else:
        st.write("Keine Optimierungsschritte vorhanden.")

    
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
        u=sim.u,                     # <-- Verschiebung übergeben
        remaining_nodes=sim.remaining_nodes,
        scale=scale                  # <-- Skalierung
    )

    st.pyplot(fig_deformed)
