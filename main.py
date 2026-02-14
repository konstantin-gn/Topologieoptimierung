import numpy as np
import numpy.typing as npt

# Solver
def solve(K: npt.NDArray[np.float64],
          F: npt.NDArray[np.float64],
          u_fixed_idx: list[int],
          eps=1e-9) -> npt.NDArray[np.float64] | None:

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
        K_mod += np.eye(K.shape[0]) * eps
        try:
            return np.linalg.solve(K_mod, F_mod)
        except np.linalg.LinAlgError:
            return None

# Grid Builder mit diagonalen Federn
def build_grid(nx: int, ny: int, k: float = 1.0):

    n_nodes = nx * ny
    ndof = 2 * n_nodes
    K_global = np.zeros((ndof, ndof))
    elements = []

    def node_id(ix, iy):
        return iy * nx + ix

    def element_dofs(i, j):
        return [2*i, 2*i+1, 2*j, 2*j+1]

    K_local = k * np.array([[1, -1], [-1, 1]])

    # Horizontale Elemente
    for iy in range(ny):
        for ix in range(nx - 1):
            i = node_id(ix, iy)
            j = node_id(ix + 1, iy)
            e_n = np.array([1.0, 0.0])
            O = np.outer(e_n, e_n)
            K_elem = np.kron(K_local, O)
            dofs = element_dofs(i, j)
            for a in range(4):
                for b in range(4):
                    K_global[dofs[a], dofs[b]] += K_elem[a, b]
            elements.append((i, j, K_elem, dofs))

    # Vertikale Elemente
    for iy in range(ny - 1):
        for ix in range(nx):
            i = node_id(ix, iy)
            j = node_id(ix, iy + 1)
            e_n = np.array([0.0, 1.0])
            O = np.outer(e_n, e_n)
            K_elem = np.kron(K_local, O)
            dofs = element_dofs(i, j)
            for a in range(4):
                for b in range(4):
                    K_global[dofs[a], dofs[b]] += K_elem[a, b]
            elements.append((i, j, K_elem, dofs))

    # Diagonale Elemente (oben links → unten rechts)
    for iy in range(ny - 1):
        for ix in range(nx - 1):
            i = node_id(ix, iy)
            j = node_id(ix + 1, iy + 1)
            e_n = np.array([1.0, 1.0]) / np.sqrt(2)
            O = np.outer(e_n, e_n)
            K_elem = np.kron(K_local, O)
            dofs = element_dofs(i, j)
            for a in range(4):
                for b in range(4):
                    K_global[dofs[a], dofs[b]] += K_elem[a, b]
            elements.append((i, j, K_elem, dofs))

    # Diagonale Elemente (oben rechts → unten links)
    for iy in range(ny - 1):
        for ix in range(1, nx):
            i = node_id(ix, iy)
            j = node_id(ix - 1, iy + 1)
            e_n = np.array([-1.0, 1.0]) / np.sqrt(2)
            O = np.outer(e_n, e_n)
            K_elem = np.kron(K_local, O)
            dofs = element_dofs(i, j)
            for a in range(4):
                for b in range(4):
                    K_global[dofs[a], dofs[b]] += K_elem[a, b]
            elements.append((i, j, K_elem, dofs))

    return K_global, elements


# Matrix Ausgabe
def print_matrix(matrix, decimals=6):
    for row in matrix:
        print("  ".join(f"{val:.{decimals}f}" for val in row))

# Main Simulation
def main():
    nx, ny = 4, 4
    K, elements = build_grid(nx, ny)

    n_nodes = nx * ny
    ndof = 2 * n_nodes

    F = np.zeros(ndof)       # Lastvektor
    load_node = n_nodes - 1  # rechte obere Ecke -- Index des rechten oberen Knotens (Nummerierung geht von links unten nach rechts oben zeilenweise)
    F[2 * load_node] = 10.0  # x-Richtung der Kraft

    # Linke Seite fixieren
    u_fixed_idx = []
    for iy in range(ny):
        node = iy * nx
        u_fixed_idx += [2*node, 2*node+1]

    u = solve(K, F, u_fixed_idx)
    if u is None:
        print("System could not be solved.")
        return

    # Gesamtenergie
    total_energy = 0.5 * u.T @ K @ u
    print("Total energy:", total_energy)

    # Elementenergien
    element_energy_list = []
    for (i, j, K_elem, dofs) in elements:
        u_e = u[dofs]
        c_e = 0.5 * u_e.T @ K_elem @ u_e
        element_energy_list.append((i, j, c_e))

    # Knotenenergien
    node_energy = np.zeros(n_nodes)
    for (i, j, c_e) in element_energy_list:
        node_energy[i] += 0.5 * c_e
        node_energy[j] += 0.5 * c_e

    # Node-Energie als 2D-Matrix, obere Reihe oben
    node_energy_matrix = node_energy.reshape((ny, nx))[::-1, :]

    # Horizontale und vertikale Elementenergien als Raster
    element_energy_h = np.zeros((ny, nx-1))
    element_energy_v = np.zeros((ny-1, nx))
    for (i, j, c_e) in element_energy_list:
        xi, yi = i % nx, i // nx
        xj, yj = j % nx, j // nx
        if yi == yj:  # horizontal
            element_energy_h[yi, min(xi, xj)] = c_e
        elif xi == xj:  # vertikal
            element_energy_v[min(yi, yj), xi] = c_e
    element_energy_h = element_energy_h[::-1, :]
    element_energy_v = element_energy_v[::-1, :]

    # Ausgabe
    print("\nNode energy matrix (grid form, top row = top of grid):")
    print_matrix(node_energy_matrix)

    print("\nHorizontal element energy (grid form, top row = top of grid):")
    print_matrix(element_energy_h)

    print("\nVertical element energy (grid form, top row = top of grid):")
    print_matrix(element_energy_v)

if __name__ == "__main__":
    main()