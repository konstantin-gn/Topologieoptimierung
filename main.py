import numpy as np
import numpy.typing as npt
import networkx as nx
import matplotlib.pyplot as plt


class LinearSolver:
    def __init__(self, eps: float = 1e-9):
        self.eps = eps

    def solve(
        self,
        K: npt.NDArray[np.float64],
        F: npt.NDArray[np.float64],
        u_fixed_idx: list[int],
    ) -> npt.NDArray[np.float64] | None:
        """
        Löst das lineare Gleichungssystem K u = F mit Dirichlet-Randbedingungen.
        Randbedingungen werden durch Modifikation von K und F umgesetzt.
        Bei Singularität wird eine kleine Regularisierung (eps*I) versucht.
        """
        K_mod = K.copy()
        F_mod = F.copy()

        # DOFs mit festen Verschiebungen auf u=0 setzen
        for d in u_fixed_idx:
            K_mod[d, :] = 0.0
            K_mod[:, d] = 0.0
            K_mod[d, d] = 1.0
            F_mod[d] = 0.0

        try:
            return np.linalg.solve(K_mod, F_mod)
        except np.linalg.LinAlgError:
            # Regularisierung gegen Singularität
            K_mod += np.eye(K.shape[0]) * self.eps
            try:
                return np.linalg.solve(K_mod, F_mod)
            except np.linalg.LinAlgError:
                return None


class MakeGrid:
    def __init__(self, nx: int, ny: int, k: float = 1.0):
        self.nx = nx
        self.ny = ny
        self.k = k

        self.n_nodes = nx * ny
        self.ndof = 2 * self.n_nodes

        self.K_global = np.zeros((self.ndof, self.ndof))
        self.edge_list = []  # speichert (i,j)
        self.elements = []   # speichert (i, j, K_elem, dofs)

        self._build_grid()

    def node_id(self, ix, iy):
        return iy * self.nx + ix

    def element_dofs(self, i, j):
        return [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]

    def _add_element(self, i, j, direction, k_factor=1.0):
        """
        Fügt ein Federelement zwischen i und j hinzu.
        direction definiert die Orientierung (z.B. [1,0] horizontal).
        k_factor erlaubt diagonale Skalierung.
        """
        # 1D Federsteifigkeit
        K_local = (self.k * k_factor) * np.array([[1.0, -1.0], [-1.0, 1.0]])

        # normierter Richtungsvektor
        e_n = direction / np.linalg.norm(direction)

        # Projektion in globale Koordinaten (2D)
        O = np.outer(e_n, e_n)

        # 4x4 Elementmatrix
        K_elem = np.kron(K_local, O)

        # Kante und Element speichern
        self.edge_list.append((i, j))
        dofs = self.element_dofs(i, j)

        # Assemble in globale Matrix
        for a in range(4):
            for b in range(4):
                self.K_global[dofs[a], dofs[b]] += K_elem[a, b]

        self.elements.append((i, j, K_elem, dofs))

    def _build_grid(self):
        # Horizontal
        for iy in range(self.ny):
            for ix in range(self.nx - 1):
                i = self.node_id(ix, iy)
                j = self.node_id(ix + 1, iy)
                self._add_element(i, j, np.array([1.0, 0.0]))

        # Vertikal
        for iy in range(self.ny - 1):
            for ix in range(self.nx):
                i = self.node_id(ix, iy)
                j = self.node_id(ix, iy + 1)
                self._add_element(i, j, np.array([0.0, 1.0]))

        # Diagonal 1
        for iy in range(self.ny - 1):
            for ix in range(self.nx - 1):
                i = self.node_id(ix, iy)
                j = self.node_id(ix + 1, iy + 1)
                self._add_element(i, j, np.array([1.0, 1.0]), k_factor=1 / np.sqrt(2))

        # Diagonal 2
        for iy in range(self.ny - 1):
            for ix in range(1, self.nx):
                i = self.node_id(ix, iy)
                j = self.node_id(ix - 1, iy + 1)
                self._add_element(i, j, np.array([-1.0, 1.0]), k_factor=1 / np.sqrt(2))

    def build_incidence_matrix(self):
        """
        Baut die Inzidenzmatrix B (Knoten x Kanten).
        Kann später für sehr schnelle Konnektivitätschecks genutzt werden.
        """
        n_edges = len(self.edge_list)
        B = np.zeros((self.n_nodes, n_edges))

        for e, (i, j) in enumerate(self.edge_list):
            B[i, e] = 1.0
            B[j, e] = -1.0

        return B


class UserInput:
    def __init__(self):
        self.nx: int = 10
        self.ny: int = 4
        self.target_mass_frac: float = 0.4
        self.load_ix: int = 0
        self.load_iy: int = 0
        self.Fx: float = 0.0
        self.Fy: float = 0.0

    def get_input(self):
        print("Bitte die Größe des Balkens eingeben (Anzahl an Knoten)")

        while True:
            try:
                nx = int(input("Länge (in Knoten): "))
                ny = int(input("Höhe  (in Knoten): "))
                frac = float(input("Optimierungsgrad (Prozent der verbleibenden Masse, z.B. 40): "))
                print("\nKraftangriffspunkt eingeben:")

                ix = int(input(f"Knoten x (0 bis {nx-1}): "))
                iy = int(input(f"Knoten y (0 bis {ny-1}): "))

                Fx = float(input("Kraft in x-Richtung (positiv=rechts, negativ=links): "))
                Fy = float(input("Kraft in y-Richtung (positiv=unten, negativ=oben): "))

                if not (0 <= ix < nx and 0 <= iy < ny):
                    raise ValueError

                self.load_ix = ix
                self.load_iy = iy
                self.Fx = Fx
                self.Fy = Fy

                if nx <= 0 or ny <= 0 or not (0 < frac <= 100):
                    raise ValueError

                self.nx = nx
                self.ny = ny
                self.target_mass_frac = frac / 100
                break

            except ValueError:
                print("Ungültige Eingabe. Bitte ganze positive Zahlen für Größe und Prozent zwischen 1-100 eingeben.")


