import numpy as np
import numpy.typing as npt


class LinearSolver:
    """
    Reiner numerischer Solver für lineare Gleichungssysteme:
        K u = F

    Der Solver kennt keine Struktur, keine Elemente und keine UI.
    """

    def __init__(self, eps: float = 1e-9) -> None:
        """
        eps : Regularisierungsparameter für singuläre Matrizen.
        """
        self.eps = eps

    def solve(
        self,
        K: npt.NDArray[np.float64],
        F: npt.NDArray[np.float64],
        u_fixed_idx: list[int],
    ) -> npt.NDArray[np.float64] | None:
        """
        Löst Ku = F unter Berücksichtigung von Dirichlet-Randbedingungen.
        """

        # Sicherheitsprüfungen
        assert K.shape[0] == K.shape[1], \
            "Stiffness matrix K must be square."
        assert K.shape[0] == F.shape[0], \
            "Force vector F must have the same size as K."

        # Kopien erzeugen, damit Originalmatrix unverändert bleibt
        K_mod = K.copy()
        F_mod = F.copy()

        # Randbedingungen einbauen
        for d in u_fixed_idx:
            K_mod[d, :] = 0.0
            K_mod[:, d] = 0.0
            K_mod[d, d] = 1.0
            F_mod[d] = 0.0

        # Direkt lösen
        try:
            return np.linalg.solve(K_mod, F_mod)

        except np.linalg.LinAlgError:
            # Regularisierung falls singulär
            K_mod += np.eye(K_mod.shape[0]) * self.eps
            try:
                return np.linalg.solve(K_mod, F_mod)
            except np.linalg.LinAlgError:
                return None
