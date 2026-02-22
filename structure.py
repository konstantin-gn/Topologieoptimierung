import numpy as np


class Structure:
    # Erstellt ein 2D-Gitter aus Federn
    def __init__(self, nx: int, ny: int, k: float = 1.0):
        self.nx = nx
        self.ny = ny
        self.k = k

        self.n_nodes = nx * ny
        self.ndof = 2 * self.n_nodes

        # Globale Steifigkeitsmatrix
        self.K_global = np.zeros((self.ndof, self.ndof))

        # Liste aller Elemente
        self.elements = []

        # Gitter sofort aufbauen
        self._build_structure()

    # Knotennummerierung (Ursprung links oben)
    def node_id(self, ix, iy):
        return (self.ny - 1 - iy) * self.nx + ix

    # Freiheitsgrade eines Elements
    def element_dofs(self, i, j):
        return [2*i, 2*i+1, 2*j, 2*j+1]

    # Element zur globalen Matrix hinzufügen
    def _add_element(self, i, j, direction):

        # Lokale 1D-Feder
        K_local = self.k * np.array([[1, -1], [-1, 1]])

        # Richtungsvektor normieren
        e_n = direction / np.linalg.norm(direction)

        # Transformation in 2D
        O = np.outer(e_n, e_n)
        K_elem = np.kron(K_local, O)

        dofs = self.element_dofs(i, j)

        # Superposition in globale Matrix
        for a in range(4):
            for b in range(4):
                self.K_global[dofs[a], dofs[b]] += K_elem[a, b]

        # Element speichern
        self.elements.append((i, j, K_elem, dofs))

    # Baut horizontale, vertikale und diagonale Federn
    def _build_structure(self):

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

        # Diagonal
        for iy in range(self.ny - 1):
            for ix in range(self.nx - 1):
                i = self.node_id(ix, iy)
                j = self.node_id(ix + 1, iy + 1)
                self._add_element(i, j, np.array([1.0, 1.0]))

        # Diagonal
        for iy in range(self.ny - 1):
            for ix in range(1, self.nx):
                i = self.node_id(ix, iy)
                j = self.node_id(ix - 1, iy + 1)
                self._add_element(i, j, np.array([-1.0, 1.0]))

    # Berechnet Knotenenergie aus Verschiebungsvektor
    def compute_node_energy(self, u):

        node_energy = np.zeros(self.n_nodes)

        for (i, j, K_elem, dofs) in self.elements:
            u_e = u[dofs]
            c_e = 0.5 * u_e.T @ K_elem @ u_e

            # Energie gleichmäßig auf beide Knoten verteilen
            node_energy[i] += 0.5 * c_e
            node_energy[j] += 0.5 * c_e

        return node_energy
