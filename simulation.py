import numpy as np
from solver import LinearSolver
from structure import Structure


class Simulation:

    # Initialisiert Grid und Solver
    def __init__(self, nx: int, ny: int, target_mass_frac: float):

        self.structure = Structure(nx, ny)
        self.solver = LinearSolver()

        # Zielanteil der verbleibenden Masse
        self.target_mass_frac = target_mass_frac

    # Führt Simulation + einfache Topologieoptimierung aus
    def run(self):

        F = np.zeros(self.structure.ndof)

        # Kraft am rechten unteren Knoten
        load_node = self.structure.node_id(self.structure.nx - 1, 0)
        F[2 * load_node] = 10.0

        # Randbedingungen
        u_fixed_idx = []

        # Festlager links unten
        node_fixed = self.structure.node_id(0, self.structure.ny - 1)
        u_fixed_idx.extend([2 * node_fixed, 2 * node_fixed + 1])

        # Loslager rechts unten (nur y fixiert)
        node_lose = self.structure.node_id(self.structure.nx - 1, self.structure.ny - 1)
        u_fixed_idx.append(2 * node_lose + 1)

        # System lösen
        u = self.solver.solve(self.structure.K_global, F, u_fixed_idx)

        if u is None:
            print("System konnte nicht gelöst werden.")
            return

        # Gesamtenergie
        total_energy = 0.5 * u.T @ self.structure.K_global @ u
        print("Total energy:", total_energy)

        # Knotenenergie berechnen
        node_energy = self.structure.compute_node_energy(u)

        # Zielanzahl verbleibender Knoten
        n_target = int(self.structure.n_nodes * self.target_mass_frac)

        # Knoten nach Energie sortieren (absteigend)
        keep_nodes = np.argsort(-node_energy)[:n_target]

        print("\nOptimierungsziel:", self.target_mass_frac * 100, "% verbleibende Knoten")
        print("Behaltene Knoten (höchste Energie):")
        print(keep_nodes)
