import numpy as np


# Stellt die Struktur als Gitter aus Federelementen dar.
class MakeGrid:
    
    def __init__(self, nx: int, ny: int, k: float = 1.0):
        self.nx        = nx    # Anzahl Knoten in x-Richtung
        self.ny        = ny    # Anzahl Knoten in y-Richtung
        self.k         = k  # Federsteifigkeit 

        self.n_nodes   = nx * ny  # Gesamtzahl Knoten
        self.ndof      = 2 * self.n_nodes 

        self.K_global  = np.zeros((self.ndof, self.ndof))
        self.edge_list = []   # speichert (i,j)
        self.elements  = []   # speichert (i, j, K_elem, dofs)

        self._build_grid()
 
    def node_id(self, ix, iy):  
        return iy * self.nx + ix

    def element_dofs(self, i, j):
        return [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]

    # Fügt ein Federelement zwischen i und j hinzu, orientiert entlang direction (z.B. [1,0] horizontal).
    def _add_element(self, i, j, direction, k_factor=1.0):
        
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

        # Elementmatrix in globale K-Matrix einfügen
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

        # Diagonal rechts unten -> links oben
        for iy in range(self.ny - 1):
            for ix in range(self.nx - 1):
                i = self.node_id(ix, iy)
                j = self.node_id(ix + 1, iy + 1)
                self._add_element(i, j, np.array([1.0, 1.0]), k_factor=1 / np.sqrt(2))

        # Diagonal links unten -> rechts oben
        for iy in range(self.ny - 1):
            for ix in range(1, self.nx):
                i = self.node_id(ix, iy)
                j = self.node_id(ix - 1, iy + 1)
                self._add_element(i, j, np.array([-1.0, 1.0]), k_factor=1 / np.sqrt(2))

    # Baut die Matrix B (Knoten x Kanten).
    def build_incidence_matrix(self):
        
        n_edges = len(self.edge_list)
        B = np.zeros((self.n_nodes, n_edges))

        for e, (i, j) in enumerate(self.edge_list):
            B[i, e] =  1.0
            B[j, e] = -1.0

        return B