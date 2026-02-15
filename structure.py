import numpy as np

# Federstruktur (2D-Gitter)
class Structure:

    def __init__(self, nx: int, ny: int, k: float = 1.0):
        self.nx = nx
        self.ny = ny
        self.k = k

        self.n_nodes = nx * ny
        self.ndof = 2 * self.n_nodes

        self.K_global = np.zeros((self.ndof, self.ndof))
        self.elements = []

        self._build_grid()

    def _node_id(self, ix, iy):
        return iy * self.nx + ix

    def _element_dofs(self, i, j):
        return [2*i, 2*i+1, 2*j, 2*j+1]

    def _add_element(self, i, j, direction):
        
        # Fügt ein Element zur globalen Matrix hinzu.
        
        K_local = self.k * np.array([[1, -1], [-1, 1]])
        O = np.outer(direction, direction)
        K_elem = np.kron(K_local, O)

        dofs = self._element_dofs(i, j)

        # Superposition
        for a in range(4):
            for b in range(4):
                self.K_global[dofs[a], dofs[b]] += K_elem[a, b]

        self.elements.append((i, j, K_elem, dofs))

    def _build_grid(self):
        
        # Baut ein Gitter mit horizontalen, vertikalen und diagonalen Federn auf.
        
        # Horizontal
        for iy in range(self.ny):
            for ix in range(self.nx - 1):
                i = self._node_id(ix, iy)
                j = self._node_id(ix + 1, iy)
                direction = np.array([1.0, 0.0])
                self._add_element(i, j, direction)

        # Vertikal
        for iy in range(self.ny - 1):
            for ix in range(self.nx):
                i = self._node_id(ix, iy)
                j = self._node_id(ix, iy + 1)
                direction = np.array([0.0, 1.0])
                self._add_element(i, j, direction)

        # Diagonal
        for iy in range(self.ny - 1):
            for ix in range(self.nx - 1):
                i = self._node_id(ix, iy)
                j = self._node_id(ix + 1, iy + 1)
                direction = np.array([1.0, 1.0]) / np.sqrt(2)
                self._add_element(i, j, direction)

        # Diagonal
        for iy in range(self.ny - 1):
            for ix in range(1, self.nx):
                i = self._node_id(ix, iy)
                j = self._node_id(ix - 1, iy + 1)
                direction = np.array([-1.0, 1.0]) / np.sqrt(2)
                self._add_element(i, j, direction)

    def compute_element_energies(self, u):
        
        # Berechnet die Energie jedes Elements.
        
        energies = []

        for (i, j, K_elem, dofs) in self.elements:
            u_e = u[dofs]
            c_e = 0.5 * u_e.T @ K_elem @ u_e
            energies.append((i, j, c_e))

        return energies

    def compute_node_energies(self, element_energies):
        
        # Verteilt Elementenergien gleichmäßig auf Knoten.
        
        node_energy = np.zeros(self.n_nodes)

        for (i, j, c_e) in element_energies:
            node_energy[i] += 0.5 * c_e
            node_energy[j] += 0.5 * c_e

        return node_energy
