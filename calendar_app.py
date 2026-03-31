import os, sqlite3, threading, time, sys, json, subprocess
from datetime import datetime
from tkinter import *
from tkinter import messagebox, ttk
from tkcalendar import Calendar
from plyer import notification
import socket

# windows-only extras
if os.name == "nt":
    import winsound
    import pystray
    from PIL import Image, ImageDraw, ImageTk

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ===============================
# Single instance logic
# ===============================
PORT = 50555
IS_PRIMARY = False

if os.name == "nt":
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", PORT))
        server.listen(1)
        IS_PRIMARY = True
    except OSError:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", PORT))
            s.send(b"SHOW")
            s.close()
        except:
            pass
        sys.exit(0)
else:
    IS_PRIMARY = True

# ===============================
# App folders & settings
# ===============================
APP_FOLDER = os.path.join(os.getenv("LOCALAPPDATA"), "ReminderApp")
os.makedirs(APP_FOLDER, exist_ok=True)

DB_FILE = os.path.join(APP_FOLDER, "reminders.db")
SETTINGS_FILE = os.path.join(APP_FOLDER, "settings.json")

DEFAULT_SETTINGS = {"theme": "dark"}

if not os.path.exists(SETTINGS_FILE):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(DEFAULT_SETTINGS, f)

with open(SETTINGS_FILE, "r") as f:
    SETTINGS = json.load(f)

