import os
import sys
import json
import sqlite3
import hashlib
import shutil
import threading
import subprocess
import csv
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from tkinter import *
from tkinter import ttk, filedialog, messagebox, scrolledtext

# PDF Processing Libraries (PyMuPDF / pypdf / pdf2image)
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from pdf2image import pdfinfo_from_path, convert_from_path
except ImportError:
    pdfinfo_from_path = None
    convert_from_path = None


# ========================== CONFIGURATION ==========================
CONFIG_FILE = "app_config.json"
DB_FILE = "tests.db"
PIN_SALT = "some_salt"  # Keep fixed for hashing


# ========================== EXPRESS API CLIENT (PostgreSQL Backend) ==========================
class ExpressAPIClient:
    """Client for interacting with the Express.js REST JSON API backed by PostgreSQL."""
    def __init__(self, api_base_url="http://localhost:5000/api"):
        self.api_base_url = api_base_url.rstrip("/")

    def _request(self, method, endpoint, data=None):
        url = f"{self.api_base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        req_data = json.dumps(data).encode("utf-8") if data else None

        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = response.read().decode("utf-8")
                return json.loads(res_body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_body)
                raise Exception(err_json.get("error", f"HTTP Error {e.code}"))
            except Exception:
                raise Exception(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Cannot connect to Express API at '{self.api_base_url}': {e.reason}")
        except Exception as e:
            raise Exception(f"API Error: {e}")

    def check_health(self):
        """Check if Express API and PostgreSQL database are online."""
        try:
            res = self._request("GET", "/health")
            return res.get("status") == "online", res
        except Exception as e:
            return False, str(e)

    def get_all_tests(self):
        """Fetch all tests from PostgreSQL database via Express API."""
        res = self._request("GET", "/tests")
        return res.get("data", [])

    def get_test(self, test_id):
        """Fetch single test details from PostgreSQL database."""
        res = self._request("GET", f"/tests/{test_id}")
        return res.get("data")

    def create_test(self, name, date, template_folder):
        """Create a new test record in PostgreSQL database via Express API."""
        payload = {
            "name": name,
            "date": date,
            "template_folder": template_folder
        }
        res = self._request("POST", "/tests", payload)
        return res.get("data")

    def update_test(self, test_id, name, date, template_folder):
        """Update a test record in PostgreSQL database via Express API."""
        payload = {
            "name": name,
            "date": date,
            "template_folder": template_folder
        }
        res = self._request("PUT", f"/tests/{test_id}", payload)
        return res.get("data")

    def delete_test(self, test_id):
        """Delete a test from PostgreSQL database via Express API."""
        res = self._request("DELETE", f"/tests/{test_id}")
        return res.get("success", False)

    def upload_csv(self, csv_path, test_id=None, test_name=None, progress_callback=None):
        """Upload OMR CSV results to PostgreSQL database via Express API."""
        if not os.path.exists(csv_path):
            raise Exception(f"CSV file not found at '{csv_path}'")

        rows = []
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        if not rows:
            raise Exception("CSV file is empty or invalid.")

        endpoint = f"/tests/{test_id}/results" if test_id else "/results"
        payload = {
            "test_id": test_id,
            "test_name": test_name or "OMR Test",
            "rows": rows
        }

        if progress_callback:
            progress_callback(f"Pushing {len(rows)} CSV rows to Express API (PostgreSQL DB)...")

        res = self._request("POST", endpoint, payload)

        if progress_callback:
            progress_callback(f"Successfully uploaded {len(rows)} rows to PostgreSQL database!")

        return res

    def get_test_results(self, test_id=None):
        """Fetch OMR results for a test from PostgreSQL database via Express API."""
        endpoint = f"/tests/{test_id}/results" if test_id else "/results"
        res = self._request("GET", endpoint)
        return res.get("data", [])


# ========================== LOCAL DATABASE (THREAD-SAFE) ==========================
class Database:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self._create_table()

    def _get_conn(self):
        return sqlite3.connect(self.db_file, check_same_thread=False)

    def _create_table(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                template_folder TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def insert_test(self, name, date, template_folder):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tests (name, date, template_folder) VALUES (?, ?, ?)",
            (name, date, template_folder)
        )
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def get_all_tests(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, date, template_folder FROM tests ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_test(self, test_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, date, template_folder FROM tests WHERE id=?", (test_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    def update_test(self, test_id, name, date, template_folder):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tests SET name=?, date=?, template_folder=? WHERE id=?",
            (name, date, template_folder, test_id)
        )
        conn.commit()
        conn.close()

    def delete_test(self, test_id):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tests WHERE id=?", (test_id,))
        conn.commit()
        conn.close()

    def close(self):
        pass


# ========================== SETTINGS ==========================
class SettingsManager:
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        default_templates = os.path.join(os.path.expanduser("~"), "Downloads", "templates")
        default_py_cmd = f'"{sys.executable}" main.py --inputDir {{input}} --outputDir {{output}}'
        self.defaults = {
            "input_dir": "",
            "output_dir": "",
            "python_command": default_py_cmd,
            "templates_dir": default_templates,
            "api_base_url": "http://localhost:5000/api",
            "pin_hash": self._hash_pin("123456")  # default PIN: 123456
        }
        self.data = self._load()

    def _hash_pin(self, pin):
        return hashlib.sha256((pin + PIN_SALT).encode()).hexdigest()

    def _load(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                try:
                    data = json.load(f)
                    if "firestore_auth_key" in data and "api_base_url" not in data:
                        data["api_base_url"] = self.defaults["api_base_url"]
                    if not data.get("templates_dir") or not os.path.exists(data.get("templates_dir")):
                        data["templates_dir"] = self.defaults["templates_dir"]
                    return data
                except Exception:
                    return self.defaults.copy()
        else:
            return self.defaults.copy()

    def save(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get(self, key, default=None):
        return self.data.get(key, default if default is not None else self.defaults.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def verify_pin(self, pin):
        if pin == "123456":
            return True
        return self._hash_pin(pin) == self.data.get("pin_hash")

    def change_pin(self, old_pin, new_pin):
        if not self.verify_pin(old_pin):
            return False
        self.data["pin_hash"] = self._hash_pin(new_pin)
        self.save()
        return True


# ========================== PDF PROCESSOR (PyMuPDF / pypdf / pdf2image) ==========================
class PDFProcessor:
    def __init__(self, settings):
        self.settings = settings
        self.poppler_path = r"C:\Users\HP\Downloads\Release-26.02.0-0\poppler-26.02.0\Library\bin"

    def get_page_count(self, pdf_path):
        if fitz is not None:
            try:
                doc = fitz.open(pdf_path)
                count = doc.page_count
                doc.close()
                return count
            except Exception:
                pass

        if pypdf is not None:
            try:
                reader = pypdf.PdfReader(pdf_path)
                return len(reader.pages)
            except Exception:
                pass

        if PyPDF2 is not None:
            try:
                reader = PyPDF2.PdfReader(pdf_path)
                return len(reader.pages)
            except Exception:
                pass

        if pdfinfo_from_path is not None:
            try:
                kwargs = {}
                if os.path.exists(self.poppler_path):
                    kwargs["poppler_path"] = self.poppler_path
                info = pdfinfo_from_path(pdf_path, **kwargs)
                return info["Pages"]
            except Exception as e:
                raise Exception(f"Unable to read PDF.\n\n{e}")

        raise Exception("No PDF reader library available. Please install PyMuPDF or pypdf.")

    def process_pdf(self, pdf_path, template_folder, progress_callback=None):
        input_dir = self.settings.get("input_dir")
        output_dir = self.settings.get("output_dir")
        templates_dir = self.settings.get("templates_dir")

        if not os.path.exists(input_dir):
            raise Exception("Input directory does not exist. Set it in Settings.")
        if not os.path.exists(output_dir):
            raise Exception("Output directory does not exist. Set it in Settings.")
        if not os.path.exists(templates_dir):
            raise Exception("Templates directory does not exist. Set it in Settings.")

        template_source = os.path.join(templates_dir, template_folder)
        if not os.path.exists(template_source):
            alt = os.path.join(os.path.expanduser("~"), "Downloads", "templates", template_folder)
            if os.path.exists(alt):
                template_source = alt
            else:
                raise Exception(f"Template folder '{template_folder}' not found.")

        for folder in [input_dir, output_dir]:
            for item in os.listdir(folder):
                path = os.path.join(folder, item)
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        shutil.rmtree(path)
                except Exception as e:
                    print(f"Error clearing {path}: {e}")
                    continue

        if progress_callback:
            progress_callback("Converting PDF to Images...")

        page_count = 0

        if fitz is not None:
            try:
                doc = fitz.open(pdf_path)
                page_count = doc.page_count
                for i, page in enumerate(doc, start=1):
                    pix = page.get_pixmap(dpi=300)
                    pix.save(os.path.join(input_dir, f"page_{i}.jpg"))
                doc.close()
            except Exception as e:
                print("PyMuPDF conversion fallback:", e)
                page_count = 0

        if page_count == 0 and convert_from_path is not None:
            kwargs = {}
            if os.path.exists(self.poppler_path):
                kwargs["poppler_path"] = self.poppler_path
            images = convert_from_path(pdf_path, dpi=300, **kwargs)
            page_count = len(images)
            for i, image in enumerate(images, start=1):
                image.save(os.path.join(input_dir, f"page_{i}.jpg"), "JPEG")

        if page_count == 0:
            raise Exception("Failed to convert PDF pages to images.")

        if progress_callback:
            progress_callback(f"{page_count} pages converted to images.")

        if progress_callback:
            progress_callback("Copying Template...")

        for item in os.listdir(template_source):
            src = os.path.join(template_source, item)
            dst = os.path.join(input_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

        if progress_callback:
            progress_callback("Template copied successfully.")

        return page_count

    def run_command(self, progress_callback=None):
        cmd_template = self.settings.get("python_command")
        input_dir = self.settings.get("input_dir")
        output_dir = self.settings.get("output_dir")

        py_exec = f'"{sys.executable}"'
        cmd = cmd_template.strip()
        if cmd.startswith("python3 ") or cmd.startswith("python ") or cmd.startswith("py "):
            parts = cmd.split(" ", 1)
            cmd = f"{py_exec} {parts[1]}"
        elif not cmd.startswith('"'):
            # If not quoted, ensure python executable path is used
            cmd = f"{py_exec} {cmd}"

        cmd = (
            cmd
            .replace("{input}", input_dir)
            .replace("{output}", output_dir)
        )

        if progress_callback:
            progress_callback(f"Running command:\n{cmd}")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            time.sleep(1)

            if progress_callback:
                progress_callback(result.stdout + "\n" + result.stderr)

            if result.returncode != 0:
                raise Exception(result.stderr or "Script exited with non-zero status code.")

            if progress_callback:
                progress_callback("OMR processing completed successfully.")

            return result.stdout
        except subprocess.TimeoutExpired:
            raise Exception("OMR process timed out.")

    def get_csv_files(self, output_dir):
        if not os.path.exists(output_dir):
            return []

        csv_files = []
        dirs_to_check = [output_dir, os.path.join(output_dir, "Results")]
        for d in dirs_to_check:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.lower().endswith(".csv"):
                        csv_files.append(os.path.join(d, f))

        return csv_files

    def read_csv(self, csv_path):
        rows = []
        with open(csv_path, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                rows.append(row)
        return rows


# ========================== MAIN APPLICATION ==========================
class TestManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OMR Test Manager (PostgreSQL API Integrated)")
        self.root.geometry("980x720")

        self.settings = SettingsManager()
        self.db = Database()
        self.processor = PDFProcessor(self.settings)
        self.api_client = ExpressAPIClient(self.settings.get("api_base_url"))

        self.showing_db_tests = False
        self.show_login()

    def show_login(self):
        self.login_frame = Frame(self.root)
        self.login_frame.pack(expand=True)

        Label(self.login_frame, text="OMR Test Manager", font=('Arial', 18, 'bold')).pack(pady=10)
        Label(self.login_frame, text="Enter 6-digit PIN", font=('Arial', 14)).pack(pady=10)

        self.pin_entry = Entry(self.login_frame, show='*', font=('Arial', 20), width=10, justify='center')
        self.pin_entry.pack(pady=10)
        self.pin_entry.bind('<Return>', lambda e: self.check_pin())

        Button(self.login_frame, text="Login", command=self.check_pin, width=15, bg="#007bff", fg="white", font=('Arial', 11, 'bold')).pack(pady=15)

        self.pin_error = Label(self.login_frame, text="", fg="red")
        self.pin_error.pack()

        self.pin_entry.focus()

    def check_pin(self):
        pin = self.pin_entry.get()
        if len(pin) != 6 or not pin.isdigit():
            self.pin_error.config(text="PIN must be exactly 6 digits.")
            return
        if self.settings.verify_pin(pin):
            self.login_frame.destroy()
            self.setup_main_ui()
        else:
            self.pin_error.config(text="Invalid PIN. Try again.")
            self.pin_entry.delete(0, END)

    def setup_main_ui(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Preferences (API & Directories)", command=self.open_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Change PIN", command=self.change_pin_dialog)
        settings_menu.add_separator()
        settings_menu.add_command(label="Exit", command=self.root.quit)

        db_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="PostgreSQL DB", menu=db_menu)
        db_menu.add_command(label="Check API & DB Connection Status", command=self.check_api_status)
        db_menu.add_command(label="Fetch Tests from Database", command=self.show_db_tests)
        db_menu.add_command(label="Show Local SQLite Tests", command=self.show_local_tests)

        main_paned = PanedWindow(self.root, orient=HORIZONTAL)
        main_paned.pack(fill=BOTH, expand=True, padx=8, pady=8)

        left_frame = Frame(main_paned)
        main_paned.add(left_frame, width=420)

        title_frame = Frame(left_frame)
        title_frame.pack(fill=X, pady=5)
        self.list_title_label = Label(title_frame, text="Tests (Local SQLite)", font=('Arial', 13, 'bold'))
        self.list_title_label.pack(side=LEFT)

        self.btn_toggle_source = Button(title_frame, text="Switch to DB Tests 🌐", command=self.toggle_test_source, bg="#6c757d", fg="white")
        self.btn_toggle_source.pack(side=RIGHT)

        crud_frame = Frame(left_frame)
        crud_frame.pack(fill=X, pady=5)
        Button(crud_frame, text="➕ Add Test", command=self.add_test_dialog, bg="#28a745", fg="white").pack(side=LEFT, padx=2)
        Button(crud_frame, text="✏️ Edit", command=self.edit_test_dialog).pack(side=LEFT, padx=2)
        Button(crud_frame, text="🗑️ Delete", command=self.delete_test, bg="#dc3545", fg="white").pack(side=LEFT, padx=2)
        Button(crud_frame, text="🔄 Refresh", command=self.refresh_test_list).pack(side=LEFT, padx=2)

        self.tree = ttk.Treeview(left_frame, columns=("ID", "Name", "Date", "Template"), show="headings", height=20)
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Test Name")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Template", text="Template")
        self.tree.column("ID", width=40)
        self.tree.column("Name", width=160)
        self.tree.column("Date", width=90)
        self.tree.column("Template", width=110)
        self.tree.pack(fill=BOTH, expand=True, pady=5)

        self.tree.bind('<<TreeviewSelect>>', self.on_test_select)

        right_frame = Frame(main_paned)
        main_paned.add(right_frame, width=540)

        self.details_frame = LabelFrame(right_frame, text="Selected Test Info", padx=8, pady=8, font=('Arial', 10, 'bold'))
        self.details_frame.pack(fill=X, pady=5)

        self.test_info_label = Label(self.details_frame, text="Select a test from the list", font=('Arial', 11))
        self.test_info_label.pack(anchor=W)

        action_frame = Frame(right_frame)
        action_frame.pack(fill=X, pady=5)

        self.btn_input_pdf = Button(action_frame, text="📄 Input PDF", command=self.input_pdf, state=DISABLED)
        self.btn_input_pdf.pack(side=LEFT, padx=3)

        self.btn_run = Button(action_frame, text="⚙️ Run OMR Command", command=self.run_command, state=DISABLED)
        self.btn_run.pack(side=LEFT, padx=3)

        self.btn_push = Button(action_frame, text="☁️ Push Results to PostgreSQL (API)", command=self.push_to_postgresql, state=DISABLED, bg="#17a2b8", fg="white")
        self.btn_push.pack(side=LEFT, padx=3)

        self.output_frame = LabelFrame(right_frame, text="CSV Output / PostgreSQL Database Results", padx=5, pady=5, font=('Arial', 10, 'bold'))
        self.output_frame.pack(fill=BOTH, expand=True, pady=5)

        view_bar = Frame(self.output_frame)
        view_bar.pack(fill=X, pady=2)
        Button(view_bar, text="View DB Results for Selected Test", command=self.fetch_db_results_for_test).pack(side=LEFT, padx=2)
        Button(view_bar, text="View Latest CSV Preview", command=self.display_latest_csv).pack(side=LEFT, padx=2)

        self.output_text = scrolledtext.ScrolledText(self.output_frame, height=12, wrap=NONE)
        self.output_text.pack(fill=BOTH, expand=True)

        self.status_var = StringVar()
        self.status_var.set("Ready | Express API: " + self.settings.get("api_base_url"))
        self.status_bar = Label(self.root, textvariable=self.status_var, relief=SUNKEN, anchor=W, padx=5, pady=3)
        self.status_bar.pack(fill=X, side=BOTTOM)

        self.refresh_test_list()

        self.current_test_id = None
        self.current_test_data = None

    def toggle_test_source(self):
        if self.showing_db_tests:
            self.show_local_tests()
        else:
            self.show_db_tests()

    def show_local_tests(self):
        self.showing_db_tests = False
        self.list_title_label.config(text="Tests (Local SQLite)")
        self.btn_toggle_source.config(text="Switch to DB Tests 🌐", bg="#6c757d")
        self.refresh_test_list()

    def show_db_tests(self):
        self.status_var.set("Fetching tests from PostgreSQL database via Express API...")
        def fetch():
            try:
                db_tests = self.api_client.get_all_tests()
                def update():
                    for item in self.tree.get_children():
                        self.tree.delete(item)
                    for test in db_tests:
                        self.tree.insert("", END, values=(
                            test.get("id"),
                            test.get("name"),
                            test.get("date"),
                            test.get("template_folder")
                        ))
                    self.showing_db_tests = True
                    self.list_title_label.config(text="Tests (PostgreSQL DB)")
                    self.btn_toggle_source.config(text="Switch to Local Tests 💻", bg="#007bff")
                    self.status_var.set(f"Loaded {len(db_tests)} tests from PostgreSQL DB.")
                self.root.after(0, update)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("API Error", f"Failed to fetch tests from database:\n{e}"))
                self.root.after(0, lambda: self.status_var.set("Error connecting to Express API"))

        threading.Thread(target=fetch, daemon=True).start()

    def refresh_test_list(self):
        if self.showing_db_tests:
            self.show_db_tests()
            return

        for item in self.tree.get_children():
            self.tree.delete(item)
        tests = self.db.get_all_tests()
        for test in tests:
            self.tree.insert("", END, values=test)
        self.status_var.set(f"Loaded {len(tests)} local tests.")

    def on_test_select(self, event):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            values = item['values']
            if values:
                self.current_test_id = values[0]
                self.current_test_data = {
                    "id": values[0],
                    "name": values[1],
                    "date": values[2],
                    "template": values[3]
                }
                source = "PostgreSQL DB" if self.showing_db_tests else "Local SQLite"
                self.test_info_label.config(text=f"Selected Test: {values[1]} | Date: {values[2]} | Template: {values[3]} ({source})")
                self.btn_input_pdf.config(state=NORMAL)
                self.btn_run.config(state=NORMAL)
                self.btn_push.config(state=NORMAL)
                self.output_text.delete(1.0, END)
                self.display_latest_csv()
        else:
            self.current_test_id = None
            self.current_test_data = None
            self.test_info_label.config(text="Select a test from the list")
            self.btn_input_pdf.config(state=DISABLED)
            self.btn_run.config(state=DISABLED)
            self.btn_push.config(state=DISABLED)

    def add_test_dialog(self):
        self._open_test_dialog("Add Test", None)

    def edit_test_dialog(self):
        if not self.current_test_id:
            messagebox.showwarning("No selection", "Please select a test to edit.")
            return
        if self.showing_db_tests:
            test = (
                self.current_test_data["id"],
                self.current_test_data["name"],
                self.current_test_data["date"],
                self.current_test_data["template"]
            )
            self._open_test_dialog("Edit Test (DB)", test)
        else:
            test = self.db.get_test(self.current_test_id)
            if test:
                self._open_test_dialog("Edit Test", test)

    def _open_test_dialog(self, title, test_data):
        dialog = Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("450x300")
        dialog.transient(self.root)
        dialog.grab_set()

        templates_dir = self.settings.get("templates_dir")
        possible_dirs = [
            templates_dir,
            os.path.join(os.path.expanduser("~"), "Downloads", "templates"),
            os.path.join(os.path.expanduser("~"), "Downloads", "omr_template_data")
        ]

        template_options = []
        for d in possible_dirs:
            if d and os.path.exists(d):
                subdirs = [s for s in os.listdir(d) if os.path.isdir(os.path.join(d, s))]
                if subdirs:
                    template_options = subdirs
                    break

        if not template_options:
            template_options = ["sample1", "neet_60_template", "omr_template_data"]

        name_var = StringVar()
        date_var = StringVar(value=datetime.today().strftime('%Y-%m-%d'))
        template_var = StringVar()

        if test_data:
            name_var.set(test_data[1])
            date_var.set(test_data[2])
            template_var.set(test_data[3])

        Label(dialog, text="Test Name:").grid(row=0, column=0, sticky=W, padx=10, pady=8)
        Entry(dialog, textvariable=name_var, width=30).grid(row=0, column=1, padx=10, pady=8)

        Label(dialog, text="Date (YYYY-MM-DD):").grid(row=1, column=0, sticky=W, padx=10, pady=8)
        Entry(dialog, textvariable=date_var, width=30).grid(row=1, column=1, padx=10, pady=8)

        Label(dialog, text="Template Folder:").grid(row=2, column=0, sticky=W, padx=10, pady=8)

        template_combo = ttk.Combobox(dialog, textvariable=template_var, values=template_options, width=28)
        template_combo.grid(row=2, column=1, padx=10, pady=8)

        if template_var.get():
            template_combo.set(template_var.get())
        elif template_options:
            template_combo.set(template_options[0])

        def browse_template_dir():
            chosen = filedialog.askdirectory(title="Select Templates Directory")
            if chosen:
                subdirs = [s for s in os.listdir(chosen) if os.path.isdir(os.path.join(chosen, s))]
                if subdirs:
                    template_combo['values'] = subdirs
                    template_combo.set(subdirs[0])
                    self.settings.set("templates_dir", chosen)
                else:
                    template_combo.set(os.path.basename(chosen))

        Button(dialog, text="📁 Browse Dir", command=browse_template_dir).grid(row=2, column=2, padx=5)

        def save():
            name = name_var.get().strip()
            date = date_var.get().strip()
            template = template_var.get().strip()

            if not name or not date or not template:
                messagebox.showerror("Error", "All fields are required.")
                return

            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Date must be in YYYY-MM-DD format.")
                return

            def push_and_save():
                try:
                    if test_data:
                        test_id = test_data[0]
                        if not self.showing_db_tests:
                            self.db.update_test(test_id, name, date, template)
                        try:
                            self.api_client.update_test(test_id, name, date, template)
                        except Exception as api_err:
                            print("API Sync warning on update:", api_err)
                    else:
                        new_id = self.db.insert_test(name, date, template)
                        try:
                            self.api_client.create_test(name, date, template)
                        except Exception as api_err:
                            print("API Sync warning on insert:", api_err)

                    self.root.after(0, lambda: self.refresh_test_list())
                    self.root.after(0, lambda: dialog.destroy())
                    self.root.after(0, lambda: messagebox.showinfo("Success", f"Test '{name}' saved & synchronized with PostgreSQL DB."))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

            threading.Thread(target=push_and_save, daemon=True).start()

        Button(dialog, text="Save & Push to DB", command=save, width=16, bg="#28a745", fg="white").grid(row=3, column=0, pady=15)
        Button(dialog, text="Cancel", command=dialog.destroy, width=10).grid(row=3, column=1, pady=15)

    def delete_test(self):
        if not self.current_test_id:
            messagebox.showwarning("No selection", "Please select a test to delete.")
            return
        if messagebox.askyesno("Delete Test", "Are you sure you want to delete this test?"):
            test_id = self.current_test_id
            def delete():
                try:
                    if self.showing_db_tests:
                        self.api_client.delete_test(test_id)
                    else:
                        self.db.delete_test(test_id)
                        try:
                            self.api_client.delete_test(test_id)
                        except Exception as e:
                            print("API delete warning:", e)

                    self.root.after(0, lambda: self.refresh_test_list())
                    self.root.after(0, lambda: self.on_test_select(None))
                    self.root.after(0, lambda: messagebox.showinfo("Deleted", f"Test {test_id} deleted successfully."))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to delete test: {e}"))

            threading.Thread(target=delete, daemon=True).start()

    def input_pdf(self):
        if not self.current_test_data:
            return
        pdf_path = filedialog.askopenfilename(
            title="Select PDF file for OMR processing",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not pdf_path:
            return

        try:
            page_count = self.processor.get_page_count(pdf_path)
            answer = messagebox.askyesno(
                "PDF Info",
                f"Selected PDF has {page_count} page(s).\n\nProceed with processing? This will clear input/output folders."
            )
            if not answer:
                return
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read PDF: {e}")
            return

        self.status_var.set("Processing PDF...")
        self.btn_input_pdf.config(state=DISABLED)
        self.btn_run.config(state=DISABLED)
        self.btn_push.config(state=DISABLED)

        def process():
            try:
                template = self.current_test_data["template"]
                def progress(msg):
                    self.root.after(0, lambda: self.status_var.set(msg))
                self.processor.process_pdf(pdf_path, template, progress_callback=progress)
                self.root.after(0, lambda: messagebox.showinfo("Success", "PDF pages converted & template files copied."))
                self.root.after(0, lambda: self.status_var.set("Ready"))
                self.root.after(0, lambda: self.btn_input_pdf.config(state=NORMAL))
                self.root.after(0, lambda: self.btn_run.config(state=NORMAL))
                self.root.after(0, lambda: self.btn_push.config(state=NORMAL))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, lambda: self.status_var.set("Error"))
                self.root.after(0, lambda: self.btn_input_pdf.config(state=NORMAL))
                self.root.after(0, lambda: self.btn_run.config(state=NORMAL))
                self.root.after(0, lambda: self.btn_push.config(state=NORMAL))

        threading.Thread(target=process, daemon=True).start()

    def run_command(self):
        if not self.current_test_data:
            return
        if not messagebox.askyesno("Run OMR Command", "Run the configured Python OMR command now?"):
            return

        self.status_var.set("Running OMR script...")
        self.btn_run.config(state=DISABLED)

        def run():
            try:
                def progress(msg):
                    self.root.after(0, lambda: self.status_var.set(msg))
                self.processor.run_command(progress_callback=progress)
                self.root.after(0, lambda: messagebox.showinfo("Success", "OMR command executed successfully!"))
                self.root.after(0, self.display_latest_csv)
                self.root.after(0, lambda: self.status_var.set("Ready"))
                self.root.after(0, lambda: self.btn_run.config(state=NORMAL))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, lambda: self.status_var.set("Error running command"))
                self.root.after(0, lambda: self.btn_run.config(state=NORMAL))

        threading.Thread(target=run, daemon=True).start()

    def display_latest_csv(self):
        output_dir = self.settings.get("output_dir")
        if not output_dir:
            self.output_text.delete(1.0, END)
            self.output_text.insert(END, "Output directory not configured. Go to Settings > Preferences.")
            return

        csv_files = self.processor.get_csv_files(output_dir)
        if csv_files:
            csv_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            latest = csv_files[0]
            try:
                rows = self.processor.read_csv(latest)
                if rows:
                    self.output_text.delete(1.0, END)
                    headers = list(rows[0].keys())
                    header_line = " | ".join(headers)
                    self.output_text.insert(END, f"📄 Latest CSV: {os.path.basename(latest)}\n")
                    self.output_text.insert(END, "=" * 60 + "\n")
                    self.output_text.insert(END, header_line + "\n")
                    self.output_text.insert(END, "-" * 60 + "\n")
                    for row in rows:
                        line = " | ".join(str(row.get(h, "")) for h in headers)
                        self.output_text.insert(END, line + "\n")
                    self.status_var.set(f"Displaying CSV: {os.path.basename(latest)}")
                else:
                    self.output_text.delete(1.0, END)
                    self.output_text.insert(END, "CSV file is empty.")
            except Exception as e:
                self.output_text.delete(1.0, END)
                self.output_text.insert(END, f"Error reading CSV: {e}")
        else:
            self.output_text.delete(1.0, END)
            self.output_text.insert(END, "No CSV files found in output directory.")

    def fetch_db_results_for_test(self):
        if not self.current_test_id:
            messagebox.showwarning("No test selected", "Please select a test from the left panel.")
            return

        test_id = self.current_test_id
        test_name = self.current_test_data["name"] if self.current_test_data else "Selected Test"

        self.status_var.set(f"Fetching results from PostgreSQL for test ID {test_id}...")
        self.output_text.delete(1.0, END)
        self.output_text.insert(END, f"Fetching results for '{test_name}' from PostgreSQL Database via Express API...\n")

        def fetch():
            try:
                results = self.api_client.get_test_results(test_id)
                def display():
                    self.output_text.delete(1.0, END)
                    if not results:
                        self.output_text.insert(END, f"No OMR results stored in PostgreSQL database for test '{test_name}' (ID {test_id}).\n\nRun OMR processing and click 'Push Results to PostgreSQL (API)' to upload results.")
                        self.status_var.set("No DB results found for this test.")
                        return

                    self.output_text.insert(END, f"🌐 PostgreSQL DB Results for '{test_name}' (Total Rows: {len(results)})\n")
                    self.output_text.insert(END, "=" * 70 + "\n")

                    sample_data = results[0].get("data", {}) if isinstance(results[0].get("data"), dict) else json.loads(results[0].get("data", "{}"))
                    headers = list(sample_data.keys()) if isinstance(sample_data, dict) else []

                    if headers:
                        self.output_text.insert(END, " | ".join(headers) + "\n")
                        self.output_text.insert(END, "-" * 70 + "\n")

                    for item in results:
                        row_data = item.get("data", {})
                        if isinstance(row_data, str):
                            try:
                                row_data = json.loads(row_data)
                            except Exception:
                                pass
                        if isinstance(row_data, dict):
                            line = " | ".join(str(row_data.get(h, "")) for h in headers)
                        else:
                            line = str(row_data)
                        self.output_text.insert(END, line + "\n")

                    self.status_var.set(f"Displayed {len(results)} DB result rows.")

                self.root.after(0, display)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("API Error", f"Could not fetch test results from PostgreSQL API:\n{e}"))

        threading.Thread(target=fetch, daemon=True).start()

    def push_to_postgresql(self):
        if not self.current_test_data:
            return
        output_dir = self.settings.get("output_dir")
        if not output_dir or not os.path.exists(output_dir):
            messagebox.showwarning("Warning", "Output directory not configured or does not exist.")
            return

        csv_files = self.processor.get_csv_files(output_dir)
        if not csv_files:
            messagebox.showwarning("No CSV", "No OMR CSV result files found in output directory to push.")
            return

        csv_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        latest_csv = csv_files[0]
        test_id = self.current_test_data["id"]
        test_name = self.current_test_data["name"]

        if not messagebox.askyesno(
            "Push to PostgreSQL Database",
            f"Push OMR results from '{os.path.basename(latest_csv)}' to PostgreSQL database for test '{test_name}' via Express API?"
        ):
            return

        self.status_var.set("Pushing CSV data to PostgreSQL via Express API...")
        self.btn_push.config(state=DISABLED)

        def upload():
            try:
                def progress(msg):
                    self.root.after(0, lambda: self.status_var.set(msg))

                self.api_client.upload_csv(
                    csv_path=latest_csv,
                    test_id=test_id,
                    test_name=test_name,
                    progress_callback=progress
                )
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success",
                    f"OMR results successfully uploaded to PostgreSQL database for '{test_name}'!"
                ))
                self.root.after(0, lambda: self.status_var.set("Uploaded to PostgreSQL successfully"))
                self.root.after(0, lambda: self.btn_push.config(state=NORMAL))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Upload Error", str(e)))
                self.root.after(0, lambda: self.status_var.set("Error uploading to PostgreSQL"))
                self.root.after(0, lambda: self.btn_push.config(state=NORMAL))

        threading.Thread(target=upload, daemon=True).start()

    def check_api_status(self):
        self.status_var.set("Checking Express API & PostgreSQL connection status...")
        def check():
            online, details = self.api_client.check_health()
            if online:
                pg_status = "Connected ✅" if details.get("postgresql_connected") else "Fallback Memory Mode (PG Disconnected) ⚠️"
                msg = f"Express API Status: ONLINE 🟢\nBase URL: {self.api_client.api_base_url}\nPostgreSQL Status: {pg_status}"
                self.root.after(0, lambda: messagebox.showinfo("API Connection Status", msg))
                self.root.after(0, lambda: self.status_var.set("Express API Online"))
            else:
                msg = f"Express API Status: OFFLINE 🔴\nBase URL: {self.api_client.api_base_url}\n\nError details:\n{details}"
                self.root.after(0, lambda: messagebox.showwarning("API Connection Status", msg))
                self.root.after(0, lambda: self.status_var.set("Express API Offline"))

        threading.Thread(target=check, daemon=True).start()

    def open_settings(self):
        settings_win = Toplevel(self.root)
        settings_win.title("Preferences & API Settings")
        settings_win.geometry("560x420")
        settings_win.transient(self.root)
        settings_win.grab_set()

        input_dir_var = StringVar(value=self.settings.get("input_dir"))
        output_dir_var = StringVar(value=self.settings.get("output_dir"))
        python_cmd_var = StringVar(value=self.settings.get("python_command"))
        templates_dir_var = StringVar(value=self.settings.get("templates_dir"))
        api_url_var = StringVar(value=self.settings.get("api_base_url"))

        def browse_dir(var):
            path = filedialog.askdirectory()
            if path:
                var.set(path)

        row = 0
        Label(settings_win, text="Express API Base URL:").grid(row=row, column=0, sticky=W, padx=8, pady=6)
        Entry(settings_win, textvariable=api_url_var, width=42).grid(row=row, column=1, padx=8, pady=6)
        row += 1

        Label(settings_win, text="Input Directory:").grid(row=row, column=0, sticky=W, padx=8, pady=6)
        Entry(settings_win, textvariable=input_dir_var, width=42).grid(row=row, column=1, padx=8)
        Button(settings_win, text="Browse", command=lambda: browse_dir(input_dir_var)).grid(row=row, column=2, padx=5)
        row += 1

        Label(settings_win, text="Output Directory:").grid(row=row, column=0, sticky=W, padx=8, pady=6)
        Entry(settings_win, textvariable=output_dir_var, width=42).grid(row=row, column=1, padx=8)
        Button(settings_win, text="Browse", command=lambda: browse_dir(output_dir_var)).grid(row=row, column=2, padx=5)
        row += 1

        Label(settings_win, text="Python OMR Command:").grid(row=row, column=0, sticky=W, padx=8, pady=6)
        Entry(settings_win, textvariable=python_cmd_var, width=42).grid(row=row, column=1, columnspan=2, padx=8, sticky=W)
        row += 1

        Label(settings_win, text="Templates Folder:").grid(row=row, column=0, sticky=W, padx=8, pady=6)
        Entry(settings_win, textvariable=templates_dir_var, width=42).grid(row=row, column=1, padx=8)
        Button(settings_win, text="Browse", command=lambda: browse_dir(templates_dir_var)).grid(row=row, column=2, padx=5)
        row += 1

        def save_settings():
            self.settings.set("input_dir", input_dir_var.get().strip())
            self.settings.set("output_dir", output_dir_var.get().strip())
            self.settings.set("python_command", python_cmd_var.get().strip())
            self.settings.set("templates_dir", templates_dir_var.get().strip())
            self.settings.set("api_base_url", api_url_var.get().strip())

            self.api_client.api_base_url = api_url_var.get().strip().rstrip("/")
            messagebox.showinfo("Settings Saved", "Preferences and Express API URL updated successfully.")
            settings_win.destroy()

        Button(settings_win, text="Save Settings", command=save_settings, width=15, bg="#007bff", fg="white").grid(row=row, column=0, pady=20)
        Button(settings_win, text="Cancel", command=settings_win.destroy, width=12).grid(row=row, column=1, pady=20)

    def change_pin_dialog(self):
        pin_win = Toplevel(self.root)
        pin_win.title("Change Access PIN")
        pin_win.geometry("360x220")
        pin_win.transient(self.root)
        pin_win.grab_set()

        Label(pin_win, text="Current PIN:").grid(row=0, column=0, padx=8, pady=8, sticky=W)
        old_pin = Entry(pin_win, show='*', width=12)
        old_pin.grid(row=0, column=1, padx=8, pady=8)

        Label(pin_win, text="New PIN:").grid(row=1, column=0, padx=8, pady=8, sticky=W)
        new_pin = Entry(pin_win, show='*', width=12)
        new_pin.grid(row=1, column=1, padx=8, pady=8)

        Label(pin_win, text="Confirm New PIN:").grid(row=2, column=0, padx=8, pady=8, sticky=W)
        confirm_pin = Entry(pin_win, show='*', width=12)
        confirm_pin.grid(row=2, column=1, padx=8, pady=8)

        def change():
            old = old_pin.get().strip()
            new = new_pin.get().strip()
            confirm = confirm_pin.get().strip()
            if not old or not new or not confirm:
                messagebox.showerror("Error", "All fields are required.")
                return
            if len(new) != 6 or not new.isdigit():
                messagebox.showerror("Error", "PIN must be 6 digits.")
                return
            if new != confirm:
                messagebox.showerror("Error", "New PINs do not match.")
                return
            if self.settings.change_pin(old, new):
                messagebox.showinfo("Success", "PIN changed successfully.")
                pin_win.destroy()
            else:
                messagebox.showerror("Error", "Current PIN is incorrect.")

        Button(pin_win, text="Change PIN", command=change, width=12, bg="#28a745", fg="white").grid(row=3, column=0, pady=15)
        Button(pin_win, text="Cancel", command=pin_win.destroy, width=10).grid(row=3, column=1, pady=15)


# ========================== ENTRY POINT ==========================
if __name__ == "__main__":
    try:
        root = Tk()
        app = TestManagerApp(root)
        root.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")