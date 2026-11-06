import tkinter as tk
from tkinter import messagebox

import FreeCAD as App
import Part


def create_cube():
    doc = App.newDocument("Cube")

    cube = Part.makeBox(25, 25, 25)
    Part.show(cube)

    doc.recompute()

    output_file = r"C:\Users\weshu\OneDrive\Desktop\IMPACT 2026\cube.FCStd"
    doc.saveAs(output_file)

    messagebox.showinfo(
        "Success",
        f"Saved:\n{output_file}"
    )


root = tk.Tk()
root.title("FreeCAD Cube Generator")
root.geometry("300x150")

label = tk.Label(root, text="Create a 25x25x25 mm cube")
label.pack(pady=15)

btn = tk.Button(root, text="Generate Cube", command=create_cube)
btn.pack(pady=10)

root.mainloop()