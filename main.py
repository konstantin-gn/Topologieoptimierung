from user_input import UserInput
from simulation import Simulation


def main():
    ui = UserInput()
    ui.get_input()

    sim = Simulation(
        ui.nx, ui.ny,
        ui.target_mass_frac,
        ui.load_ix, ui.load_iy,
        ui.Fx, ui.Fy,
    )
    sim.run()


if __name__ == "__main__":
    main()