class Simulation:
    """
    Deine Simulation + Erweiterung:
    - initialize_state(): setzt F, Lager, protected nodes, remaining sets einmalig
    - run(): startet neu (reset)
    - resume(): setzt ab aktuellem Stand fort
    - to_record_dict/from_record_dict: Save/Load für TinyDB
    """

    def __init__(self, nx, ny, target_mass_frac, load_ix, load_iy, Fx, Fy):
        self.grid = MakeGrid(nx, ny)
        self.solver = LinearSolver()

        self.target_mass_frac = float(target_mass_frac)
        self.load_ix = int(load_ix)
        self.load_iy = int(load_iy)
        self.Fx = float(Fx)
        self.Fy = float(Fy)

        self.optim_steps: list[set[int]] = []

        # --- Zustandsfelder für Save/Load/Fortsetzen ---
        self._initialized = False
        self.F: np.ndarray | None = None
        self.u_fixed_idx: list[int] | None = None

        self.load_node: int | None = None
        self.node_fixed: int | None = None
        self.node_lose: int | None = None

        self.protected_nodes: set[int] | None = None
        self.support_nodes: set[int] | None = None

        self.remaining_nodes: set[int] | None = None
        self.remaining_elements: set[int] | None = None

        self.u: np.ndarray | None = None  # letzte Lösung (Plot)

    # ---------------------------------------------------------
    # Initialisierung (einmalig)
    # ---------------------------------------------------------
    def initialize_state(self) -> None:
        """
        Baut Startzustand (F, Lager, Schutzknoten, remaining sets).
        Wird bei run() und resume() genutzt.
        """
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

    # ---------------------------------------------------------
    # Start neu
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # Fortsetzen
    # ---------------------------------------------------------
    def resume(self, max_iters: int | None = None) -> None:
        """
        Setzt Optimierung ab aktuellem Stand fort.
        max_iters optional, um nur N Schritte weiterzumachen.
        """
        self.initialize_state()
        self._optimization_loop(max_tries=50, cond_max=1e8, max_iters=max_iters)

    # ---------------------------------------------------------
    # Kernschleife (deine while-Schleife, minimal angepasst)
    # ---------------------------------------------------------
    def _optimization_loop(self, max_tries: int, cond_max: float, max_iters: int | None):
        """
        Führt die iterative Knoten-Entfernung durch.
        Der Code entspricht deiner run()-Schleife, nur dass
        remaining_nodes/elements aus dem Objekt kommen (für resume).
        """
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

        # Finale Lösung für Plot: nochmal auf finaler Struktur lösen
        K_opt = self._assemble_K_for_elements(self.remaining_elements)

        removed_nodes = set(range(self.grid.n_nodes)) - self.remaining_nodes
        u_fixed_idx_opt = list(self.u_fixed_idx)
        for n in removed_nodes:
            u_fixed_idx_opt += [2 * n, 2 * n + 1]
        u_fixed_idx_opt = sorted(set(u_fixed_idx_opt))

        u_opt = self.solver.solve(K_opt, self.F, u_fixed_idx_opt)
        self.u = u_opt if u_opt is not None else np.zeros(self.grid.ndof)

        # Konsolen-Ausgabe wie bisher
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

    # ---------------------------------------------------------
    # Save/Load (TinyDB kompatibel)
    # ---------------------------------------------------------
    def to_record_dict(self, label: str) -> dict:
        """
        Exportiert Zustand in JSON-kompatibles Dict:
        - sets -> lists
        - numpy -> lists
        """
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

    @staticmethod
    def from_record_dict(record: dict) -> "Simulation":
        """
        Baut Simulation aus DB-Daten wieder auf.
        """
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

    # ---------------------------------------------------------
    # Deine Helper (unverändert)
    # ---------------------------------------------------------
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

    def _compute_node_energy_subset(self, u: np.ndarray, remaining_elements: set[int]) -> np.ndarray:
        node_energy = np.zeros(self.grid.n_nodes, dtype=float)

        for idx in remaining_elements:
            i, j, K_elem, dofs = self.grid.elements[idx]
            u_e = u[dofs]
            c_e = 0.5 * u_e.T @ K_elem @ u_e
            node_energy[i] += 0.5 * c_e
            node_energy[j] += 0.5 * c_e

        return node_energy

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

    def _assemble_K_for_elements(self, remaining_elements: set[int]) -> np.ndarray:
        K = np.zeros((self.grid.ndof, self.grid.ndof), dtype=float)

        for idx in remaining_elements:
            i, j, K_elem, dofs = self.grid.elements[idx]
            for a in range(4):
                for b in range(4):
                    K[dofs[a], dofs[b]] += K_elem[a, b]

        return K

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