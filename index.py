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


# ========================== EXPRESS / STRAPI API CLIENT ==========================
class ExpressAPIClient:
    """Client for interacting with the Express.js / Strapi Users-Permissions REST JSON API."""
    def __init__(self, api_base_url="http://localhost:5000/api"):
        self.api_base_url = api_base_url.rstrip("/")
        self.auth_token = None
        self.current_user = None
        self.user_schools = []
        self.selected_school = None

    def _request(self, method, endpoint, data=None):
        url = f"{self.api_base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

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
                if "error" in err_json:
                    err_detail = err_json["error"].get("message") if isinstance(err_json["error"], dict) else err_json["error"]
                    raise Exception(err_detail)
                raise Exception(f"HTTP Error {e.code}")
            except Exception as parse_err:
                if str(parse_err) != f"HTTP Error {e.code}":
                    raise parse_err
                raise Exception(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Cannot connect to API at '{self.api_base_url}': {e.reason}")
        except Exception as e:
            raise Exception(f"API Error: {e}")

    def authenticate_google_email(self, email, name="Google User"):
        """Authenticate user with Google email via Strapi Users & Permissions Google Provider API."""
        clean_email = email.strip().lower()
        if not clean_email.endswith("@gmail.com") or len(clean_email) < 11:
            raise Exception("Access denied. Only valid @gmail.com accounts are permitted for Google Login.")

        payload = {
            "email": clean_email,
            "username": clean_email.split('@')[0],
            "provider": "google"
        }
        res = self._request("POST", "/auth/google", payload)
        if "jwt" in res and "user" in res:
            self.auth_token = res.get("jwt")
            self.current_user = res.get("user")
            self.user_schools = self.current_user.get("schools", [])
            if self.user_schools:
                self.selected_school = self.user_schools[0]
            return True, res
        elif res.get("success"):
            self.auth_token = res.get("token")
            self.current_user = res.get("user")
            self.user_schools = res.get("schools", [])
            if self.user_schools:
                self.selected_school = self.user_schools[0]
            return True, res
        error_msg = res.get("error", {}).get("message") if isinstance(res.get("error"), dict) else res.get("error", "Authentication failed.")
        return False, error_msg

    def check_health(self):
        """Check API & Database status."""
        try:
            res = self._request("GET", "/health")
            return res.get("status") == "online", res
        except Exception as e:
            return False, str(e)

    def get_tests_for_school(self, school_id=None):
        """Fetch tests scoped by selected school ID."""
        s_id = school_id or (self.selected_school["id"] if self.selected_school else 1)
        res = self._request("GET", f"/schools/{s_id}/tests")
        return res.get("data", [])

    def create_test_for_school(self, name, date, template_folder, school_id=None):
        """Create test scoped to selected school."""
        s_id = school_id or (self.selected_school["id"] if self.selected_school else 1)
        payload = {
            "name": name,
            "date": date,
            "template_folder": template_folder
        }
        res = self._request("POST", f"/schools/{s_id}/tests", payload)
        return res.get("data")

    def update_test(self, test_id, name, date, template_folder):
        """Update test record."""
        payload = {
            "name": name,
            "date": date,
            "template_folder": template_folder
        }
        res = self._request("PUT", f"/tests/{test_id}", payload)
        return res.get("data")

    def delete_test(self, test_id):
        """Delete test record."""
        res = self._request("DELETE", f"/tests/{test_id}")
        return res.get("success", False)

    def upload_csv_for_school(self, csv_path, test_id=None, test_name=None, school_id=None, progress_callback=None):
        """Upload OMR CSV score rows scoped to selected school."""
        if not os.path.exists(csv_path):
            raise Exception(f"CSV file not found at '{csv_path}'")

        rows = []
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        if not rows:
            raise Exception("CSV file is empty or invalid.")

        s_id = school_id or (self.selected_school["id"] if self.selected_school else 1)
        endpoint = f"/schools/{s_id}/tests/{test_id}/results" if test_id else f"/schools/{s_id}/results"
        payload = {
            "test_id": test_id,
            "test_name": test_name or "OMR Test",
            "rows": rows
        }

        if progress_callback:
            progress_callback(f"Pushing {len(rows)} CSV rows to database for School ID {s_id}...")

        res = self._request("POST", endpoint, payload)

        if progress_callback:
            progress_callback(f"Successfully uploaded {len(rows)} rows to database for School ID {s_id}!")

        return res

    def get_test_results_for_school(self, test_id=None, school_id=None):
        """Fetch OMR student score rows for selected school & test."""
        s_id = school_id or (self.selected_school["id"] if self.selected_school else 1)
        endpoint = f"/schools/{s_id}/tests/{test_id}/results" if test_id else f"/schools/{s_id}/results"
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
            "last_google_email": "sreehasathota@gmail.com"
        }
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                try:
                    data = json.load(f)
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


