import numpy as np
import numpy.typing as npt


# Solver für lineare Gleichungssysteme mit Dirichlet-Randbedingungen
class LinearSolver:

    def __init__(self, eps: float = 1e-9):
        self.eps = eps

    # Löst K u = F mit Dirichlet-Randbedingungen
    # Randbedingungen werden durch Modifikation von K und F umgesetzt.
    # Bei Singularität wird eine kleine Regularisierung (eps*I) versucht.
    def solve(
        self,
        K: npt.NDArray[np.float64],
        F: npt.NDArray[np.float64],
        u_fixed_idx: list[int],
        ) -> npt.NDArray[np.float64] | None:
        
        K_mod = K.copy()
        F_mod = F.copy()

        # DOFs mit festen Verschiebungen auf u=0 setzen
        for d in u_fixed_idx:
            K_mod[d, :] = 0.0
            K_mod[:, d] = 0.0
            K_mod[d, d] = 1.0
            F_mod[d] = 0.0

        try:
            return np.linalg.solve(K_mod, F_mod) 
        except np.linalg.LinAlgError:

            # Regularisierung gegen Singularität (z.B. bei Mechanismus)
            K_mod += np.eye(K.shape[0]) * self.eps
            try:
                return np.linalg.solve(K_mod, F_mod) 
            except np.linalg.LinAlgError:
                return None