from simulation import Simulation


if __name__ == "__main__":

    # Beispielwerte 
    nx = 10
    ny = 4
    target_mass_frac = 0.4

    sim = Simulation(nx, ny, target_mass_frac)
    sim.run()
