# UserInput sammelt die Eingaben für die Simulation
class UserInput:
    def __init__(self):
        self.nx: int = 10
        self.ny: int = 4
        self.target_mass_frac: float = 0.4
        self.load_ix: int = 0
        self.load_iy: int = 0
        self.Fx: float = 0.0
        self.Fy: float = 0.0

    def get_input(self):
        print("Bitte die Größe des Balkens eingeben (Anzahl an Knoten)")

        while True: # Eingabe in Schleife, damit ungültige Eingaben nicht direkt zum Abbruch führen
            try:
                nx = int(input("Länge (in Knoten): "))
                ny = int(input("Höhe  (in Knoten): "))
                frac = float(input("Optimierungsgrad (Prozent der verbleibenden Masse, z.B. 40): "))
                print("\nKraftangriffspunkt eingeben:")

                ix = int(input(f"Knoten x (0 bis {nx-1}): "))
                iy = int(input(f"Knoten y (0 bis {ny-1}): "))

                Fx = float(input("Kraft in x-Richtung (positiv=rechts, negativ=links): "))
                Fy = float(input("Kraft in y-Richtung (positiv=unten, negativ=oben): "))

                if not (0 <= ix < nx and 0 <= iy < ny):
                    raise ValueError

                self.load_ix = ix
                self.load_iy = iy
                self.Fx = Fx
                self.Fy = Fy

                if nx <= 0 or ny <= 0 or not (0 < frac <= 100): # ungültige Werte für Größe oder Prozent
                    raise ValueError

                self.nx = nx
                self.ny = ny
                self.target_mass_frac = frac / 100
                break

            except ValueError:
                print("Ungültige Eingabe. Bitte ganze positive Zahlen für Größe und Prozent zwischen 1-100 eingeben.")