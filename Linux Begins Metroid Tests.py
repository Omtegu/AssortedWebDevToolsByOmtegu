import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import json
import uuid

BGM_TRACKS = [
    "bgm_Title", "bgm_Samus_Entrance", "bgm_Item_Get", "bgm_Brinstar", "bgm_Norfair",
    "bgm_Norfair_SM", "bgm_Kraid", "bgm_Crateria_Surface", "bgm_Crateria_Depths", "bgm_Ridley",
    "bgm_Tourian", "bgm_Brinstar_Overgrowth", "bgm_Brinstar_Red_Soil", "bgm_Lower_Norfair",
    "bgm_Mother_Brain", "bgm_Ending", "bgm_Mission_Report", "bgm_Minor_Item_Get", "bgm_Wrecked_Ship",
    "bgm_Item_Room", "bgm_Escape", "bgm_Miniboss2", "bgm_Kraid_Boss", "bgm_Ridley_Boss",
    "bgm_Mother_Brain_Boss", "bgm_Miniboss", "bgm_Ambience", "bgm_Crateria_Space_Pirates"
]

ITEMS = {
    0: "Energy Drop", 1: "Long Beam", 2: "Charge Beam", 3: "Ice Beam", 4: "Wave Beam",
    5: "Spazer Beam", 6: "Plasma Beam", 7: "Energy Tank", 8: "Varia Suit", 9: "Gravity Suit",
    10: "Morph Ball", 11: "Spring Ball", 12: "Boost Ball", 13: "Spider Ball", 14: "Bombs",
    15: "Power Bombs", 16: "Missiles", 17: "Super Missiles", 18: "High Jump Boots",
    19: "Space Jump", 20: "Speed Booster", 21: "Screw Attack", 22: "Sensor Visor",
    23: "Thermal Visor", 24: "X-Ray Visor", 25: "Refill", 26: "Power Grip", 27: "Grapple Beam",
    28: "Unknown", 29: "Unknown", 30: "Surge Core", 31: "Aegis Core", 32: "Crystal Core",
    33: "Magnet Core", 34: "Phazon Core"
}

class RoomEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Metroid Room Editor")
        self.dark_mode = False
        self.grid_size = 40
        self.cell_size = 20
        self.grid_data = {}
        self.loaded_room = None
        self.show_ids = False
        self.next_door_id = 0
        self.room_counter = 0
        self.current_area = 1
        self.hover_preview = None
        self.elevators = []
        
        self.world_data = {
            "id": 45644296059790,
            "name": "LUCINA",
            "name_full": "LUCINA - DEMO 2",
            "stats": {
                "size": 2,
                "world_w": 38,
                "world_h": 38,
                "screens": 0,
                "rooms": 0,
                "style": 3,
                "items": 0,
                "areas": 3,
                "bosses": 0,
                "cores": 1,
                "focus": -1,
                "hazard_runs": 0,
                "progression": 1,
                "ship_hints": 1
            },
            "version": 0.75,
            "world_version": 1,
            "GENERAL": {
                "world_w": 38,
                "world_h": 38,
                "total_enemies": 0,
                "total_objects": 0,
                "total_doors": 0,
                "total_blocks": 0,
                "escape": {
                    "dynamic_music": 1,
                    "halfway_point": 70,
                    "time": 215
                },
                "gate_bosses": [],
                "areas": [
                    {"name": "CRATERIA", "color": "#F0F0F0", "bgm": "bgm_Ambience"},
                    {"name": "BRINSTAR", "color": "#F0F0F0", "bgm": "bgm_Brinstar"},
                    {"name": "NORFAIR", "color": "#F0F0F0", "bgm": "bgm_Norfair"},
                    {"name": "WRECKED", "color": "#F0F0F0", "bgm": "bgm_Wrecked_Ship"},
                    {"name": "KRAID", "color": "#F0F0F0", "bgm": "bgm_Ambience"},
                    {"name": "TOURIAN", "color": "#F0F0F0", "bgm": "bgm_Tourian"},
                    {"name": "RIDLEY", "color": "#F0F0F0", "bgm": "bgm_Crateria_Surface"}
                ],
                "spawns": [],
                "MAP_ELEVATORS": []
            },
            "ROOMS": []
        }

        self.setup_ui()
        self.toggle_theme()

    def setup_ui(self):
        self.root.geometry("900x800")
        self.root.minsize(800, 600)
        
        self.toolbar = ttk.Frame(self.root)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        
        self.canvas = tk.Canvas(self.root, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        buttons = [
            ("Import Room", self.import_room),
            ("Export World", self.export_world),
            ("Edit World", self.edit_world_dialog),
            ("Theme", self.toggle_theme),
            ("Show Spawns", self.show_spawns)
        ]
        
        for text, cmd in buttons:
            btn = ttk.Button(self.toolbar, text=text, command=cmd)
            btn.pack(side=tk.LEFT, padx=2, pady=2)

        self.canvas.bind("<Motion>", self.update_preview)
        self.canvas.bind("<Button-1>", self.place_room)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        self.draw_grid()

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        bg = "#2d2d2d" if self.dark_mode else "white"
        fg = "#ffffff" if self.dark_mode else "#000000"
        
        self.canvas.config(bg=bg)
        for item in self.canvas.find_withtag("grid"):
            self.canvas.itemconfig(item, outline=fg)
        
        self.refresh_canvas()

    def draw_grid(self):
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                self.canvas.create_rectangle(
                    x * self.cell_size, y * self.cell_size,
                    (x + 1) * self.cell_size, (y + 1) * self.cell_size,
                    outline="#666666" if self.dark_mode else "#e0e0e0",
                    tags="grid"
                )

    def import_room(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not path:
            return
        
        try:
            with open(path, "r") as f:
                room = json.load(f)
                self.validate_room(room)
                self.loaded_room = room
                self.configure_room(room)
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def validate_room(self, room):
        if "GENERAL" not in room or "SCREENS" not in room:
            raise ValueError("Invalid room format")
        
        # Add META if missing
        if "META" not in room:
            room["META"] = {
                "id": str(uuid.uuid4().int)[:16],
                "content_version": 1,
                "landsite": 0,
                "boss": -1
            }
        
        # Convert door positions from numbers to direction strings
        door_pos_map = {1: "right", 2: "up", 3: "left", 4: "bottom"}
        for screen in room["SCREENS"]:
            # Remove PATHING if present
            screen.pop("PATHING", None)
            
            for door in screen.get("DOORS", []):
                num_pos = door.get("pos")
                if num_pos in door_pos_map:
                    door["pos"] = door_pos_map[num_pos]

    def configure_room(self, room):
        win = tk.Toplevel(self.root)
        win.title("Room Configuration")
        
        # Area selection
        ttk.Label(win, text="Area:").grid(row=0, column=0)
        area_var = tk.IntVar(value=room["GENERAL"].get("area", 1))
        ttk.Spinbox(win, from_=1, to=7, textvariable=area_var).grid(row=0, column=1)
        
        # Music selection
        ttk.Label(win, text="BGM:").grid(row=0, column=2)
        bgm_var = tk.StringVar(value=room["GENERAL"].get("bgm", ""))
        ttk.Combobox(win, textvariable=bgm_var, values=BGM_TRACKS).grid(row=0, column=3)
        
        # Item configuration
        items = [obj for screen in room["SCREENS"] for obj in screen["OBJECTS"] if "item" in obj]
        item_vars = []
        # Create reverse mapping from item names to IDs
        ITEMS_REVERSE = {v: k for k, v in ITEMS.items()}
        item_names = list(ITEMS.values())
        
        for idx, obj in enumerate(items):
            frame = ttk.Frame(win)
            frame.grid(row=idx + 1, column=0, columnspan=4, sticky="w")
            ttk.Label(frame, text=f"Item {idx + 1}:").pack(side=tk.LEFT)
            
            current_name = ITEMS.get(obj["item"], "Unknown")
            var = tk.StringVar(value=current_name)
            
            combobox = ttk.Combobox(frame, textvariable=var, values=item_names, width=20)
            combobox.pack(side=tk.LEFT)
            item_vars.append((obj, var))

        def save():
            room["GENERAL"]["area"] = area_var.get()
            room["GENERAL"]["bgm"] = bgm_var.get()
            # Propagate area to all screens in the room
            for screen in room["SCREENS"]:
                screen["MAP"] = screen.get("MAP", {})
                screen["MAP"]["area"] = area_var.get()
            for obj, var in item_vars:
                selected_name = var.get()
                obj["item"] = ITEMS_REVERSE.get(selected_name, 28)  # Default to Unknown
                
            win.destroy()
            messagebox.showinfo("Ready", "Room configured")

        ttk.Button(win, text="Save", command=save).grid(row=len(items) + 2, columnspan=4)

    def update_preview(self, event):
        if not self.loaded_room:
            return
        
        self.canvas.delete("preview")
        x = event.x // self.cell_size
        y = event.y // self.cell_size
        
        for screen in self.loaded_room["SCREENS"]:
            sx = x + (screen["x"] - 4)
            sy = y + (screen["y"] - 4)
            self.draw_room_preview(sx, sy, screen)

    def draw_room_preview(self, x, y, screen):
        x1 = x * self.cell_size + 2
        y1 = y * self.cell_size + 2
        x2 = (x + 1) * self.cell_size - 2
        y2 = (y + 1) * self.cell_size - 2
        
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#00ff00" if self.dark_mode else "#009900",
            dash=(2, 4), tags="preview"
        )
        
        # Draw doors in preview
        for door in screen.get("DOORS", []):
            door_type = door.get("type", 1)
            door_color = "#FF0000" if door_type == 2 else "#0000FF"
            pos = door.get("pos", "")
            door_size = 5  # Preview door size
            
            if pos == "left":
                dx1 = x1
                dy1 = (y1 + y2) // 2 - door_size
                dx2 = dx1 + door_size
                dy2 = dy1 + 2 * door_size
            elif pos == "right":
                dx1 = x2 - door_size
                dy1 = (y1 + y2) // 2 - door_size
                dx2 = dx1 + door_size
                dy2 = dy1 + 2 * door_size
            elif pos == "up":
                dx1 = (x1 + x2) // 2 - door_size
                dy1 = y1
                dx2 = dx1 + 2 * door_size
                dy2 = dy1 + door_size
            elif pos == "bottom":
                dx1 = (x1 + x2) // 2 - door_size
                dy1 = y2 - door_size
                dx2 = dx1 + 2 * door_size
                dy2 = dy1 + door_size
            else:
                continue
            
            self.canvas.create_rectangle(dx1, dy1, dx2, dy2, fill=door_color, tags="preview")

    def place_room(self, event):
        if not self.loaded_room:
            return
        
        x = event.x // self.cell_size
        y = event.y // self.cell_size
        
        # Check screen collisions
        collision = False
        for screen in self.loaded_room["SCREENS"]:
            sx = x + (screen["x"] - 4)
            sy = y + (screen["y"] - 4)
            if (sx, sy) in self.grid_data:
                collision = True
                break
        
        if collision:
            messagebox.showerror("Collision", "Overlapping screens!")
            return
            
        room_id = self.room_counter
        self.room_counter += 1
        
        # Add required meta fields
        self.loaded_room.setdefault("META", {}).update({
            "id": str(uuid.uuid4().int)[:16],
            "content_version": 1,
            "landsite": 0,
            "boss": -1
        })
        
        self.loaded_room["room_id"] = room_id
        self.loaded_room["GENERAL"]["world_x"] = x
        self.loaded_room["GENERAL"]["world_y"] = y

        for screen in self.loaded_room["SCREENS"]:
            sx = x + (screen["x"] - 4)
            sy = y + (screen["y"] - 4)
            screen["world_x"] = sx
            screen["world_y"] = sy
            screen["room_id"] = room_id
            self.grid_data[(sx, sy)] = screen
            
            # Process doors
            for door in screen.get("DOORS", []):
                door["id"] = self.next_door_id
                self.next_door_id += 1

        self.update_world_stats()
        self.connect_doors()
        self.process_special_objects()
        self.world_data["ROOMS"].append(self.loaded_room)
        self.refresh_canvas()
        self.loaded_room = None

    def update_world_stats(self):
        self.world_data["stats"]["rooms"] += 1
        screens = len(self.loaded_room["SCREENS"])
        self.world_data["stats"]["screens"] += screens
        self.world_data["stats"]["items"] += sum(
            1 for s in self.loaded_room["SCREENS"] 
            for o in s["OBJECTS"] if "item" in o
        )
        self.world_data["GENERAL"]["total_doors"] += sum(
            len(s["DOORS"]) for s in self.loaded_room["SCREENS"]
        )

    def connect_doors(self):
        for screen in self.loaded_room["SCREENS"]:
            x = screen["world_x"]
            y = screen["world_y"]
            
            # Updated neighbor mapping to use direction strings:
            # Right: current door "right" connects with neighbor's "left"
            # Left: current door "left" connects with neighbor's "right"
            # Bottom: current door "bottom" connects with neighbor's "up"
            # Up: current door "up" connects with neighbor's "bottom"
            neighbors = {
                (x + 1, y): "right",
                (x - 1, y): "left",
                (x, y + 1): "bottom",
                (x, y - 1): "up"
            }
            
            for (nx, ny), direction in neighbors.items():
                if (nx, ny) in self.grid_data:
                    adj_screen = self.grid_data[(nx, ny)]
                    self.link_doors(screen, adj_screen, direction)

    def link_doors(self, screen, adj_screen, direction):
        reverse_dir = {"left": "right", "right": "left", "up": "bottom", "bottom": "up"}
        
        for door in screen.get("DOORS", []):
            if door.get("pos") == direction:
                for adj_door in adj_screen.get("DOORS", []):
                    if adj_door.get("pos") == reverse_dir[direction]:
                        door["dest_rm"] = adj_screen["room_id"]
                        door["dest_id"] = adj_door["id"]
                        adj_door["dest_rm"] = screen["room_id"]
                        adj_door["dest_id"] = door["id"]

    def process_special_objects(self):
        if any(obj["type"] == 1 
               for s in self.loaded_room["SCREENS"] 
               for obj in s["OBJECTS"]):
            self.add_spawn("GUNSHIP")
            
        for screen in self.loaded_room["SCREENS"]:
            if screen.get("ELEVATORS"):
                self.elevators.append({
                    "x": screen["world_x"],
                    "y": screen["world_y"],
                    "dest_area": self.loaded_room["GENERAL"]["area"]
                })

    def add_spawn(self, spawn_type):
        spawn = {
            "world_x": self.loaded_room["GENERAL"]["world_x"],
            "world_y": self.loaded_room["GENERAL"]["world_y"],
            "x": 0,
            "y": 152,
            "name": spawn_type,
            "area": self.loaded_room["GENERAL"]["area"],
            "screen_n": 0,
            "room_id": self.loaded_room["room_id"],
            "type": 1
        }
        self.world_data["GENERAL"]["spawns"].append(spawn)

    def refresh_canvas(self):
        self.canvas.delete("room")
        for (x, y), screen in self.grid_data.items():
            self.draw_screen(x, y, screen)

    def draw_screen(self, x, y, screen):
        area_id = screen.get("MAP", {}).get("area", 1) - 1
        color = self.world_data["GENERAL"]["areas"][area_id]["color"]
        
        x1 = x * self.cell_size
        y1 = y * self.cell_size
        x2 = x1 + self.cell_size
        y2 = y1 + self.cell_size
        
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, tags="room")
        
        # Draw doors (FIXED: Type 1 now blue)
        for door in screen.get("DOORS", []):
            door_color = "#FF0000" if door.get("type") == 2 else "#0000FF"  # Blue for type 1
            door_size = self.cell_size // 4
            
            if door["pos"] == "left":
                self.canvas.create_rectangle(
                    x1, y1 + self.cell_size // 2 - door_size,
                    x1 + door_size, y1 + self.cell_size // 2 + door_size,
                    fill=door_color, tags="door"
                )
            elif door["pos"] == "right":
                self.canvas.create_rectangle(
                    x1 + self.cell_size - door_size, y1 + self.cell_size // 2 - door_size,
                    x1 + self.cell_size, y1 + self.cell_size // 2 + door_size,
                    fill=door_color, tags="door"
                )
            elif door["pos"] == "up":
                self.canvas.create_rectangle(
                    x1 + self.cell_size // 2 - door_size, y1,
                    x1 + self.cell_size // 2 + door_size, y1 + door_size,
                    fill=door_color, tags="door"
                )
            elif door["pos"] == "bottom":
                self.canvas.create_rectangle(
                    x1 + self.cell_size // 2 - door_size, y2 - door_size,
                    x1 + self.cell_size // 2 + door_size, y2,
                    fill=door_color, tags="door"
                )

        # Draw elevator markers
        if screen.get("ELEVATORS"):
            self.canvas.create_rectangle(x1 + 4, y1 + 4, x2 - 4, y2 - 4,
                                         outline="#00FFFF" if self.dark_mode else "#009999",
                                         width=2, tags="room")

    def show_context_menu(self, event):
        x = event.x // self.cell_size
        y = event.y // self.cell_size
        
        if (x, y) not in self.grid_data:
            return
            
        screen = self.grid_data[(x, y)]
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Edit Room", command=lambda: self.edit_room(screen))
        menu.add_command(label="Delete Room", command=lambda: self.delete_room(x, y))
        menu.tk_popup(event.x_root, event.y_root)

    def edit_room(self, screen):
        win = tk.Toplevel(self.root)
        win.title("Edit Room")
        
        # Item editing
        items = [obj for obj in screen.get("OBJECTS", []) if "item" in obj]
        for idx, obj in enumerate(items):
            frame = ttk.Frame(win)
            frame.grid(row=idx, column=0, sticky="w")
            ttk.Label(frame, text=f"Item {idx + 1}:").pack(side=tk.LEFT)
            var = tk.StringVar(value=str(obj["item"]))
            ttk.Combobox(frame, textvariable=var, values=list(ITEMS.keys())).pack(side=tk.LEFT)
            ttk.Label(frame, text=ITEMS.get(obj["item"], "Unknown")).pack(side=tk.LEFT)

        def save():
            for idx, obj in enumerate(items):
                obj["item"] = int(var.get())
            self.refresh_canvas()
            win.destroy()
            
        ttk.Button(win, text="Save", command=save).grid(row=len(items) + 1, columnspan=2)

    def delete_room(self, x, y):
        if messagebox.askyesno("Confirm", "Delete this room?"):
            del self.grid_data[(x, y)]
            self.world_data["ROOMS"] = [r for r in self.world_data["ROOMS"] 
                                        if r["room_id"] != self.grid_data.get((x, y), {}).get("room_id")]
            self.refresh_canvas()

    def edit_world_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("World Settings")
        
        ttk.Label(win, text="World Name:").grid(row=0, column=0)
        name_var = tk.StringVar(value=self.world_data["name"])
        ttk.Entry(win, textvariable=name_var).grid(row=0, column=1)
        
        ttk.Label(win, text="Areas:").grid(row=1, column=0)
        area_vars = []
        for idx, area in enumerate(self.world_data["GENERAL"]["areas"]):
            ttk.Label(win, text=area["name"]).grid(row=idx + 2, column=0)
            color_btn = ttk.Button(win, text="Color", 
                                   command=lambda i=idx: self.set_area_color(i))
            color_btn.grid(row=idx + 2, column=1)
            bgm_var = tk.StringVar(value=area["bgm"])
            ttk.Combobox(win, textvariable=bgm_var, values=BGM_TRACKS).grid(row=idx + 2, column=2)
            area_vars.append((color_btn, bgm_var))

        def save():
            self.world_data["name"] = name_var.get()
            for idx, (_, bgm_var) in enumerate(area_vars):
                self.world_data["GENERAL"]["areas"][idx]["bgm"] = bgm_var.get()
            win.destroy()
        
        ttk.Button(win, text="Save", command=save).grid(row=10, columnspan=3)

    def set_area_color(self, idx):
        color = colorchooser.askcolor(title="Choose Area Color")[1]
        if color:
            self.world_data["GENERAL"]["areas"][idx]["color"] = color
            self.refresh_canvas()

    def export_world(self):
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if not path:
            return
            
        try:
            # Convert door positions back to numbers
            door_pos_map = {"right": 1, "up": 2, "left": 3, "bottom": 4}
            for room in self.world_data["ROOMS"]:
                for screen in room["SCREENS"]:
                    for door in screen.get("DOORS", []):
                        str_pos = door.get("pos")
                        if str_pos in door_pos_map:
                            door["pos"] = door_pos_map[str_pos]

            # Finalize world data
            self.world_data["GENERAL"]["MAP_ELEVATORS"] = self.elevators
            self.world_data["stats"].update({
                "screens": sum(len(r["SCREENS"]) for r in self.world_data["ROOMS"]),
                "rooms": len(self.world_data["ROOMS"]),
                "items": sum(1 for r in self.world_data["ROOMS"] 
                            for s in r["SCREENS"] 
                            for o in s["OBJECTS"] if "item" in o)
            })
            
            with open(path, "w") as f:
                json.dump(self.world_data, f, indent=4, ensure_ascii=False)
                
            messagebox.showinfo("Success", "World exported successfully!")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def show_spawns(self):
        self.canvas.delete("spawns")
        for spawn in self.world_data["GENERAL"]["spawns"]:
            x = spawn["world_x"]
            y = spawn["world_y"]
            self.canvas.create_oval(
                x * self.cell_size + 8, y * self.cell_size + 8,
                (x + 1) * self.cell_size - 8, (y + 1) * self.cell_size - 8,
                outline="#FF0000", width=2, tags="spawns"
            )

if __name__ == "__main__":
    root = tk.Tk()
    app = RoomEditorApp(root)
    root.mainloop()