# ===============================
# Database Setup (Main Thread)
# ===============================
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS reminders(
    id INTEGER PRIMARY KEY,
    datetime TEXT,
    text TEXT,
    status TEXT DEFAULT 'pending'
)
""")
conn.commit()

# ===============================
# UI Setup
# ===============================
root = Tk()
root.title("Qubify-IT's Prodlendar")
root.geometry("1000x650")

#Set Window and Taskbar Icon
try:
    root.iconbitmap(resource_path("icon.ico"))
except Exception:
    pass

# State variables
show_settings = False
show_list = False
EDIT_MODE = False
editing_id = None
selected_ids = set()

# Color Palettes
COLORS = {
    "dark": {
        "top_bar": "#000000",
        "bg": "#0e1621",        # Deep dark blue
        "fg": "#ffffff",
        "accent": "#2b5278",
        "card_bg": "#17212b",
        "input_bg": "#242f3d",
        "input_fg": "white"
    },
    "light": {
        "top_bar": "#ffffff",
        "bg": "#f0f0f0",        # Light Gray
        "fg": "#000000",
        "accent": "#e0e0e0",
        "card_bg": "#ffffff",
        "input_bg": "#ffffff",
        "input_fg": "black"
    }
}

# -------------------------------
# Theme Engine (FIXED)
# -------------------------------
def apply_theme():
    mode = SETTINGS["theme"]
    C = COLORS[mode]
    
    # 1. Configure Main Root
    root.config(bg=C["bg"])
    
    # 2. Configure Top Bar
    top_bar.config(bg=C["top_bar"])
    
    # 3. Configure recursive widgets
    def recurse_color(widget):
        # CRASH FIX: Do not color inside the Calendar widget
        # The calendar has complex internal parts that break if we force colors on them.
        if isinstance(widget, Calendar) or "Calendar" in str(widget.winfo_class()):
            return

        w_type = widget.winfo_class()
        
        try:
            # Default Backgrounds
            if widget == top_bar:
                pass # Handled above
            elif widget in [settings_btn, list_btn]:
                widget.config(bg=C["top_bar"], fg=C["fg"] if mode == "dark" else "black")
            elif widget == settings_panel:
                widget.config(bg=C["card_bg"])
            elif widget == main_content:
                widget.config(bg=C["bg"])
            elif widget == right_panel:
                widget.config(bg=C["bg"])
            elif isinstance(widget, Entry) or isinstance(widget, Text):
                widget.config(bg=C["input_bg"], fg=C["input_fg"], insertbackground=C["fg"])
            elif isinstance(widget, Listbox):
                widget.config(bg=C["input_bg"], fg=C["input_fg"])
            elif "Frame" in w_type:
                # Check if it's a card
                if getattr(widget, "is_card", False):
                    widget.config(bg=C["card_bg"])
                else:
                    widget.config(bg=C["bg"])
            elif "Label" in w_type:
                # Check for specific labels
                if getattr(widget, "is_card_label", False):
                    widget.config(bg=C["card_bg"], fg=C["fg"])
                elif widget == status_label:
                    widget.config(bg=C["bg"], fg="green")
                elif widget == edit_indicator:
                    widget.config(bg=C["bg"], fg="orange")
                else:
                    widget.config(bg=C["bg"], fg=C["fg"])
            elif "Canvas" in w_type:
                widget.config(bg=C["bg"], highlightthickness=0)
            elif "Button" in w_type:
                 widget.config(bg=C["accent"], fg=C["fg"])
        except TclError:
            # CRASH FIX: If a widget refuses the color (like a Scrollbar or specialized widget), ignore it.
            pass

        # Recurse
        for child in widget.winfo_children():
            recurse_color(child)

    recurse_color(root)
    
    # Update Toggle Button Text
    btn_text = "Switch to Light Mode" if mode == "dark" else "Switch to Dark Mode"
    theme_toggle_btn.config(text=btn_text)

# -------------------------------
# Layout Frames
# -------------------------------
# 1. Top Bar
top_bar = Frame(root, height=50)
top_bar.pack(side=TOP, fill=X)
top_bar.pack_propagate(False) # Force height

# 2. Main Content Area
main_content = Frame(root)
main_content.pack(side=TOP, fill=BOTH, expand=True)

# 3. Panels inside Main Content
# Settings (Left - Hidden)
settings_panel = Frame(main_content, width=200, padx=10, pady=10)
# (We don't pack it yet)

# Central Area (Always visible)
center_panel = Frame(main_content)
center_panel.pack(side=LEFT, fill=BOTH, expand=True, padx=20, pady=20)

# Reminder List (Right - Hidden)
right_panel = Frame(main_content, width=350)
# (We don't pack it yet)

# -------------------------------
# Top Bar Controls
# -------------------------------
def toggle_settings_panel():
    global show_settings
    if show_settings:
        settings_panel.pack_forget()
    else:
        settings_panel.pack(side=LEFT, fill=Y, before=center_panel)
    show_settings = not show_settings

def toggle_list_panel():
    global show_list
    if show_list:
        right_panel.pack_forget()
    else:
        # Pack to the right side
        right_panel.pack(side=RIGHT, fill=Y)
    show_list = not show_list

settings_btn = Button(top_bar, text="⚙ Settings", command=toggle_settings_panel, bd=0, font=("Arial", 10, "bold"))
settings_btn.pack(side=LEFT, padx=10, pady=10)

# Load and place the PNG logo
try:
    logo_img = Image.open(resource_path("icon.png"))
    logo_img = logo_img.resize((30, 30), Image.Resampling.LANCZOS)
    root.top_bar_logo = ImageTk.PhotoImage(logo_img) # Attach to root to prevent garbage collection
    logo_label = Label(top_bar, image=root.top_bar_logo, bg=top_bar["bg"])
    logo_label.is_card_label = False # Keep theme engine from overriding it
    logo_label.pack(side=LEFT, padx=(10, 0))
except Exception:
    pass

app_title = Label(top_bar, text="Qubify-IT's Prodlendar", font=("Segoe UI", 12, "bold"), bg=top_bar["bg"], fg="white")
app_title.pack(side=LEFT, padx=(5, 20)) # Changed left padding to 5 so it sits close to the logo

list_btn = Button(top_bar, text="☰ Reminders", command=toggle_list_panel, bd=0, font=("Arial", 10, "bold"))
list_btn.pack(side=RIGHT, padx=10, pady=10)

# -------------------------------
# Settings Panel Content
# -------------------------------
def toggle_theme_logic():
    SETTINGS["theme"] = "light" if SETTINGS["theme"] == "dark" else "dark"
    with open(SETTINGS_FILE, "w") as f:
        json.dump(SETTINGS, f)
    apply_theme()

theme_toggle_btn = Button(settings_panel, text="Switch Theme", command=toggle_theme_logic)
theme_toggle_btn.pack(pady=20, fill=X)

# -------------------------------
# Center Panel (Input)
# -------------------------------
edit_indicator = Label(center_panel, text="", font=("Segoe UI", 10, "bold"))
edit_indicator.pack(pady=(0, 5))

cal = Calendar(center_panel, selectmode='day', date_pattern="yyyy-mm-dd")
cal.pack(pady=10)

time_frame = Frame(center_panel)
time_frame.pack(pady=5)
Label(time_frame, text="Time (HH:MM): ").pack(side=LEFT)
time_entry = Entry(time_frame, width=10)
time_entry.pack(side=LEFT)

note_entry = Text(center_panel, width=50, height=6)
note_entry.pack(pady=10)

status_label = Label(center_panel, text="", font=("Arial", 10))
status_label.pack(pady=5)

# -------------------------------
# Right Panel (List)
# -------------------------------
# Scrollable canvas for list
canvas = Canvas(right_panel, borderwidth=0, highlightthickness=0)
scrollbar = Scrollbar(right_panel, orient="vertical", command=canvas.yview)
scrollable_frame = Frame(canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

# Controls below list
list_controls = Frame(right_panel)
list_controls.pack(side=BOTTOM, fill=X, pady=10, padx=20) # Controls at bottom

canvas.pack(side=LEFT, fill=BOTH, expand=True, padx=(20, 0)) # Padx 20 from left
scrollbar.pack(side=RIGHT, fill=Y)

# -------------------------------
# Logic: Load, Save, Edit
# -------------------------------
def load_reminders():
    # Clear list
    for w in scrollable_frame.winfo_children():
        w.destroy()
    
    selected_ids.clear()
    update_edit_buttons()

    # Query DB
    reminders = c.execute("SELECT id, datetime, text, status FROM reminders ORDER BY datetime").fetchall()
    
    for rid, dt, txt, st in reminders:
        # Card Frame
        card = Frame(scrollable_frame, bd=1, relief="solid", padx=10, pady=8)
        card.pack(fill=X, pady=5, padx=(5, 5))
        card.is_card = True # Flag for themer

        # Data Labels
        l_dt = Label(card, text=dt, font=("Arial", 8, "bold"))
        l_dt.pack(anchor="w")
        l_dt.is_card_label = True

        l_txt = Label(card, text=txt, wraplength=250, justify=LEFT)
        l_txt.pack(anchor="w")
        l_txt.is_card_label = True
        
        # Click Handler
        def on_click(e, _rid=rid, _card=card):
            # Ctrl check
            if e.state & 0x0004: # Control key held
                if _rid in selected_ids:
                    selected_ids.remove(_rid)
                    _card.config(bd=1, relief="solid") # Deselect style
                else:
                    selected_ids.add(_rid)
                    _card.config(bd=3, relief="raised") # Select style
            else:
                # Single select
                # Clear others visually
                for child in scrollable_frame.winfo_children():
                    child.config(bd=1, relief="solid")
                selected_ids.clear()
                selected_ids.add(_rid)
                _card.config(bd=3, relief="raised")
            
            update_edit_buttons()

        card.bind("<Button-1>", on_click)
        l_dt.bind("<Button-1>", on_click)
        l_txt.bind("<Button-1>", on_click)

    # Re-apply theme to new elements
    apply_theme()

def update_edit_buttons():
    # Enable edit only if exactly 1 item selected
    if len(selected_ids) == 1:
        btn_edit.config(state=NORMAL)
    else:
        btn_edit.config(state=DISABLED)
    
    if len(selected_ids) > 0:
        btn_del.config(state=NORMAL)
    else:
        btn_del.config(state=DISABLED)

def start_edit():
    global EDIT_MODE, editing_id
    if len(selected_ids) != 1:
        return
    
    rid = list(selected_ids)[0]
    editing_id = rid
    row = c.execute("SELECT datetime, text FROM reminders WHERE id=?", (rid,)).fetchone()
    if row:
        dt_str, txt = row
        # Parse "YYYY-MM-DD HH:MM"
        try:
            date_part, time_part = dt_str.split(" ")
            # Set Calendar
            cal.selection_set(date_part)
            # Set Time
            time_entry.delete(0, END)
            time_entry.insert(0, time_part)
            # Set Text
            note_entry.delete("1.0", END)
            note_entry.insert("1.0", txt)
            
            EDIT_MODE = True
            edit_indicator.config(text=f"Editing Reminder ID: {rid}")
        except:
            messagebox.showerror("Error", "Could not parse reminder data.")

def delete_reminders():
    if not selected_ids: return
    for rid in selected_ids:
        c.execute("DELETE FROM reminders WHERE id=?", (rid,))
    conn.commit()
    load_reminders()

def save_reminder():
    global EDIT_MODE, editing_id
    
    date_val = cal.get_date()
    time_val = time_entry.get().strip()
    
    # Validation
    try:
        # Normalize time format
        full_dt_str = f"{date_val} {time_val}"
        valid_dt = datetime.strptime(full_dt_str, "%Y-%m-%d %H:%M")
        final_dt_str = valid_dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        messagebox.showerror("Invalid Date/Time", "Please ensure format is YYYY-MM-DD and HH:MM")
        return

    text_val = note_entry.get("1.0", END).strip()
    if not text_val:
        messagebox.showerror("Missing Text", "Please enter a reminder note.")
        return

    if EDIT_MODE and editing_id is not None:
        rid = list(selected_ids)[0]
        c.execute("UPDATE reminders SET datetime=?, text=?, status='pending' WHERE id=?", (final_dt_str, text_val, editing_id))
        status_label.config(text="Updated!", fg="green")
        EDIT_MODE = False
        editing_id = None
        edit_indicator.config(text="")
        # Clear inputs
        note_entry.delete("1.0", END)
        time_entry.delete(0, END)
    else:
        c.execute("INSERT INTO reminders(datetime, text, status) VALUES(?, ?, 'pending')", (final_dt_str, text_val))
        status_label.config(text="Saved!", fg="green")
        # Clear inputs
        note_entry.delete("1.0", END)

    conn.commit()
    load_reminders()
    root.after(2000, lambda: status_label.config(text=""))

# Buttons
Button(center_panel, text="SAVE REMINDER", command=save_reminder, width=20, height=2).pack(pady=10)

btn_edit = Button(list_controls, text="Edit Selected", command=start_edit, state=DISABLED)
btn_edit.pack(side=LEFT, fill=X, expand=True, padx=2)

btn_del = Button(list_controls, text="Delete Selected", command=delete_reminders, state=DISABLED)
btn_del.pack(side=LEFT, fill=X, expand=True, padx=2)

# ===============================
# Background Services
# ===============================
def checker_thread():
    # MUST OPEN NEW CONNECTION IN THREAD
    t_conn = sqlite3.connect(DB_FILE)
    t_c = t_conn.cursor()
    
    while True:
        now = datetime.now()
        rows = t_c.execute("SELECT id, datetime, text, status FROM reminders WHERE status='pending'").fetchall()
        
        for rid, dt, txt, st in rows:
            try:
                rem_time = datetime.strptime(dt, "%Y-%m-%d %H:%M")
                if rem_time <= now:
                    # Notify
                    if os.name == "nt":
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                        
                        # Clean the text so quotes don't break the PowerShell string
                        safe_txt = txt.replace('"', "'").replace('\n', ' ')
                        
                        # Native Windows Action Center Notification via PowerShell
                        ps_script = f'''
                        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
                        $textNodes = $template.GetElementsByTagName("text")
                        $textNodes.Item(0).AppendChild($template.CreateTextNode("Prodlendar Reminder")) | Out-Null
                        $textNodes.Item(1).AppendChild($template.CreateTextNode("{safe_txt}")) | Out-Null
                        $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
                        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Qubify-IT Prodlendar")
                        $notifier.Show($toast)
                        '''
                        # 0x08000000 ensures the command prompt window stays completely hidden
                        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], creationflags=0x08000000)
                    else:
                        # Fallback for other operating systems
                        notification.notify(title="Prodlendar Reminder", message=txt, timeout=10)
                    t_c.execute("UPDATE reminders SET status='passed' WHERE id=?", (rid,))
                    t_conn.commit()
                    # Refresh UI if list is open (via main thread)
                    root.after(0, load_reminders)
            except ValueError:
                pass # skip invalid dates
        
        time.sleep(5)

# Tray Icon
def tray_setup():
    try:
        image = Image.open(resource_path("icon.ico"))
    except Exception:
        # Fallback if image fails to load
        image = Image.new("RGB", (64, 64), "black")
        d = ImageDraw.Draw(image)
        d.rectangle([16, 16, 48, 48], fill="#2b5278")

    def open_app(icon, item):
        root.after(0, restore_window)

    def exit_app(icon, item):
        icon.stop()
        root.quit()
        sys.exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Open", open_app),
        pystray.MenuItem("Exit", exit_app)
    )

    icon = pystray.Icon("Prodlendar", image, "Prodlendar", menu)
    icon.run()

# Window Management
def restore_window():
    root.deiconify()
    root.lift()
    root.focus_force()

def hide_window():
    root.withdraw()

root.protocol("WM_DELETE_WINDOW", hide_window)

def listen_socket():
    while True:
        try:
            conn_, _ = server.accept()
            data = conn_.recv(1024)
            if data == b"SHOW":
                root.after(0, restore_window)
            conn_.close()
        except:
            pass

# ===============================
# Startup
# ===============================
apply_theme() # Apply initial theme
load_reminders() # Load initial data

# Start Threads
threading.Thread(target=checker_thread, daemon=True).start()
threading.Thread(target=listen_socket, daemon=True).start()
if os.name == "nt":
    threading.Thread(target=tray_setup, daemon=True).start()

root.mainloop()
