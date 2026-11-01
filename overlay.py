import tkinter as tk

class JoystickOverlay:
    def __init__(self, size=150, deadzone_ratio=0.04, max_reach=0.2):
        self.size = size
        self.center = size // 2
        self.max_reach = max_reach 
        
        self.root = tk.Tk()
        self.root.overrideredirect(True)

        # Always Above Other Windows
        self.root.wm_attributes("-topmost", True)

        # Transparent background
        self.root.wm_attributes("-transparentcolor", "black") 
        
        # Positioning: Bottom Right of the screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"{size}x{size}+{screen_w - size - 50}+{screen_h - size - 150}")
        
        self.canvas = tk.Canvas(self.root, width=size, height=size, bg="black", highlightthickness=0)
        self.canvas.pack()
        
        # Deadzone size
        dz_radius = int((deadzone_ratio / max_reach) * (size / 2))
        
        # HUD Limits
        self.canvas.create_oval(2, 2, size-2, size-2, outline="gray", dash=(1, 3))
        
        # Deadzone Circle
        self.canvas.create_oval(
            self.center - dz_radius, self.center - dz_radius,
            self.center + dz_radius, self.center + dz_radius,
            outline="white"
        )
        
        # Central Indicator
        self.canvas.create_oval(self.center - 2, self.center - 2, self.center + 2, self.center + 2, fill="white")
        
        # Point for the nose
        self.nose_indicator = self.canvas.create_oval(
            self.center - 6, self.center - 6,
            self.center + 6, self.center + 6,
            fill="lime", outline="green"
        )

    def update(self, dx, dy, in_deadzone):

        # Changing colors when moving or not moving the cursor
        color = "lime" if in_deadzone else "orange"
        self.canvas.itemconfig(self.nose_indicator, fill=color)
        
        # Mapping dx/dy traversal in pixel coordinates
        px_x = self.center + (dx / self.max_reach) * (self.size / 2)
        px_y = self.center + (dy / self.max_reach) * (self.size / 2)
        
        # C
        px_x = max(6, min(self.size - 6, px_x))
        px_y = max(6, min(self.size - 6, px_y))
        
        self.canvas.coords(
            self.nose_indicator,
            px_x - 6, px_y - 6,
            px_x + 6, px_y + 6
        )
        
        # Redrawing
        self.root.update()
        
    def close(self):
        self.root.destroy()