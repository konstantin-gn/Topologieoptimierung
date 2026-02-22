import numpy as np
import numpy.typing as npt


class LinearSolver:
    # Konstruktor mit Regularisierungsparameter
    def __init__(self, eps: float = 1e-9):
        self.eps = eps  # Kleine Diagonalerhöhung zur Stabilisierung

    # Löst Ku = F unter Dirichlet-Randbedingungen
    def solve(
        self,
        K: npt.NDArray[np.float64],
        F: npt.NDArray[np.float64],
        u_fixed_idx: list[int]
    ) -> npt.NDArray[np.float64] | None:

        # Sicherheitsprüfung
        assert K.shape[0] == K.shape[1], "K muss quadratisch sein"
        assert K.shape[0] == F.shape[0], "Dimension von K und F muss übereinstimmen"

        # Kopien erzeugen, damit Originalsystem nicht verändert wird
        K_mod = K.copy()
        F_mod = F.copy()

        # Dirichlet-Randbedingungen einbauen
        for d in u_fixed_idx:
            K_mod[d, :] = 0.0
            K_mod[:, d] = 0.0
            K_mod[d, d] = 1.0
            F_mod[d] = 0.0

        # Direkt lösen
        try:
            return np.linalg.solve(K_mod, F_mod)

        # Falls Matrix singulär ist → Regularisierung
        except np.linalg.LinAlgError:
            K_mod += np.eye(K_mod.shape[0]) * self.eps
            try:
                return np.linalg.solve(K_mod, F_mod)
            except np.linalg.LinAlgError:
                return None
