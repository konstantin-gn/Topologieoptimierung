import numpy as np
import numpy.typing as npt


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

        self.K_global = np.zeros((self.ndof, self.ndof))
        self.edge_list = []  # speichert (i,j)
        self.elements  = []

        self._build_grid()

    def node_id(self, ix, iy):
        return iy * self.nx + ix

    def element_dofs(self, i, j):
        return [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]

    def _add_element(self, i, j, direction):
        K_local = self.k * np.array([[1, -1], [-1, 1]])
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

        # Diagonal ↘
        for iy in range(self.ny - 1):
            for ix in range(self.nx - 1):
                i = self.node_id(ix, iy)
                j = self.node_id(ix + 1, iy + 1)
                self._add_element(i, j, np.array([1.0, 1.0]))

        # Diagonal ↙
        for iy in range(self.ny - 1):
            for ix in range(1, self.nx):
                i = self.node_id(ix, iy)
                j = self.node_id(ix - 1, iy + 1)
                self._add_element(i, j, np.array([-1.0, 1.0]))

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
        self.active_nodes = set(range(self.grid.n_nodes))

    def run(self):
        F = np.zeros(self.grid.ndof)     # Kraftvektor initialisieren

        load_node = self.grid.node_id(self.load_ix, self.load_iy)          # Lastknoten bestimmen (Lastangriffspunkt)

        F[2 * load_node]     = self.Fx   # x-Richtung
        F[2 * load_node + 1] = self.Fy   # y-Richtung

        # Randbedingungen
        u_fixed_idx = []
        node_fixed = self.grid.node_id(0, self.grid.ny - 1)                # Festlager unten links (vorerst)
        u_fixed_idx.extend([2 * node_fixed, 2 * node_fixed + 1])

        node_lose = self.grid.node_id(self.grid.nx - 1, self.grid.ny - 1)  # Loslager unten rechts (vorerst)
        u_fixed_idx.append(2 * node_lose + 1)

        target_nodes = int(self.grid.n_nodes * self.target_mass_frac)

        iteration = 0

        while len(self.active_nodes) > target_nodes:

            iteration += 1
            print(f"\nIteration {iteration}")

            K = self.rebuild_global_matrix()

            u = self.solver.solve(K, F, u_fixed_idx)

            if u is None:
                print("Solver ERROR !")
                break

            node_energy = self._compute_node_energy_active(u)

            removable = [
                node for node in self.active_nodes
                if node not in {load_node, node_fixed, node_lose}
            ]

            removable_sorted = sorted(removable, key=lambda n: node_energy[n])

            n_remove = max(1, int(0.05 * len(self.active_nodes)))

            removed  = 0

            for node in removable_sorted:

                trial = self.active_nodes - {node}

                if self._is_connected(trial):

                    self.active_nodes.remove(node)
                    removed += 1

                if removed >= n_remove:
                    break

            print("aktive Knoten:", len(self.active_nodes))     
        
        topology = np.zeros(self.grid.n_nodes)

        for n in self.active_nodes:
            topology[n] = 1

        topology_matrix = topology.reshape((self.grid.ny, self.grid.nx))

        print("\nFinal Topologiematrix:")

        for row in topology_matrix:
            print(" ".join(str(int(x)) for x in row))  
        
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

        valid_edges = [                  # gültige Kanten bestimmen
            (i, j)
            for (i, j) in self.grid.edge_list
            if i in allowed_nodes and j in allowed_nodes
        ]

        if len(valid_edges) == 0:
            return False

        n = len(allowed_nodes)
        node_list = list(allowed_nodes)
        node_index = {node: idx for idx, node in enumerate(node_list)}

        B = np.zeros((n, len(valid_edges)))

        for e, (i, j) in enumerate(valid_edges):
            B[node_index[i], e] = 1
            B[node_index[j], e] = -1

        L = B @ B.T

        eigvals = np.linalg.eigvalsh(L)

        tol = 1e-8
        n_zero = np.sum(eigvals < tol)

        return n_zero == 1
    
    def rebuild_global_matrix(self):

        ndof = self.grid.ndof
        K = np.zeros((ndof, ndof))

        for i, j, K_elem, dofs in self.grid.elements:

            if i not in self.active_nodes:
                continue

            if j not in self.active_nodes:
                continue

            for a in range(4):
                for b in range(4):
                    K[dofs[a], dofs[b]] += K_elem[a, b]

        return K


if __name__ == "__main__":
    user_input = UserInput()
    user_input.get_input()

    sim = Simulation(
        nx=user_input.nx,
        ny=user_input.ny,
        target_mass_frac=user_input.target_mass_frac,
        load_ix=user_input.load_ix,
        load_iy=user_input.load_iy,
        Fx=user_input.Fx,
        Fy=user_input.Fy,
    )
    sim.run()