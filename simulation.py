import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

from grid import MakeGrid
from solver import LinearSolver

# Simulation-Objekt mit Run- und Resume-Funktion sowie Save/Load für DB
class Simulation:

    # Initialisierung mit Parametern
    def __init__(self, nx, ny, target_mass_frac, load_ix, load_iy, Fx, Fy):
        self.grid = MakeGrid(nx, ny)
        self.solver = LinearSolver()

        self.target_mass_frac = float(target_mass_frac)
        self.load_ix = int(load_ix)
        self.load_iy = int(load_iy)
        self.Fx = float(Fx)
        self.Fy = float(Fy)

        self.optim_steps: list[set[int]] = []

        # Historie für Plot 
        self.history = {
            "iter": [],
            "mass_frac": [],
            "max_u": [],
            "compliance": [],
            "n_nodes": [],
            "n_springs": [],
        }

        # Zustandsfelder für Save/Load/Fortsetzen
        self._initialized = False
        self.F: np.ndarray | None = None
        self.u_fixed_idx: list[int] | None = None

        self.load_node:  int | None = None
        self.node_fixed: int | None = None
        self.node_lose:  int | None = None

        self.protected_nodes: set[int] | None = None
        self.support_nodes:   set[int] | None = None

        self.remaining_nodes:    set[int] | None = None
        self.remaining_elements: set[int] | None = None

        self.u: np.ndarray | None = None  # aktueller Verschiebungsvektor (für Plot)

    # Initialisierung 
    # baut die Startstruktur auf (F, Lager, Schutzknoten, remaining sets) und wird bei run() und resume() genutzt.
    def initialize_state(self) -> None:

        if self._initialized:
            return

        # Kraftvektor
        F = np.zeros(self.grid.ndof)
        load_node = self.grid.node_id(self.load_ix, self.load_iy)
        F[2 * load_node] = self.Fx
        F[2 * load_node + 1] = self.Fy

        # Randbedingungen (Lager)
        u_fixed_idx: list[int] = []

        node_fixed = self.grid.node_id(0, self.grid.ny - 1)
        u_fixed_idx.extend([2 * node_fixed, 2 * node_fixed + 1])

        node_lose = self.grid.node_id(self.grid.nx - 1, self.grid.ny - 1)
        u_fixed_idx.append(2 * node_lose + 1)

        # Start: alles vorhanden
        remaining_nodes = set(range(self.grid.n_nodes))
        remaining_elements = set(range(len(self.grid.elements)))

        # Schutz: Last- und Lagerknoten dürfen nicht entfernt werden
        protected_nodes = {load_node, node_fixed, node_lose}
        support_nodes = {node_fixed, node_lose}

        # Schritte speichern
        self.optim_steps = [remaining_nodes.copy()]

        # initiale Lösung (hilft nach Laden, damit u nicht None ist)
        u0 = self.solver.solve(self.grid.K_global, F, u_fixed_idx)
        if u0 is None:
            u0 = np.zeros(self.grid.ndof)

        # speichern
        self.F = F
        self.u_fixed_idx = u_fixed_idx
        self.load_node = load_node
        self.node_fixed = node_fixed
        self.node_lose = node_lose
        self.protected_nodes = protected_nodes
        self.support_nodes = support_nodes
        self.remaining_nodes = remaining_nodes
        self.remaining_elements = remaining_elements
        self.u = u0

        self._initialized = True


    # Start neu
    def run(self) -> None:
        """
        Startet neu (setzt Zustand zurück) und optimiert vollständig.
        """
        self._initialized = False
        self.initialize_state()

        # Anfangsenergie ausgeben (wie zuvor)
        u_start = self.solver.solve(self.grid.K_global, self.F, self.u_fixed_idx)
        if u_start is None:
            print("System konnte nicht gelöst werden.")
            return

        total_energy = 0.5 * u_start.T @ self.grid.K_global @ u_start
        print("Total energy:", total_energy)

        # optional: debug-energy-matrix
        self._compute_node_energy(u_start)

        # Optimierung ausführen
        self._optimization_loop(max_tries=50, cond_max=1e8, max_iters=None)

    
    # Speichert Kennzahlen der aktuellen Iteration in self.history (für Plot)
    def _log_iteration(self, it: int, K, F, u) -> None:
        
        # Anteil verbleibender Knoten 
        n_total = self.grid.n_nodes
        n_nodes = len(self.remaining_nodes) if self.remaining_nodes is not None else n_total
        mass_frac = n_nodes / max(1, n_total)

        # Max. Verformung
        max_u = float(np.linalg.norm(u))

        # Compliance (Weichheit)
        compliance = float(F @ u)

        # Federn: Anzahl verbleibender Elemente 
        n_springs = len(self.remaining_elements) if self.remaining_elements is not None else len(self.grid.elements)

        # Log speichern 
        self.history["iter"].append(it)
        self.history["mass_frac"].append(mass_frac)
        self.history["max_u"].append(max_u)
        self.history["compliance"].append(compliance)
        self.history["n_nodes"].append(n_nodes)
        self.history["n_springs"].append(n_springs)

    # Fortsetzen
    def resume(self, max_iters: int | None = None) -> None:
        """
        Setzt Optimierung ab aktuellem Stand fort.
        max_iters optional, um nur N Schritte weiterzumachen.
        """
        self.initialize_state()
        self._optimization_loop(max_tries=50, cond_max=1e8, max_iters=max_iters)


    # Kernschleife 
    # führt die iterative Knoten-Entfernung durch
    # sortiert die Kandidaten nach Energie (wie bisher) und prüft Konnektivität, Lastpfad und mechanische Stabilität
    def _optimization_loop(self, max_tries: int, cond_max: float, max_iters: int | None):
       
        assert self.F is not None
        assert self.u_fixed_idx is not None
        assert self.load_node is not None
        assert self.protected_nodes is not None
        assert self.support_nodes is not None
        assert self.remaining_nodes is not None
        assert self.remaining_elements is not None

        n_nodes_target = int(self.grid.n_nodes * self.target_mass_frac)

        iters = 0

        while len(self.remaining_nodes) > n_nodes_target:

            if max_iters is not None and iters >= max_iters:
                break

            # K aus aktuellen Elementen assembeln
            K_iter = self._assemble_K_for_elements(self.remaining_elements)

            # entfernte Knoten als u=0 fixieren
            removed_nodes = set(range(self.grid.n_nodes)) - self.remaining_nodes
            u_fixed_idx_iter = list(self.u_fixed_idx)
            for n in removed_nodes:
                u_fixed_idx_iter += [2 * n, 2 * n + 1]
            u_fixed_idx_iter = sorted(set(u_fixed_idx_iter))

            # Solve für aktuelle Struktur
            u_iter = self.solver.solve(K_iter, self.F, u_fixed_idx_iter)
            if u_iter is None:
                print("Iteration abgebrochen: aktuelle Struktur ist nicht lösbar (singulär/mechanismus).")
                break

            self.u = u_iter  # für Plot

            self._log_iteration(iters, K_iter, self.F, u_iter)  # Kennzahlen loggen

            # Energien für aktuelle Struktur
            node_energy = self._compute_node_energy_subset(u_iter, self.remaining_elements)

            # Kandidaten-Maske
            energy_masked = node_energy.copy()
            for n in self.protected_nodes:
                energy_masked[n] = np.inf
            for n in removed_nodes:
                energy_masked[n] = np.inf

            if not np.isfinite(np.min(energy_masked)):
                print("Keine entfernbaren Knoten mehr gefunden.")
                break

            accepted = False
            tries = 0

            while tries < max_tries:
                candidate = int(np.argmin(energy_masked))
                if not np.isfinite(energy_masked[candidate]):
                    break

                trial_nodes = self.remaining_nodes - {candidate}

                ok_connected = self._is_connected(trial_nodes)
                ok_loadpath = self._has_load_path_to_supports(trial_nodes, self.load_node, self.support_nodes)

                if ok_connected and ok_loadpath:

                    trial_elements = {
                        idx
                        for idx, (i, j, _, _) in enumerate(self.grid.elements)
                        if i in trial_nodes and j in trial_nodes
                    }

                    K_trial = self._assemble_K_for_elements(trial_elements)

                    removed_trial = set(range(self.grid.n_nodes)) - trial_nodes
                    u_fixed_idx_trial = list(self.u_fixed_idx)
                    for n in removed_trial:
                        u_fixed_idx_trial += [2 * n, 2 * n + 1]
                    u_fixed_idx_trial = sorted(set(u_fixed_idx_trial))

                    ok_mech = self._is_mechanically_stable(K_trial, u_fixed_idx_trial, cond_max=cond_max)

                    if ok_mech:
                        self.remaining_nodes = trial_nodes
                        self.remaining_elements = trial_elements
                        self.optim_steps.append(self.remaining_nodes.copy())
                        accepted = True
                        break

                # Kandidat sperren
                energy_masked[candidate] = np.inf
                tries += 1

            if not accepted:
                print("Keine gültige Knoten-Entfernung in dieser Iteration gefunden.")
                break

            iters += 1

        # Lösung für Plot: nochmal auf finaler Struktur lösen
        K_opt = self._assemble_K_for_elements(self.remaining_elements)

        removed_nodes = set(range(self.grid.n_nodes)) - self.remaining_nodes
        u_fixed_idx_opt = list(self.u_fixed_idx)
        for n in removed_nodes:
            u_fixed_idx_opt += [2 * n, 2 * n + 1]
        u_fixed_idx_opt = sorted(set(u_fixed_idx_opt))

        u_opt = self.solver.solve(K_opt, self.F, u_fixed_idx_opt)
        self.u = u_opt if u_opt is not None else np.zeros(self.grid.ndof)

        # Konsolen-Ausgabe 
        topology_vector = np.zeros(self.grid.n_nodes)
        for node in self.remaining_nodes:
            topology_vector[node] = 1
        topology_matrix = topology_vector.reshape((self.grid.ny, self.grid.nx))

        print(f"\nOptimierungsziel: {self.target_mass_frac*100:.0f}% der Ausgangsknoten")
        print("Knoten, die im optimierten Balken verbleiben:")
        print(sorted(list(self.remaining_nodes)))

        print("\nTopologie-Matrix (1 = behalten, 0 = gelöscht):")
        for row in topology_matrix:
            print("  ".join(str(int(val)) for val in row))


    # Save/Load 
    # exportiert alle relevanten Informationen in ein JSON-kompatibles Dict 
    # sets -> lists, numpy arrays -> lists
    def to_record_dict(self, label: str) -> dict:
        
        self.initialize_state()

        def s2l(s: set[int] | None) -> list[int]:
            return sorted(list(s)) if s is not None else []

        return {
            "label": label,

            # Parameter
            "nx": self.grid.nx,
            "ny": self.grid.ny,
            "target_mass_frac": float(self.target_mass_frac),
            "load_ix": int(self.load_ix),
            "load_iy": int(self.load_iy),
            "Fx": float(self.Fx),
            "Fy": float(self.Fy),

            # Zustand
            "remaining_nodes": s2l(self.remaining_nodes),
            "remaining_elements": s2l(self.remaining_elements),
            "optim_steps": [sorted(list(step)) for step in (self.optim_steps or [])],
            "u": self.u.tolist() if self.u is not None else None,

            # Status
            "finished": bool(len(self.remaining_nodes) <= int(self.grid.n_nodes * self.target_mass_frac)),
        }

    # Baut Simulation aus DB-Daten wieder auf.
    @staticmethod
    def from_record_dict(record: dict) -> "Simulation":
        
        sim = Simulation(
            record["nx"],
            record["ny"],
            record["target_mass_frac"],
            record["load_ix"],
            record["load_iy"],
            record["Fx"],
            record["Fy"],
        )

        # Basis initialisieren (F, Lager, etc.)
        sim.initialize_state()

        # Zustand setzen
        sim.remaining_nodes = set(record.get("remaining_nodes", []))
        sim.remaining_elements = set(record.get("remaining_elements", []))
        sim.optim_steps = [set(step) for step in record.get("optim_steps", [])]

        u_list = record.get("u", None)
        if u_list is not None:
            sim.u = np.array(u_list, dtype=float)

        sim._initialized = True
        return sim

    # Berechnet die Energiebeiträge für alle Knoten basierend auf den aktuellen Verschiebungen u
    def _compute_node_energy(self, u):
        node_energy = np.zeros(self.grid.n_nodes)

        for i, j, K_elem, dofs in self.grid.elements:
            u_e = u[dofs]
            c_e = 0.5 * u_e.T @ K_elem @ u_e
            node_energy[i] += 0.5 * c_e
            node_energy[j] += 0.5 * c_e

        node_energy_matrix = node_energy.reshape((self.grid.ny, self.grid.nx))
        print("\nNode energy matrix:")
        for row in node_energy_matrix:
            print("  ".join(f"{val:.6f}" for val in row))

        return node_energy

    # Berechnet die Energiebeiträge für eine Teilmenge von Elementen 
    def _compute_node_energy_subset(self, u: np.ndarray, remaining_elements: set[int]) -> np.ndarray:
        node_energy = np.zeros(self.grid.n_nodes, dtype=float)

        for idx in remaining_elements:
            i, j, K_elem, dofs = self.grid.elements[idx]
            u_e = u[dofs]
            c_e = 0.5 * u_e.T @ K_elem @ u_e
            node_energy[i] += 0.5 * c_e
            node_energy[j] += 0.5 * c_e

        return node_energy
    
    # Prüft, ob die verbleibenden Knoten eine zusammenhängende Struktur bilden.
    def _is_connected(self, allowed_nodes):
        valid_edges = [
            (i, j)
            for (i, j) in self.grid.edge_list
            if i in allowed_nodes and j in allowed_nodes
        ]

        if len(valid_edges) == 0:
            return False

        G = nx.Graph()
        G.add_nodes_from(allowed_nodes)
        G.add_edges_from(valid_edges)

        return nx.is_connected(G)

    # Prüft, ob es einen Pfad von der Last zu mindestens einem der Stützpunkte gibt (Lastpfad).
    def _has_load_path_to_supports(self, allowed_nodes: set[int], load_node: int, support_nodes: set[int]) -> bool:
        if load_node not in allowed_nodes:
            return False

        valid_edges = [
            (i, j)
            for (i, j) in self.grid.edge_list
            if i in allowed_nodes and j in allowed_nodes
        ]

        if len(valid_edges) == 0:
            return False

        G = nx.Graph()
        G.add_nodes_from(allowed_nodes)
        G.add_edges_from(valid_edges)

        for s in support_nodes:
            if s in allowed_nodes and nx.has_path(G, load_node, s):
                return True

        return False
    
    # Baut die globale Steifigkeitsmatrix K aus den Elementmatrizen der verbleibenden Elemente zusammen.
    def _assemble_K_for_elements(self, remaining_elements: set[int]) -> np.ndarray:
        K = np.zeros((self.grid.ndof, self.grid.ndof), dtype=float)

        for idx in remaining_elements:
            i, j, K_elem, dofs = self.grid.elements[idx]
            for a in range(4):
                for b in range(4):
                    K[dofs[a], dofs[b]] += K_elem[a, b]

        return K

    # Prüft, ob die Struktur mit den gegebenen Randbedingungen mechanisch stabil (keine Einzelstäbe) ist.
    def _is_mechanically_stable(self, K, u_fixed_idx, cond_max=1e8):
        ndof = K.shape[0]

        fixed = np.zeros(ndof, dtype=bool)
        fixed[u_fixed_idx] = True
        free_idx = np.where(~fixed)[0]

        if len(free_idx) < 2:
            return False

        K_ff = K[np.ix_(free_idx, free_idx)]

        try:
            c = np.linalg.cond(K_ff)
        except np.linalg.LinAlgError:
            return False

        return np.isfinite(c) and (c < cond_max)

    # Visualisierung/Plot
    def plot_structure(self, u=None, scale=1.0, remaining_nodes=None):
        fig, ax = plt.subplots()

        if remaining_nodes is None:
            remaining_nodes = set(range(self.grid.n_nodes))

        edges = []
        for (i, j, _, _) in self.grid.elements:
            if i in remaining_nodes and j in remaining_nodes:
                edges.append((i, j))

        for (i, j) in edges:
            x1 = i % self.grid.nx
            y1 = i // self.grid.nx
            x2 = j % self.grid.nx
            y2 = j // self.grid.nx

            if u is not None:
                x1 += scale * u[2 * i]
                y1 += scale * u[2 * i + 1]
                x2 += scale * u[2 * j]
                y2 += scale * u[2 * j + 1]

            ax.plot([x1, x2], [y1, y2], "k-")

        ax.set_aspect("equal")
        ax.invert_yaxis()
        ax.set_title("Struktur")
        return fig
    
    # Erweiterung 1: Heatmap der Knotenenergien
    def plot_energy_heatmap(self):
        if self.u is None or self.remaining_elements is None:
            return None

        node_energy = self._compute_node_energy_subset(
            self.u,
            self.remaining_elements
        )

        energy_matrix = node_energy.reshape(
            (self.grid.ny, self.grid.nx)
        )

        fig, ax = plt.subplots()

        im = ax.imshow(
            energy_matrix,
            origin="upper",
            cmap="jet"
        )

        plt.colorbar(im, ax=ax, label="Knotenenergie")

        ax.set_title("Knotenenergie Heatmap")
        ax.set_xlabel("x")
        ax.set_ylabel("y")

        return fig
    
    # Erweiterung 2: Finaler Report mit Kennzahlen zur aktuellen Struktur
    def compute_report(self):
        if self.u is None or self.remaining_nodes is None:
            return None

        total_nodes = self.grid.n_nodes
        remaining_nodes = len(self.remaining_nodes)

        mass_frac = remaining_nodes / total_nodes * 100

        # Verschiebungen berechnen
        ux = self.u[0::2]
        uy = self.u[1::2]

        u_mag = np.sqrt(ux**2 + uy**2)

        max_disp = np.max(u_mag)
        mean_disp = np.mean(u_mag)

        # Compliance
        compliance = float(self.F.T @ self.u)

        # Energie
        K = self._assemble_K_for_elements(self.remaining_elements)
        energy = 0.5 * float(self.u.T @ K @ self.u)

        report = {
            "total_nodes":       total_nodes,
            "remaining_nodes":   remaining_nodes,
            "mass_percent":      mass_frac,
            "max_displacement":  max_disp,
            "mean_displacement": mean_disp,
            "compliance":        compliance,
            "energy":            energy,
        }

        return report
    
    # Erweiterung 3: Lastpfad-Visualisierung (UNVERFORMT)
    def plot_load_paths(self, threshold=0.05):

        if self.u is None or self.remaining_elements is None:
            return None

        fig, ax = plt.subplots()

        energies = []

        # Energie pro Element berechnen
        for idx in self.remaining_elements:

            i, j, K_elem, dofs = self.grid.elements[idx]

            u_e = self.u[dofs]

            energy = float(u_e.T @ K_elem @ u_e)

            energies.append((i, j, energy))

        if not energies:
            return fig

        max_energy = max(e for _, _, e in energies)

        if max_energy == 0:
            max_energy = 1.0

        # Filter: nur starke Lastpfade anzeigen
        threshold = threshold * max_energy

        for i, j, energy in energies:

            if energy < threshold:
                continue

            x1 = i % self.grid.nx
            y1 = i // self.grid.nx
            x2 = j % self.grid.nx
            y2 = j // self.grid.nx

            intensity = energy / max_energy

            ax.plot(
                [x1, x2],
                [y1, y2],
                color=plt.cm.jet(intensity),
                linewidth=1 + 4 * intensity
            )

        ax.set_aspect("equal")
        ax.invert_yaxis()

        ax.set_title("Lastpfade (Kraftfluss)")
        ax.set_xlabel("x")
        ax.set_ylabel("y")

        return fig