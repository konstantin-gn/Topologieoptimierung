import streamlit as st
import matplotlib.pyplot as plt

from main import Simulation


st.title("2D Topologieoptimierung")

st.sidebar.header("Struktur")

nx = st.sidebar.number_input("Breite (Knoten)", 2, 100, 10)
ny = st.sidebar.number_input("Höhe (Knoten)", 2, 100, 4)

mass_frac = st.sidebar.slider("Verbleibende Masse (%)", 1, 100, 40) / 100.0


st.sidebar.header("Kraft")

load_ix = st.sidebar.number_input("Knoten x", 0, nx - 1, 0)
load_iy = st.sidebar.number_input("Knoten y", 0, ny - 1, 0)

Fx = st.sidebar.number_input("Fx", value=0.0)
Fy = st.sidebar.number_input("Fy", value=0.0)


if st.button("Simulation starten"):

    sim = Simulation(
        nx,
        ny,
        mass_frac,
        load_ix,
        load_iy,
        Fx,
        Fy,
    )

    sim.run()

    st.subheader("Ausgangsstruktur")
    fig1 = sim.plot_structure()
    st.pyplot(fig1)

    st.subheader("Optimierte Struktur")
    fig2 = sim.plot_structure(remaining_nodes=sim.remaining_nodes)
    st.pyplot(fig2)

    st.subheader("Verformung")
    fig3 = sim.plot_structure(u=sim.u, scale=10, remaining_nodes=sim.remaining_nodes)
    st.pyplot(fig3)