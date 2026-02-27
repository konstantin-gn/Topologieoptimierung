import streamlit as st
from main import Simulation
from db_connector import DBConnector
import io
import matplotlib.pyplot as plt
import pandas as pd

st.title("2D Topologieoptimierung")


# Session State Defaults und Initialisierung
defaults = {
    "sim": None,
    "ran": False,
    "loaded_doc_id": None,
    # aktiver Run (wird beim Laden gesetzt)
    "current_label": None,
    # UI-Werte (Anfangswerte)
    "nx": 31,
    "ny": 10,
    "mass_pct": 40,
    "load_ix": 15,
    "load_iy": 0,
    "Fx": 0.0,
    "Fy": 1.0,
    # temporärer Speicher für geladene Werte (damit Slider/Inputs korrekt springen)
    "pending_record": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# wenn pending_record gesetzt ist, dann Werte daraus in Session State übertragen (z.B. nach Laden eines Runs)
if st.session_state.pending_record is not None:
    record = st.session_state.pending_record

    # Werte in Session State übertragen (damit Slider/Inputs korrekt springen)
    st.session_state.nx = int(record["nx"])
    st.session_state.ny = int(record["ny"])
    st.session_state.mass_pct = int(round(float(record["target_mass_frac"]) * 100))

    st.session_state.load_ix = int(record["load_ix"])
    st.session_state.load_iy = int(record["load_iy"])
    st.session_state.Fx = float(record["Fx"])
    st.session_state.Fy = float(record["Fy"])

    # clamp damit Werte im gültigen Bereich bleiben (z.B. wenn nx/ny kleiner geworden sind)
    st.session_state.load_ix = min(st.session_state.load_ix, st.session_state.nx - 1)
    st.session_state.load_iy = min(st.session_state.load_iy, st.session_state.ny - 1)

    st.session_state.pending_record = None

# DB Connector initialisieren
db = DBConnector("db.json")


# Seitenleiste mit Eingaben und Buttons
st.sidebar.header("Struktur: Settings")

nx = st.sidebar.number_input("Breite (Knoten)", 2, 100, key="nx")
ny = st.sidebar.number_input("Höhe (Knoten)", 2, 100, key="ny")

mass_frac = st.sidebar.slider("Verbleibende Masse (%)", 1, 100, key="mass_pct") / 100.0

st.sidebar.header("Kraft")

# clamp damit Werte im gültigen Bereich bleiben (z.B. wenn nx/ny kleiner geworden sind)
st.session_state.load_ix = min(int(st.session_state.load_ix), int(nx) - 1)
st.session_state.load_iy = min(int(st.session_state.load_iy), int(ny) - 1)

load_ix = st.sidebar.number_input("Knoten x", 0, int(nx) - 1, key="load_ix")
load_iy = st.sidebar.number_input("Knoten y", 0, int(ny) - 1, key="load_iy")

Fx = st.sidebar.number_input("Fx", key="Fx")
Fy = st.sidebar.number_input("Fy", key="Fy")

# Speichern/Laden Bereich
st.sidebar.header("Speichern / Laden")

saved = db.list_simulations()
options = ["(keine)"] + [
    f'#{r["doc_id"]} | {r["label"]} | {r["created_at"]} | finished={r["finished"]}'
    for r in saved
]
selected = st.sidebar.selectbox("Gespeicherte Simulationen", options, index=0)

# Name: wenn ein Run geladen ist, zeige den aktuellen Namen, sonst "new run"
default_name = st.session_state.current_label or "new run"
save_label = st.sidebar.text_input("Name", value=default_name)

# Speichern = Update (überschreibt bestehenden Run)
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


# Neu speichern = Save as-funktion (nur wenn Name noch nicht existiert)-
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

# Laden eines bestehenden Runs
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

            # UI-Werte in pending_record packen, damit sie nach dem Rerun in die Inputs/Slider übertragen werden
            st.session_state.pending_record = record
            st.rerun()

        except Exception as e:
            st.sidebar.error(f"Laden fehlgeschlagen: {e}")

# Löschen (aktuellen Dropdown-Run löschen)

if st.sidebar.button("Löschen"):
    if selected == "(keine)":
        st.sidebar.warning("Bitte einen Eintrag auswählen.")
    else:
        try:
            doc_id = int(selected.split("|")[0].strip().lstrip("#"))

            # löschen
            db.delete_by_doc_id(doc_id)

            # Falls der gelöschte Run gerade aktiv war -> State zurücksetzen
            if st.session_state.loaded_doc_id == doc_id:
                st.session_state.sim = None
                st.session_state.ran = False
                st.session_state.loaded_doc_id = None
                st.session_state.current_label = None

            st.sidebar.success(f"Run #{doc_id} gelöscht.")
            st.rerun()

        except Exception as e:
            st.sidebar.error(f"Löschen fehlgeschlagen: {e}")

# Simulation starten (neuer Run -> current_label reset)
if st.button("Simulation starten"):
    sim = Simulation(nx, ny, mass_frac, load_ix, load_iy, Fx, Fy)
    sim.run()

    st.session_state.sim = sim
    st.session_state.ran = True
    st.session_state.loaded_doc_id = None

    # neuer Run -> nicht an alten Namen gebunden
    st.session_state.current_label = None

# Ausgabe/Plots der Simulationsergebnisse
if st.session_state.ran and st.session_state.sim is not None:
    sim = st.session_state.sim

    # Statusanzeige
    if st.session_state.current_label:
        st.caption(f"Aktive Simulation: **{st.session_state.current_label}**")
    else:
        st.caption("Aktive Simulation: (noch nicht gespeichert)")

    all_nodes = set(range(sim.grid.n_nodes))

    # Originalstruktur (unverformt, alle Knoten)
    st.subheader("Originalstruktur")
    fig_original = sim.plot_structure(u=None, remaining_nodes=all_nodes, scale=1.0)
    ax = fig_original.axes[0]
    ax.set_title("Ausgangsstruktur")
    st.pyplot(fig_original)
    plt.close(fig_original)

    # Optimierungsschritte (wenn vorhanden)
    st.subheader("Optimierungs-Schritte")
    if hasattr(sim, "optim_steps") and sim.optim_steps and len(sim.optim_steps) > 0:
        max_step = len(sim.optim_steps) - 1
        step = st.slider("Schritt wählen", 0, max_step, max_step, 1)
        remaining_nodes_step = sim.optim_steps[step]
        progress_pct = int((step / max_step) * 100)  # Prozentualer Fortschritt
        fig_step = sim.plot_structure(
            u=None, remaining_nodes=remaining_nodes_step, scale=1.0
        )
        st.pyplot(fig_step)
        plt.close(fig_step)

        # Download-Button für letzte optimierte Struktur
        final_nodes = sim.optim_steps[-1]
        fig_opt = sim.plot_structure(u=None, remaining_nodes=final_nodes, scale=1.0)
        ax_opt = fig_opt.axes[0]
        ax_opt.set_title("Optimierte Struktur (100 %)")  # Titel nur hier
        buf_opt = io.BytesIO()
        fig_opt.savefig(buf_opt, format="png", dpi=300, bbox_inches="tight")
        buf_opt.seek(0)
        st.download_button(
            label="Optimierte Struktur herunterladen (unverformt)",
            data=buf_opt,
            file_name="optimierte_struktur.png",
            mime="image/png",
        )
        st.pyplot(fig_opt)
        plt.close(fig_opt)

    else:
        st.write("Keine Optimierungsschritte vorhanden.")

    # Heatmap der Knoteneenergie
    st.subheader("Knotenenergie Heatmap")

    fig_heatmap = sim.plot_energy_heatmap()

    if fig_heatmap is not None:
        st.pyplot(fig_heatmap)
        plt.close(fig_heatmap)
    else:
        st.write("Keine Energie-Daten vorhanden.")

    st.subheader("Lastpfade (Kraftfluss)")

    # Slider für Filterstärke
    threshold = st.slider(
        "Lastpfad Filter (höher = nur starke Pfade sichtbar)", 0.0, 0.2, 0.05, 0.01
    )

    # Plot mit Threshold
    fig_load = sim.plot_load_paths(threshold)

    if fig_load is not None:
        st.pyplot(fig_load)
        plt.close(fig_load)
    else:
        st.write("Keine Lastpfade verfügbar.")

    # Verformte Struktur (wenn vorhanden)
    st.subheader("Verformte Struktur")

    scale = st.slider("Verformung skalieren", 0.01, 1.0, 0.1, 0.01)

    remaining_nodes_for_plot = getattr(sim, "remaining_nodes", None)
    if remaining_nodes_for_plot is None:
        remaining_nodes_for_plot = all_nodes

    fig_deformed = sim.plot_structure(
        u=getattr(sim, "u", None), remaining_nodes=remaining_nodes_for_plot, scale=scale
    )
    st.pyplot(fig_deformed)
    plt.close(fig_deformed)

    # Finaler Report
    st.subheader("Finaler Report")

    report = sim.compute_report()

    if report is not None:

        st.write(
            f"Verbleibende Knoten: {report['remaining_nodes']} / {report['total_nodes']}"
        )
        st.write(f"Verbleibende Masse: {report['mass_percent']:.1f} %")

        st.write(f"Maximale Verschiebung: {report['max_displacement']:.6f}")
        st.write(f"Mittlere Verschiebung: {report['mean_displacement']:.6f}")

        st.write(f"Compliance: {report['compliance']:.6f}")
        st.write(f"Gesamtenergie: {report['energy']:.6f}")

        # Textfile erzeugen
        report_text = f"""
    TOPOLOGIEOPTIMIERUNG REPORT

    Verbleibende Knoten:   {report['remaining_nodes']} / {report['total_nodes']}
    Verbleibende Masse:    {report['mass_percent']:.1f} %

    Maximale Verschiebung: {report['max_displacement']:.6f}
    Mittlere Verschiebung: {report['mean_displacement']:.6f}

    Compliance:            {report['compliance']:.6f}
    Gesamtenergie:         {report['energy']:.6f}
    """

        st.download_button("Report herunterladen", report_text, file_name="report.txt")

    else:
        st.write("Kein Report verfügbar.")

    # Kennzahlen über Iterationen plotten
    st.subheader("Kennzahlen über Iterationen")

    df = pd.DataFrame(sim.history).set_index("iter")

    st.write("Verbleibende Masse")
    st.line_chart(df["mass_frac"])

    st.write("Max. Verformung (Indikator)")
    st.line_chart(df["max_u"])

    st.write("Compliance (Fᵀu)")
    st.line_chart(df["compliance"])

    st.write("Anzahl Knoten / Federn")
    st.line_chart(df[["n_nodes", "n_springs"]])
