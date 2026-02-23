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
    def __init__(self, nx: int, ny: int, target_mass_frac: float):
        self.grid   = MakeGrid(nx, ny)
        self.solver = LinearSolver()
        self.target_mass_frac = target_mass_frac

    def run(self):
        F = np.zeros(self.grid.ndof)

        # Kraft auf rechten oberen Knoten (vorerst)
        load_node = self.grid.node_id(self.grid.nx - 1, 0)
        F[2 * load_node] = 10.0

        # Randbedingungen
        u_fixed_idx = []
        node_fixed = self.grid.node_id(0, self.grid.ny - 1)                # Festlager unten links (vorerst)
        u_fixed_idx.extend([2 * node_fixed, 2 * node_fixed + 1])

        node_lose = self.grid.node_id(self.grid.nx - 1, self.grid.ny - 1)  # Loslager unten rechts (vorerst)
        u_fixed_idx.append(2 * node_lose + 1)

        u = self.solver.solve(self.grid.K_global, F, u_fixed_idx)
        if u is None:
            print("System konnte nicht gelöst werden.")
            return

        total_energy = 0.5 * u.T @ self.grid.K_global @ u
        print("Total energy:", total_energy)

        node_energy = self._compute_node_energy(u)

        n_nodes_total = self.grid.n_nodes
        n_nodes_target = int(n_nodes_total * self.target_mass_frac)

        remaining_nodes = set(range(self.grid.n_nodes))
        essential_nodes = {load_node, node_fixed, node_lose}

        sorted_nodes = np.argsort(node_energy)  # kleinste zuerst

        for node in sorted_nodes:

            if node in essential_nodes:
                continue

            if len(remaining_nodes) <= n_nodes_target:
                break

            trial_nodes = remaining_nodes - {node}

            if self._is_connected(trial_nodes):
                remaining_nodes.remove(node)

        print(
            f"\nOptimierungsziel: {self.target_mass_frac*100:.0f}% der Ausgangsknoten"
        )
        print("Knoten, die im optimierten Balken verbleiben:")
        print(sorted(list(remaining_nodes)))

        # ---- Binäre Topologie-Matrix erzeugen ----
        topology_vector = np.zeros(self.grid.n_nodes)

        for node in remaining_nodes:
            topology_vector[node] = 1

        topology_matrix = topology_vector.reshape((self.grid.ny, self.grid.nx))

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

        # gültige Kanten bestimmen
        valid_edges = [
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


if __name__ == "__main__":
    user_input = UserInput()
    user_input.get_input()

    sim = Simulation(
        nx=user_input.nx, ny=user_input.ny, target_mass_frac=user_input.target_mass_frac
    )
    sim.run()