import matplotlib.pyplot as plt
import numpy as np


class StreamlitPlotter:

    def __init__(self, grid):
        self.grid = grid

    def plot_structure(self, active_nodes):

        fig, ax = plt.subplots()

        for i, j in self.grid.edge_list:

            if i not in active_nodes:
                continue

            if j not in active_nodes:
                continue

            x1 = i % self.grid.nx
            y1 = i // self.grid.nx

            x2 = j % self.grid.nx
            y2 = j // self.grid.nx

            ax.plot([x1, x2], [-y1, -y2], "black")

        ax.set_title("Optimierte Struktur")
        ax.set_aspect("equal")
        ax.grid()

        return fig


    def plot_deformation(self, active_nodes, u, scale=1.0):

        fig, ax = plt.subplots()

        for i, j in self.grid.edge_list:

            if i not in active_nodes:
                continue

            if j not in active_nodes:
                continue

            x1 = i % self.grid.nx
            y1 = i // self.grid.nx

            x2 = j % self.grid.nx
            y2 = j // self.grid.nx

            dx1 = scale * u[2*i]
            dy1 = scale * u[2*i+1]

            dx2 = scale * u[2*j]
            dy2 = scale * u[2*j+1]

            ax.plot(
                [x1+dx1, x2+dx2],
                [-y1-dy1, -y2-dy2],
                "red"
            )

        ax.set_title("Verformung")
        ax.set_aspect("equal")
        ax.grid()

        return fig