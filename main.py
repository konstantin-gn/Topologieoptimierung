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
            F_mod[d]    = 0.0

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
        self.ndof    = 2 * self.n_nodes

        self.K_global  = np.zeros((self.ndof, self.ndof))
        self.edge_list = []  # speichert (i,j)
        self.elements  = []

        self._build_grid()

    def node_id(self, ix, iy):
        return iy * self.nx + ix

    def element_dofs(self, i, j):
        return [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]

    def _add_element(self, i, j, direction, k_factor=1.0):
        
        # 1D-Federsteifigkeit (lokal) mit Skalierung
        K_local = (self.k * k_factor) * np.array([[1.0, -1.0], [-1.0, 1.0]])

        # normierter Richtungsvektor
        e_n = direction / np.linalg.norm(direction)

        # Projektion in globale Koordinaten
        O = np.outer(e_n, e_n)

        # 4x4 Elementsteifigkeitsmatrix im globalen System
        K_elem = np.kron(K_local, O)

        # Kante und Element speichern
        self.edge_list.append((i, j))
        dofs = self.element_dofs(i, j)

        # Assemble: Beitrag in globale Matrix addieren (Superposition)
        for a in range(4):
            for b in range(4):
                self.K_global[dofs[a], dofs[b]] += K_elem[a, b]

        self.elements.append((i, j, K_elem, dofs))

    def _build_grid(self):
<<<<<<< HEAD
=======
        
>>>>>>> überarbeitung-optimierung
        # Horizontal -
        for iy in range(self.ny):
            for ix in range(self.nx - 1):
                i = self.node_id(ix, iy)
                j = self.node_id(ix + 1, iy)
                self._add_element(i, j, np.array([1.0, 0.0]))

        # Vertikal |
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
                nx   = int(input("Länge (in Knoten): "))
                ny   = int(input("Höhe  (in Knoten): "))
                frac = float(input("Optimierungsgrad (Prozent der verbleibenden Masse, z.B. 40): "))
                print("\nKraftangriffspunkt eingeben:")

                ix = int(input(f"Knoten x (0 bis {nx-1}): "))
                iy = int(input(f"Knoten y (0 bis {ny-1}): "))

                Fx = float(input("Kraft in x-Richtung (positiv=rechts, negativ=links): "))
                Fy = float(input("Kraft in y-Richtung (positiv=unten,  negativ=oben): "))

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

    def __init__(self, nx, ny, target_mass_frac, load_ix, load_iy, Fx, Fy):
        self.grid   = MakeGrid(nx, ny)
        self.solver = LinearSolver()
        self.target_mass_frac = target_mass_frac
        self.load_ix = load_ix
        self.load_iy = load_iy
        self.Fx = Fx
        self.Fy = Fy
        self.active_nodes = set(range(self.grid.n_nodes))

    def run(self):
<<<<<<< HEAD
=======
        """
        Führt eine statische Simulation Ku=F aus und macht anschließend eine
        knotenbasierte Topologieoptimierung:

        - Knotenenergie aus Feder-Verformungsenergie (node_energy)
        - Knoten mit niedriger Energie entfernen
        - Entfernen nur, wenn Struktur zusammenhängend bleibt (_is_connected)
        - Last- und Lagerknoten werden geschützt (nicht entfernbar)
        """
        # Kraftvektor aufbauen
>>>>>>> überarbeitung-optimierung
        F = np.zeros(self.grid.ndof)
        load_node = self.grid.node_id(self.load_ix, self.load_iy)
        F[2 * load_node]     = self.Fx   # x-Richtung
        F[2 * load_node + 1] = self.Fy   # y-Richtung

<<<<<<< HEAD
        # Randbedingungen
=======
        # Kräfte: +x nach rechts, +y nach unten 
        F[2 * load_node]     = self.Fx
        F[2 * load_node + 1] = self.Fy

        # 2) Randbedingungen (Lager)
>>>>>>> überarbeitung-optimierung
        u_fixed_idx = []
        node_fixed = self.grid.node_id(0, self.grid.ny - 1)                # Festlager unten links
        u_fixed_idx.extend([2 * node_fixed, 2 * node_fixed + 1])

        node_lose = self.grid.node_id(self.grid.nx - 1, self.grid.ny - 1)  # Loslager unten rechts
        u_fixed_idx.append(2 * node_lose + 1)

<<<<<<< HEAD
=======

        # 3) Lösen K*u = F
>>>>>>> überarbeitung-optimierung
        u = self.solver.solve(self.grid.K_global, F, u_fixed_idx)
        if u is None:
            print("System konnte nicht gelöst werden.")
            return

        total_energy = 0.5 * u.T @ self.grid.K_global @ u
        print("Total energy:", total_energy)

<<<<<<< HEAD
        # Knotenenergien berechnen
        node_energy = self._compute_node_energy(u)

        # Berechne Elementenergie
        element_energy = np.zeros(len(self.grid.elements))
        for idx, (i, j, K_elem, dofs) in enumerate(self.grid.elements):
            u_e = u[dofs]
            c_e = 0.5 * u_e.T @ K_elem @ u_e
            element_energy[idx] = c_e
=======
        # Knotenenergie berechnen
        # _compute_node_energy teilt jede Elementenergie 50/50 auf beide Knoten auf
        node_energy = self._compute_node_energy(u)
      
        # Iterative Optimierung: Knoten mit niedriger Energie entfernen, bis Ziel erreicht
        # Ziel: Anzahl zu behaltender Knoten
        n_nodes_target = int(self.grid.n_nodes * self.target_mass_frac)
