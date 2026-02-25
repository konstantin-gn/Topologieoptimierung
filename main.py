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

        K_mod = K.copy()
        F_mod = F.copy()

        for d in u_fixed_idx:
            K_mod[d, :] = 0.0
            K_mod[:, d] = 0.0
            K_mod[d, d] = 1.0
            F_mod[d] = 0.0

        try:
            return np.linalg.solve(K_mod, F_mod)
        except np.linalg.LinAlgError:
            K_mod += np.eye(K.shape[0]) * self.eps
            try:
                return np.linalg.solve(K_mod, F_mod)
            except np.linalg.LinAlgError:
                return None


class MakeGrid:
    def __init__(self, nx: int, ny: int, k: float = 1.0):
        self.nx = nx
        self.ny = ny
        self.k  = k

        self.n_nodes = nx * ny
        self.ndof = 2 * self.n_nodes

        self.K_global = np.zeros((self.ndof, self.ndof))
        self.edge_list = []  # speichert (i,j)
        self.elements = []

        self._build_grid()

    def node_id(self, ix, iy):
        return iy * self.nx + ix

    def element_dofs(self, i, j):
        return [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]

    def _add_element(self, i, j, direction, k_factor=1.0):
        # lokale 1D-Federsteifigkeit mit optionalem Skalierungsfaktor
        K_local = (self.k * k_factor) * np.array([[1, -1], [-1, 1]])

        # Normierter Richtungsvektor der Feder
        e_n = direction / np.linalg.norm(direction)

        # Projektion in globale Koordinaten
        O = np.outer(e_n, e_n)

        # 4x4 Elementsteifigkeitsmatrix im globalen System
        K_elem = np.kron(K_local, O)

        self.edge_list.append((i, j))
        dofs = self.element_dofs(i, j)

        # Superposition in globale Steifigkeitsmatrix
        for a in range(4):
            for b in range(4):
                self.K_global[dofs[a], dofs[b]] += K_elem[a, b]

        self.elements.append((i, j, K_elem, dofs))

        e_n = direction / np.linalg.norm(direction)
        O = np.outer(e_n, e_n)
        K_elem = np.kron(K_local, O)

        self.edge_list.append((i, j))
        dofs = self.element_dofs(i, j)

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

        # Vertical
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
                self._add_element(
                    i, j,
                    np.array([1.0, 1.0]),
                    k_factor=1/np.sqrt(2)
                )

        # Diagonal 2
        for iy in range(self.ny - 1):
            for ix in range(1, self.nx):
                i = self.node_id(ix, iy)
                j = self.node_id(ix - 1, iy + 1)
                self._add_element(
                    i, j,
                    np.array([-1.0, 1.0]),
                    k_factor=1/np.sqrt(2)
                )
                
    def build_incidence_matrix(self):
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
                frac = float(
                    input(
                        "Optimierungsgrad (Prozent der verbleibenden Masse, z.B. 40): "
                    )
                )
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
                print(
                    "Ungültige Eingabe. Bitte ganze positive Zahlen für Größe und Prozent zwischen 1-100 eingeben."
                )


