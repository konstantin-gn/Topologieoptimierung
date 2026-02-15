import numpy as np
from solver import LinearSolver
from structure import Structure


def main():

    nx, ny = 4, 4

    # Struktur erzeugen
    structure = Structure(nx, ny)

    K = structure.K_global
    ndof = structure.ndof

    # Lastvektor
    F = np.zeros(ndof)
    load_node = structure.n_nodes - 1
    F[2 * load_node] = 10.0

    # Linke Seite fixieren
    u_fixed_idx = []
    for iy in range(ny):
        node = iy * nx
        u_fixed_idx += [2*node, 2*node+1]

    # Solver erzeugen
    solver = LinearSolver()

    # System lösen
    u = solver.solve(K, F, u_fixed_idx)

    if u is None:
        print("System could not be solved.")
        return

    # Gesamtenergie
    total_energy = 0.5 * u.T @ K @ u
    print("Total energy:", total_energy)

    # Element- und Knotenenergie
    element_energies = structure.compute_element_energies(u)
    node_energy = structure.compute_node_energies(element_energies)

    print("\nNode energies:")
    print(node_energy.reshape((ny, nx))[::-1, :])


if __name__ == "__main__":
    main()