>>>>>>> überarbeitung-optimierung

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

<<<<<<< HEAD
=======
        u_opt = self.solver.solve(K_opt, F, u_fixed_idx_opt)
        self.u = u_opt if u_opt is not None else np.zeros(self.grid.ndof)

        # Topologie-Matrix (1=Knoten bleibt, 0=entfernt)
>>>>>>> überarbeitung-optimierung
        topology_vector = np.zeros(self.grid.n_nodes)
        for node in remaining_nodes:
            topology_vector[node] = 1

        topology_matrix = topology.reshape((self.grid.ny, self.grid.nx))

        print("\nFinal Topologiematrix:")

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
        print("\nKnoten-Energie Matrix:")
        for row in node_energy_matrix:
            print("  ".join(f"{val:.6f}" for val in row))

        return node_energy
    
    def _compute_node_energy_subset(self, u: np.ndarray, remaining_elements: set[int]) -> np.ndarray:
        """
        Berechnet die Knotenenergie nur über die aktuell verbleibenden Elemente.
        (Wichtig für iterative Optimierung, da sich die Struktur laufend ändert.)

        u: Verschiebungsvektor (2 DOF pro Knoten)
        remaining_elements: Indizes der Elemente, die gerade noch existieren
        """
        node_energy = np.zeros(self.grid.n_nodes, dtype=float)

        for idx in remaining_elements:
            i, j, K_elem, dofs = self.grid.elements[idx]
            u_e = u[dofs]
            c_e = 0.5 * u_e.T @ K_elem @ u_e  # Element-Verformungsenergie

            # Hälfte auf jeden Endknoten (wie in der Aufgabenstellung)
            node_energy[i] += 0.5 * c_e
            node_energy[j] += 0.5 * c_e

        return node_energy
    
    def _compute_node_energy_active(self, u):

        energy = np.zeros(self.grid.n_nodes)

        for i, j, K_elem, dofs in self.grid.elements:

            if i not in self.active_nodes:
                continue

            if j not in self.active_nodes:
                continue

            u_e = u[dofs]

            e = 0.5 * u_e.T @ K_elem @ u_e

            energy[i] += 0.5 * e
            energy[j] += 0.5 * e

        return energy

    def _is_connected(self, allowed_nodes):
<<<<<<< HEAD
        import networkx as nx

        valid_edges = [                  # gültige Kanten bestimmen
=======
        # gültige Kanten (nur Knoten in allowed_nodes)
        valid_edges = [
>>>>>>> überarbeitung-optimierung
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
    
<<<<<<< HEAD
    def plot_structure(self, u=None, scale=1.0, remaining_nodes=None):
        import matplotlib.pyplot as plt

=======
    def _has_load_path_to_supports(
        self,
        allowed_nodes: set[int],
        load_node: int,
        support_nodes: set[int],
        ) -> bool:
        """
        Prüft, ob der Lastknoten über die vorhandenen Federn (Kanten) einen Pfad
        zu mindestens einem Lagerknoten besitzt.

        allowed_nodes: die aktuell verbleibenden Knoten
        load_node: Knoten, an dem die Last angreift
        support_nodes: Menge der Lagerknoten (z.B. {Festlager, Loslager})
        """
        # Wenn Lastknoten gar nicht mehr existiert -> fail (sollte durch protected_nodes nicht passieren)
        if load_node not in allowed_nodes:
            return False

        # gültige Kanten (nur zwischen verbleibenden Knoten)
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

        # Prüfe Pfad zu mind. einem Lager
        for s in support_nodes:
            if s in allowed_nodes and nx.has_path(G, load_node, s):
                return True

        return False
    
    def _assemble_K_for_elements(self, remaining_elements: set[int]) -> np.ndarray:
        """
        Baut eine globale Steifigkeitsmatrix nur aus den übergebenen Elementen auf.
        Minimalinvasiv: nutzt die bereits gespeicherten (K_elem, dofs) aus self.grid.elements.
        """
        K = np.zeros((self.grid.ndof, self.grid.ndof), dtype=float)

        for idx in remaining_elements:
            i, j, K_elem, dofs = self.grid.elements[idx]
            # Superposition: Elementbeitrag an den entsprechenden DOFs aufsummieren
            for a in range(4):
                for b in range(4):
                    K[dofs[a], dofs[b]] += K_elem[a, b]

        return K
    
    def _is_mechanically_stable(self, K, u_fixed_idx, cond_max=1e8):
        """
        Prüft mechanische Stabilität über die Konditionszahl
        der freien DOFs (K_ff).
        cond_max: Schwelle für akzeptable Konditionszahl.
                Je kleiner, desto strenger.
        """
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
        """
        Konsistente Plotlogik:
        - Wenn remaining_nodes gesetzt: zeichne alle Elemente, deren Endknoten drin sind.
        - Wenn remaining_nodes None:    fallback = alle Knoten.
        """
>>>>>>> überarbeitung-optimierung
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
<<<<<<< HEAD

        return fig

    def plot_nodes(self, remaining_nodes, u=None, scale=1.0):
        import matplotlib.pyplot as plt
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
=======
>>>>>>> überarbeitung-optimierung
        return fig