class Simulation:
    def __init__(self, nx, ny, target_mass_frac, load_ix, load_iy, Fx, Fy):
        self.grid   = MakeGrid(nx, ny)
        self.solver = LinearSolver()
        self.target_mass_frac = target_mass_frac
        self.load_ix = load_ix
        self.load_iy = load_iy
        self.Fx = Fx
        self.Fy = Fy
        self.optim_steps: list[set[int]] = []  # speichert Knoten in jedem Schritt

    def run(self):
        F = np.zeros(self.grid.ndof)
        load_node = self.grid.node_id(self.load_ix, self.load_iy)
        F[2 * load_node]     = self.Fx   # x-Richtung
        F[2 * load_node + 1] = self.Fy   # y-Richtung

        # Randbedingungen
        u_fixed_idx = []
        node_fixed = self.grid.node_id(0, self.grid.ny - 1)                # Festlager unten links
        u_fixed_idx.extend([2 * node_fixed, 2 * node_fixed + 1])

        node_lose = self.grid.node_id(self.grid.nx - 1, self.grid.ny - 1)  # Loslager unten rechts
        u_fixed_idx.append(2 * node_lose + 1)

        u = self.solver.solve(self.grid.K_global, F, u_fixed_idx)
        if u is None:
            print("System konnte nicht gelöst werden.")
            return

        total_energy = 0.5 * u.T @ self.grid.K_global @ u
        print("Total energy:", total_energy)

        # Knotenenergien berechnen
        node_energy = self._compute_node_energy(u)

        # Berechne Elementenergie
        element_energy = np.zeros(len(self.grid.elements))
        for idx, (i, j, K_elem, dofs) in enumerate(self.grid.elements):
            u_e = u[dofs]
            c_e = 0.5 * u_e.T @ K_elem @ u_e
            element_energy[idx] = c_e

        # Ziel: Anzahl der zu behaltenden Elemente
        n_elements_target = int(len(self.grid.elements) * self.target_mass_frac)
        remaining_elements = set(range(len(self.grid.elements)))

        # Optimierungsschritte initialisieren
        self.optim_steps: list[set[int]] = []
        # Anfangszustand: alle Knoten
        all_nodes = set(range(self.grid.n_nodes))
        self.optim_steps.append(all_nodes.copy())

        # Sortiere Elemente nach Energie (kleinste zuerst)
        sorted_elements = np.argsort(element_energy)

        for e_idx in sorted_elements:
            if len(remaining_elements) <= n_elements_target:
                break
            trial_elements = remaining_elements - {e_idx}

            # Berechne verbleibende Knoten für diesen Trial-Schritt
            remaining_nodes_trial = set()
            for idx in trial_elements:
                i, j, _, _ = self.grid.elements[idx]
                remaining_nodes_trial.add(i)
                remaining_nodes_trial.add(j)

            # Prüfe, ob die Struktur noch verbunden ist
            if self._is_connected(remaining_nodes_trial):
                remaining_elements.remove(e_idx)
                # Schritt speichern: aktuelle Knoten nach Entfernung
                self.optim_steps.append(remaining_nodes_trial.copy())

        # Speichere die endgültigen Ergebnisse
        self.remaining_elements = remaining_elements

        # Alle verbleibenden Knoten aus den verbleibenden Elementen ableiten
        remaining_nodes = set()
        for idx in remaining_elements:
            i, j, _, _ = self.grid.elements[idx]
            remaining_nodes.add(i)
            remaining_nodes.add(j)

        self.remaining_nodes = remaining_nodes
        self.u = u

        topology_vector = np.zeros(self.grid.n_nodes)
        for node in remaining_nodes:
            topology_vector[node] = 1

        topology_matrix = topology_vector.reshape((self.grid.ny, self.grid.nx))

        print(f"\nOptimierungsziel: {self.target_mass_frac*100:.0f}% der Ausgangsknoten")
        print("Knoten, die im optimierten Balken verbleiben:")
        print(sorted(list(remaining_nodes)))

        print("\nTopologie-Matrix (1 = behalten, 0 = gelöscht):")
        for row in topology_matrix:
            print("  ".join(str(int(val)) for val in row))

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

    def _is_connected(self, allowed_nodes):
   

        # gültige Kanten (nur Knoten in allowed_nodes)
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
    
    def plot_structure(self, u=None, scale=1.0, remaining_nodes=None):
       

        fig, ax = plt.subplots()

        for (i, j) in self.grid.edge_list:
            if remaining_nodes is not None:
                if i not in remaining_nodes or j not in remaining_nodes:
                    continue

            x1 = i % self.grid.nx
            y1 = i // self.grid.nx
            x2 = j % self.grid.nx
            y2 = j // self.grid.nx

            if u is not None:
                x1 += scale * u[2*i]
                y1 += scale * u[2*i+1]
                x2 += scale * u[2*j]
                y2 += scale * u[2*j+1]

            ax.plot([x1, x2], [y1, y2], "k-")

        ax.set_aspect("equal")
        ax.invert_yaxis()
        ax.set_title("Struktur")

        return fig

    def plot_nodes(self, remaining_nodes, u=None, scale=1.0):
        
        fig, ax = plt.subplots()
        
        for node in remaining_nodes:
            x = node % self.grid.nx
            y = node // self.grid.nx
            if u is not None:
                x += scale * u[2*node]
                y += scale * u[2*node+1]
            ax.scatter(x, y, color="black", s=30)  # Punktgröße anpassen

        ax.set_aspect("equal")
        ax.invert_yaxis()
        ax.set_title("Knotenstruktur")
        return fig