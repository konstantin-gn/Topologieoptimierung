import streamlit as st

from main import Simulation
from plotter import StreamlitPlotter


st.title("2D Topologieoptimierung")

st.sidebar.header("Parameter")

nx = st.sidebar.slider("Breite (nx)", 5, 30, 15)
ny = st.sidebar.slider("Höhe (ny)", 3, 15, 6)

mass = st.sidebar.slider("Masse (%)", 10, 100, 40)

load_x = st.sidebar.slider("Last x", 0, nx-1, nx//2)
load_y = st.sidebar.slider("Last y", 0, ny-1, ny-1)

Fx = st.sidebar.number_input("Fx", value=0.0)
Fy = st.sidebar.number_input("Fy", value=-1.0)


if st.button("Optimierung starten"):

    sim = Simulation(
        nx,
        ny,
        mass/100,
        load_x,
        load_y,
        Fx,
        Fy
    )

    active_nodes, u, grid = sim.run()

    plotter = StreamlitPlotter(grid)

    st.subheader("Optimierte Struktur")

    fig1 = plotter.plot_structure(active_nodes)

    st.pyplot(fig1)


    st.subheader("Verformung")

    fig2 = plotter.plot_deformation(active_nodes, u, scale=5)

    st.pyplot(fig2)