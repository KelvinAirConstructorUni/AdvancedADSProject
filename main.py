import tkinter as tk
import heapq

# --- Backend ---
rooms = {"Room A": 2, "Room B": 3, "Room C": 4}
time_slots = ["9AM", "10AM", "2PM", "3PM"]
student_list = []

class CreateToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y = self.widget.winfo_rootx()+20, self.widget.winfo_rooty()+20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(
            tw,
            text=self.text,
            justify='left',
            background="#ffffe0",  # light yellow
            foreground="black",     # text color black
            relief='solid',
            borderwidth=1,
            font=("tahoma", "10", "normal")
        )
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


class Node:
    def __init__(self, schedule=None, g=0):
        self.schedule = schedule or {}
        self.g = g
        self.h = 0
        self.f = 0
    def __lt__(self, other):
        return self.f < other.f

def calculate_g(schedule):
    conflicts = 0
    for student, (time, room) in schedule.items():
        student_info = next(s for s in student_list if s["name"] == student)
        if time not in student_info["time_slot"]:
            conflicts += 1
    room_count = {}
    for _, (_, room) in schedule.items():
        room_count[room] = room_count.get(room, 0) + 1
    overcrowding = sum(max(0, room_count[r] - rooms[r]) for r in room_count)
    return conflicts + overcrowding

def calculate_h(schedule):
    remaining = [s for s in student_list if s["name"] not in schedule]
    h = 0
    for s in remaining:
        if not s["time_slot"]:
            h += 1
    return h

def a_star_schedule():
    open_list = []
    start_node = Node(schedule={})
    start_node.g = 0
    start_node.h = calculate_h(start_node.schedule)
    start_node.f = start_node.g + start_node.h
    heapq.heappush(open_list, start_node)

    best_schedule = None
    best_cost = float("inf")

    while open_list:
        current = heapq.heappop(open_list)
        if len(current.schedule) == len(student_list):
            if current.g < best_cost:
                best_schedule = current.schedule
                best_cost = current.g
            continue

        next_student = next(s for s in student_list if s["name"] not in current.schedule)
        for time in next_student["time_slot"]:
            for room in rooms:
                new_schedule = current.schedule.copy()
                new_schedule[next_student["name"]] = (time, room)
                g = calculate_g(new_schedule)
                h = calculate_h(new_schedule)
                node = Node(new_schedule, g)
                node.h = h
                node.f = g + h
                heapq.heappush(open_list, node)

    return best_schedule, best_cost

# --- GUI ---
root = tk.Tk()
root.title("Group Study Scheduler (Visual Grid)")

# --- Input ---
tk.Label(root, text="Student name:").pack()
name_entry = tk.Entry(root)
name_entry.pack()

tk.Label(root, text="Available times (comma-separated):").pack()
time_entry = tk.Entry(root)
time_entry.pack()

tk.Label(root, text="Class/Room:").pack()
room_entry = tk.Entry(root)
room_entry.pack()

student_display = tk.Text(root, height=10, width=50)
student_display.pack(pady=5)

def update_student_display():
    student_display.delete("1.0", tk.END)
    for s in student_list:
        student_display.insert(tk.END, f"{s['name']} - {', '.join(s['time_slot'])} - {s['room']}\n")

def submit_student():
    name = name_entry.get().strip()
    times = [t.strip() for t in time_entry.get().split(",")]
    room = room_entry.get().strip()
    if not name or not times:
        return
    if any(s["name"] == name for s in student_list):
        return
    student_list.append({"name": name, "time_slot": times, "room": room})
    update_student_display()
    name_entry.delete(0, tk.END)
    time_entry.delete(0, tk.END)
    room_entry.delete(0, tk.END)

tk.Button(root, text="Add Student", command=submit_student).pack(pady=2)

# --- Grid for schedule visualization ---
grid_frame = tk.Frame(root)
grid_frame.pack(pady=10)

def run_scheduler():
    for widget in grid_frame.winfo_children():
        widget.destroy()  # clear previous grid

    if not student_list:
        return

    schedule, cost = a_star_schedule()
    if not schedule:
        tk.Label(grid_frame, text="No valid schedule found").grid()
        return

    # Count students per room
    room_count = {}
    for student, (time, room) in schedule.items():
        room_count[room] = room_count.get(room, 0) + 1

    # Header row (time slots)
    tk.Label(grid_frame, text="Student / Time").grid(row=0, column=0, padx=5, pady=2)
    for j, t in enumerate(time_slots):
        tk.Label(grid_frame, text=t).grid(row=0, column=j+1, padx=5, pady=2)

    # Fill grid
    for i, s in enumerate(student_list):
        tk.Label(grid_frame, text=s["name"]).grid(row=i + 1, column=0, padx=5, pady=2)
        for j, t in enumerate(time_slots):
            cell_text = ""
            bg_color = "white"
            tooltip_text = ""
            if s["name"] in schedule:
                assigned_time, assigned_room = schedule[s["name"]]
                if t == assigned_time:
                    cell_text = assigned_room
                    if t not in s["time_slot"]:
                        bg_color = "red"
                        tooltip_text = "⚠️ Student cannot attend this time"
                    elif room_count[assigned_room] > rooms[assigned_room]:
                        bg_color = "orange"
                        tooltip_text = "🔶 Room overcrowded"
                    else:
                        bg_color = "lightgreen"
                        tooltip_text = "✅ Student scheduled here"
            label = tk.Label(grid_frame, text=cell_text, width=12, bg=bg_color, relief="ridge")
            label.grid(row=i + 1, column=j + 1, padx=2, pady=2)
            if tooltip_text:
                CreateToolTip(label, tooltip_text)

    # Show total conflict score
    tk.Label(grid_frame, text=f"Total Conflict Score: {cost}").grid(row=len(student_list)+1, column=0, columnspan=len(time_slots)+1, pady=5)

tk.Button(root, text="Run Scheduler (Visual A*)", command=run_scheduler).pack(pady=5)
root.mainloop()