# ========================== PDF PROCESSOR ==========================
class PDFProcessor:
    def __init__(self, settings):
        self.settings = settings

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

        raise Exception("No PDF reader library available.")

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
                print("PyMuPDF fallback:", e)

        if page_count == 0:
            raise Exception("Failed to convert PDF pages to images.")

        if progress_callback:
            progress_callback(f"{page_count} pages converted to images. Copying Template...")

        for item in os.listdir(template_source):
            src = os.path.join(template_source, item)
            dst = os.path.join(input_dir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

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
            cmd = f"{py_exec} {cmd}"

        cmd = (
            cmd
            .replace("{input}", input_dir)
            .replace("{output}", output_dir)
        )

        if progress_callback:
            progress_callback(f"Running command:\n{cmd}")

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        time.sleep(1)

        if result.returncode != 0:
            raise Exception(result.stderr or "Script exited with non-zero status code.")

        return result.stdout

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
        self.root.title("OMR Test Manager")
        self.root.geometry("1020x750")

        self.settings = SettingsManager()
        self.db = Database()
        self.processor = PDFProcessor(self.settings)
        self.api_client = ExpressAPIClient(self.settings.get("api_base_url"))

        self.showing_db_tests = True
        self.show_google_login()

    def show_google_login(self):
        self.login_frame = Frame(self.root)
        self.login_frame.pack(expand=True)

        Label(self.login_frame, text="OMR Test Manager", font=('Arial', 22, 'bold')).pack(pady=15)

        Label(self.login_frame, text="ENTER YOUR GMAIL (@gmail.com):", font=('Arial', 12, 'bold')).pack(pady=12)

        last_email = self.settings.get("last_google_email", "sreehasathota@gmail.com")
        self.email_entry = Entry(self.login_frame, font=('Arial', 14), width=32, justify='center')
        self.email_entry.insert(0, last_email)
        self.email_entry.pack(pady=5)
        self.email_entry.bind('<Return>', lambda e: self.perform_google_login())

        Button(
            self.login_frame,
            text="🌐 Sign In with Google Email",
            command=self.perform_google_login,
            width=28,
            bg="#4285F4",
            fg="white",
            font=('Arial', 11, 'bold')
        ).pack(pady=15)

        self.login_status = Label(self.login_frame, text="", fg="red", font=('Arial', 10), wraplength=400)
        self.login_status.pack(pady=5)

        self.email_entry.focus()

    def perform_google_login(self):
        email = self.email_entry.get().strip().lower()
        if not email or not email.endswith("@gmail.com") or len(email) < 11:
            self.login_status.config(
                text="Access denied. Only valid @gmail.com email addresses are permitted for Google Login.",
                fg="red"
            )
            return

        self.login_status.config(text="Authenticating...", fg="blue")

        def login_thread():
            try:
                success, res = self.api_client.authenticate_google_email(email)
                if success:
                    self.settings.set("last_google_email", email)
                    def proceed():
                        self.login_frame.destroy()
                        self.setup_main_ui()
                    self.root.after(0, proceed)
                else:
                    self.root.after(0, lambda: self.login_status.config(text=res.get("error", "Login failed"), fg="red"))
            except Exception as e:
                self.root.after(0, lambda: self.login_status.config(text=f"{e}", fg="red"))

        threading.Thread(target=login_thread, daemon=True).start()

    def setup_main_ui(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        settings_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Preferences & API URL", command=self.open_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Switch Google User / Logout", command=self.logout)
        settings_menu.add_separator()
        settings_menu.add_command(label="Exit", command=self.root.quit)

        db_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Database & Schools", menu=db_menu)
        db_menu.add_command(label="Check API & Database Health", command=self.check_api_status)
        db_menu.add_command(label="Refresh Assigned Schools", command=self.refresh_assigned_schools)

        # Top Bar for Multi-School Selection Dropdown & Logged-in User Profile
        top_bar = Frame(self.root, bg="#e9ecef", padx=10, pady=8)
        top_bar.pack(fill=X)

        role_info = self.api_client.current_user.get("role", {})
        role_name = role_info.get("name", "test_editor") if isinstance(role_info, dict) else str(role_info)
        user_name = self.api_client.current_user.get("username", self.api_client.current_user.get("email", "User")) if self.api_client.current_user else "User"
        user_email = self.api_client.current_user.get("email", "") if self.api_client.current_user else ""
        Label(top_bar, text=f"👤 Logged in: {user_name} ({user_email}) | Role: {role_name}", font=('Arial', 10, 'bold'), bg="#e9ecef").pack(side=LEFT)

        school_frame = Frame(top_bar, bg="#e9ecef")
        school_frame.pack(side=RIGHT)

        Label(school_frame, text="🏫 Select School:", font=('Arial', 10, 'bold'), bg="#e9ecef").pack(side=LEFT, padx=5)

        school_names = [f"{s['name']} ({s['code']})" for s in self.api_client.user_schools]
        self.school_combo = ttk.Combobox(school_frame, values=school_names, width=34, state="readonly")
        self.school_combo.pack(side=LEFT, padx=5)

        if school_names:
            self.school_combo.set(school_names[0])

        self.school_combo.bind("<<ComboboxSelected>>", self.on_school_changed)

        # Main Paned View
        main_paned = PanedWindow(self.root, orient=HORIZONTAL)
        main_paned.pack(fill=BOTH, expand=True, padx=8, pady=8)

        left_frame = Frame(main_paned)
        main_paned.add(left_frame, width=440)

        title_frame = Frame(left_frame)
        title_frame.pack(fill=X, pady=5)
        self.list_title_label = Label(title_frame, text="Tests (Selected School DB)", font=('Arial', 12, 'bold'))
        self.list_title_label.pack(side=LEFT)

        self.btn_toggle_source = Button(title_frame, text="Switch to Local Tests 💻", command=self.toggle_test_source, bg="#6c757d", fg="white")
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
        self.tree.column("Name", width=170)
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

        self.btn_push = Button(action_frame, text="☁️ Push Results to Selected School DB", command=self.push_to_postgresql, state=DISABLED, bg="#17a2b8", fg="white")
        self.btn_push.pack(side=LEFT, padx=3)

        self.output_frame = LabelFrame(right_frame, text="CSV Output / Database Results", padx=5, pady=5, font=('Arial', 10, 'bold'))
        self.output_frame.pack(fill=BOTH, expand=True, pady=5)

        view_bar = Frame(self.output_frame)
        view_bar.pack(fill=X, pady=2)
        Button(view_bar, text="View DB Results for Selected Test", command=self.fetch_db_results_for_test).pack(side=LEFT, padx=2)
        Button(view_bar, text="View Latest CSV Preview", command=self.display_latest_csv).pack(side=LEFT, padx=2)

        self.output_text = scrolledtext.ScrolledText(self.output_frame, height=12, wrap=NONE)
        self.output_text.pack(fill=BOTH, expand=True)

        self.status_var = StringVar()
        school_name = self.api_client.selected_school["name"] if self.api_client.selected_school else "School"
        self.status_var.set(f"Ready | Active School: {school_name} | API: {self.settings.get('api_base_url')}")
        self.status_bar = Label(self.root, textvariable=self.status_var, relief=SUNKEN, anchor=W, padx=5, pady=3)
        self.status_bar.pack(fill=X, side=BOTTOM)

        self.refresh_test_list()

        self.current_test_id = None
        self.current_test_data = None

    def on_school_changed(self, event):
        selected_idx = self.school_combo.current()
        if selected_idx >= 0 and selected_idx < len(self.api_client.user_schools):
            self.api_client.selected_school = self.api_client.user_schools[selected_idx]
            school_name = self.api_client.selected_school["name"]
            self.status_var.set(f"Switched active school to: {school_name}")
            self.refresh_test_list()

    def refresh_assigned_schools(self):
        if not self.api_client.current_user:
            return
        email = self.api_client.current_user.get("email", "")
        def fetch():
            try:
                schools = self.api_client.getUserSchools(email)
                def update():
                    self.api_client.user_schools = schools
                    school_names = [f"{s['name']} ({s['code']})" for s in schools]
                    self.school_combo['values'] = school_names
                    if school_names:
                        self.school_combo.set(school_names[0])
                        self.api_client.selected_school = schools[0]
                    self.refresh_test_list()
                    messagebox.showinfo("Refreshed", f"Loaded {len(schools)} assigned schools.")
                self.root.after(0, update)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

        threading.Thread(target=fetch, daemon=True).start()

    def logout(self):
        self.root.destroy()
        new_root = Tk()
        app = TestManagerApp(new_root)
        new_root.mainloop()

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
        self.showing_db_tests = True
        school_name = self.api_client.selected_school["name"] if self.api_client.selected_school else "School"
        self.list_title_label.config(text=f"Tests ({school_name} DB)")
        self.btn_toggle_source.config(text="Switch to Local Tests 💻", bg="#007bff")
        self.refresh_test_list()

    def refresh_test_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.showing_db_tests:
            tests = self.db.get_all_tests()
            for test in tests:
                self.tree.insert("", END, values=test)
            self.status_var.set(f"Loaded {len(tests)} local tests.")
            return

        school_id = self.api_client.selected_school["id"] if self.api_client.selected_school else 1
        school_name = self.api_client.selected_school["name"] if self.api_client.selected_school else "School"

        self.status_var.set(f"Fetching tests for '{school_name}' from database...")

        def fetch():
            try:
                db_tests = self.api_client.get_tests_for_school(school_id)
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
                    self.status_var.set(f"Loaded {len(db_tests)} tests for {school_name}.")
                self.root.after(0, update)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("API Error", f"Failed to fetch tests:\n{e}"))

        threading.Thread(target=fetch, daemon=True).start()

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
                school_name = self.api_client.selected_school["name"] if self.api_client.selected_school else "School"
                source = f"PostgreSQL DB ({school_name})" if self.showing_db_tests else "Local SQLite"
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
        test = (
            self.current_test_data["id"],
            self.current_test_data["name"],
            self.current_test_data["date"],
            self.current_test_data["template"]
        )
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
            os.path.join(os.path.expanduser("~"), "Downloads", "templates")
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

        Button(dialog, text="📁 Browse Dir", command=browse_template_dir).grid(row=2, column=2, padx=5)

        def save():
            name = name_var.get().strip()
            date = date_var.get().strip()
            template = template_var.get().strip()

            if not name or not date or not template:
                messagebox.showerror("Error", "All fields are required.")
                return

            def push_and_save():
                try:
                    if test_data:
                        test_id = test_data[0]
                        if not self.showing_db_tests:
                            self.db.update_test(test_id, name, date, template)
                        self.api_client.update_test(test_id, name, date, template)
                    else:
                        if not self.showing_db_tests:
                            self.db.insert_test(name, date, template)
                        self.api_client.create_test_for_school(name, date, template)

                    self.root.after(0, lambda: self.refresh_test_list())
                    self.root.after(0, lambda: dialog.destroy())
                    school_name = self.api_client.selected_school["name"] if self.api_client.selected_school else "School"
                    self.root.after(0, lambda: messagebox.showinfo("Success", f"Test '{name}' saved for {school_name}."))
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
                    self.api_client.delete_test(test_id)
                    self.root.after(0, lambda: self.refresh_test_list())
                    self.root.after(0, lambda: self.on_test_select(None))
                    self.root.after(0, lambda: messagebox.showinfo("Deleted", f"Test {test_id} deleted."))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

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
            if not messagebox.askyesno("PDF Info", f"Selected PDF has {page_count} page(s).\n\nProceed with processing?"):
                return
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read PDF: {e}")
            return

        self.status_var.set("Processing PDF...")
        def process():
            try:
                template = self.current_test_data["template"]
                def progress(msg):
                    self.root.after(0, lambda: self.status_var.set(msg))
                self.processor.process_pdf(pdf_path, template, progress_callback=progress)
                self.root.after(0, lambda: messagebox.showinfo("Success", "PDF pages converted & template files copied."))
                self.root.after(0, lambda: self.status_var.set("Ready"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, lambda: self.status_var.set("Error"))

        threading.Thread(target=process, daemon=True).start()

    def run_command(self):
        if not self.current_test_data:
            return
        if not messagebox.askyesno("Run OMR Command", "Run the configured Python OMR command now?"):
            return

        self.status_var.set("Running OMR script...")
        def run():
            try:
                def progress(msg):
                    self.root.after(0, lambda: self.status_var.set(msg))
                self.processor.run_command(progress_callback=progress)
                self.root.after(0, lambda: messagebox.showinfo("Success", "OMR command executed successfully!"))
                self.root.after(0, self.display_latest_csv)
                self.root.after(0, lambda: self.status_var.set("Ready"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.root.after(0, lambda: self.status_var.set("Error running command"))

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
                    self.output_text.insert(END, f"📄 Latest CSV: {os.path.basename(latest)}\n")
                    self.output_text.insert(END, "=" * 60 + "\n")
                    self.output_text.insert(END, " | ".join(headers) + "\n")
                    self.output_text.insert(END, "-" * 60 + "\n")
                    for row in rows:
                        self.output_text.insert(END, " | ".join(str(row.get(h, "")) for h in headers) + "\n")
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
        school_name = self.api_client.selected_school["name"] if self.api_client.selected_school else "School"

        self.status_var.set(f"Fetching results for '{test_name}' ({school_name})...")
        self.output_text.delete(1.0, END)

        def fetch():
            try:
                results = self.api_client.get_test_results_for_school(test_id)
                def display():
                    self.output_text.delete(1.0, END)
                    if not results:
                        self.output_text.insert(END, f"No OMR results stored in database for test '{test_name}' under {school_name}.\n\nRun OMR processing and click 'Push Results to Selected School DB' to upload results.")
                        return

                    self.output_text.insert(END, f"🌐 Database Results for '{test_name}' - {school_name} (Total Rows: {len(results)})\n")
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

                    self.status_var.set(f"Displayed {len(results)} DB result rows for {school_name}.")

                self.root.after(0, display)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("API Error", str(e)))

        threading.Thread(target=fetch, daemon=True).start()

    def push_to_postgresql(self):
        if not self.current_test_data:
            return
        output_dir = self.settings.get("output_dir")
        if not output_dir or not os.path.exists(output_dir):
            messagebox.showwarning("Warning", "Output directory not configured.")
            return

        csv_files = self.processor.get_csv_files(output_dir)
        if not csv_files:
            messagebox.showwarning("No CSV", "No OMR CSV result files found in output directory.")
            return

        csv_files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        latest_csv = csv_files[0]
        test_id = self.current_test_data["id"]
        test_name = self.current_test_data["name"]
        school_name = self.api_client.selected_school["name"] if self.api_client.selected_school else "School"

        if not messagebox.askyesno("Push to Database", f"Push OMR results from '{os.path.basename(latest_csv)}' to database for test '{test_name}' under school '{school_name}'?"):
            return

        self.status_var.set(f"Pushing CSV data for {school_name}...")

        def upload():
            try:
                def progress(msg):
                    self.root.after(0, lambda: self.status_var.set(msg))

                self.api_client.upload_csv_for_school(
                    csv_path=latest_csv,
                    test_id=test_id,
                    test_name=test_name,
                    progress_callback=progress
                )
                self.root.after(0, lambda: messagebox.showinfo("Success", f"OMR results successfully uploaded for '{school_name}'!"))
                self.root.after(0, lambda: self.status_var.set(f"Uploaded results to {school_name} successfully."))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Upload Error", str(e)))

        threading.Thread(target=upload, daemon=True).start()

    def check_api_status(self):
        self.status_var.set("Checking API status...")
        def check():
            online, details = self.api_client.check_health()
            msg = f"API Status: ONLINE 🟢\nBase URL: {self.api_client.api_base_url}\nDetails: {details}" if online else f"API Offline: {details}"
            self.root.after(0, lambda: messagebox.showinfo("API Connection Status", msg))

        threading.Thread(target=check, daemon=True).start()

    def open_settings(self):
        settings_win = Toplevel(self.root)
        settings_win.title("Preferences & API Settings")
        settings_win.geometry("560x360")
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
        Label(settings_win, text="Express / Strapi API URL:").grid(row=row, column=0, sticky=W, padx=8, pady=6)
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
            messagebox.showinfo("Settings Saved", "Preferences updated successfully.")
            settings_win.destroy()

        Button(settings_win, text="Save Settings", command=save_settings, width=15, bg="#007bff", fg="white").grid(row=row, column=0, pady=20)
        Button(settings_win, text="Cancel", command=settings_win.destroy, width=12).grid(row=row, column=1, pady=20)


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