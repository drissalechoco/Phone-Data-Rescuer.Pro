import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import os
from datetime import datetime
from carver_engine import PhoneRescueEngine, get_base_dir

class PhoneRescueApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Phone Data Rescuer Pro - أداة صيانة وإنقاذ بيانات الهواتف")
        self.root.geometry("650x540")
        self.root.resizable(False, False)

        self.engine = PhoneRescueEngine()
        self.base_output = os.path.join(get_base_dir(), "Recovered_Data")
        os.makedirs(self.base_output, exist_ok=True)

        self.setup_ui()

    def setup_ui(self):
        # العنوان الرئيسي
        header_frame = tk.Frame(self.root, bg="#1b263b", pady=12)
        header_frame.pack(fill="x")
        tk.Label(
            header_frame,
            text="Phone Data Rescuer Pro v1.0",
            font=("Segoe UI", 15, "bold"),
            fg="white",
            bg="#1b263b"
        ).pack()
        tk.Label(
            header_frame,
            text="إنقاذ وسائط واتساب والصور قبل التفليش + استعادة الملفات من الذاكرة",
            font=("Segoe UI", 9),
            fg="#e0e1dd",
            bg="#1b263b"
        ).pack()

        # نظام التبويبات (Tabs)
        notebook = ttk.Notebook(self.root)
        notebook.pack(pady=10, padx=15, fill="both", expand=True)

        # التبويب الأول: الإنقاذ قبل التفليش عبر ADB
        tab_adb = ttk.Frame(notebook)
        notebook.add(tab_adb, text="  1. إنقاذ البيانات قبل التفليش (ADB)  ")

        tk.Label(tab_adb, text="اسم الزبون أو نوع الهاتف:", font=("Segoe UI", 10, "bold")).pack(pady=(15, 5))
        self.customer_entry = tk.Entry(tab_adb, font=("Segoe UI", 11), width=40, justify="center")
        self.customer_entry.pack(pady=5)

        adb_btn_frame = tk.Frame(tab_adb)
        adb_btn_frame.pack(pady=15)

        self.btn_check_adb = tk.Button(
            adb_btn_frame,
            text="فحص اتصال الهاتف",
            font=("Segoe UI", 10, "bold"),
            bg="#415a77",
            fg="white",
            width=20,
            command=self.check_adb
        )
        self.btn_check_adb.grid(row=0, column=0, padx=8)

        self.btn_pull_adb = tk.Button(
            adb_btn_frame,
            text="بدء سحب البيانات الآن",
            font=("Segoe UI", 10, "bold"),
            bg="#2e7d32",
            fg="white",
            width=22,
            command=self.start_adb_rescue
        )
        self.btn_pull_adb.grid(row=0, column=1, padx=8)

        # التبويب الثاني: الفحص العميق لبطاقات الذاكرة وملفات الـ Dump
        tab_carve = ttk.Frame(notebook)
        notebook.add(tab_carve, text="  2. استعادة من بطاقة SD أو ملف Dump  ")

        tk.Label(tab_carve, text="اختر ملف صورة الذاكرة (.bin / .img) أو اكتب حرف القرص (مثل \\\\.\\E:):", font=("Segoe UI", 9, "bold")).pack(pady=(15, 5))
        
        path_frame = tk.Frame(tab_carve)
        path_frame.pack(pady=5)

        self.source_entry = tk.Entry(path_frame, font=("Segoe UI", 10), width=42)
        self.source_entry.grid(row=0, column=0, padx=5)

        tk.Button(
            path_frame,
            text="اختيار ملف...",
            font=("Segoe UI", 9),
            command=self.browse_dump_file
        ).grid(row=0, column=1)

        self.btn_start_carve = tk.Button(
            tab_carve,
            text="بدء الفحص العميق واستخراج الملفات",
            font=("Segoe UI", 10, "bold"),
            bg="#d84315",
            fg="white",
            width=30,
            command=self.start_carving
        )
        self.btn_start_carve.pack(pady=15)

        # شاشة عرض السجل (Log) المشتركة
        log_frame = tk.Frame(self.root)
        log_frame.pack(padx=15, pady=(0, 10), fill="both", expand=True)

        top_log_bar = tk.Frame(log_frame)
        top_log_bar.pack(fill="x")
        tk.Label(top_log_bar, text="سجل العمليات المباشر:", font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(top_log_bar, text="فتح مجلد الملفات المستعادة", font=("Segoe UI", 8), command=self.open_output_folder).pack(side="right")

        self.log_box = scrolledtext.ScrolledText(log_frame, height=12, font=("Consolas", 9), bg="#0d1b2a", fg="#e0e1dd")
        self.log_box.pack(fill="both", expand=True, pady=(5, 0))

    def log(self, text):
        self.root.after(0, lambda: self._append_log(text))

    def _append_log(self, text):
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)

    def open_output_folder(self):
        if os.path.exists(self.base_output):
            os.startfile(self.base_output)

    def browse_dump_file(self):
        file_path = filedialog.askopenfilename(
            title="اختر ملف صورة الذاكرة (Dump)",
            filetypes=[("Dump & Image Files", "*.bin *.img *.dd *.raw"), ("All Files", "*.*")]
        )
        if file_path:
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, file_path)

    def check_adb(self):
        self.log_box.delete(1.0, tk.END)
        res = self.engine.check_adb_device()
        if res == "ADB_MISSING":
            self.log("[-] خطأ: يرجى وضع ملفات adb.exe في نفس مجلد البرنامج.")
        elif isinstance(res, list) and len(res) > 0:
            self.log(f"[✔] تم التعرف على الهاتف بنجاح: {res}")
        else:
            self.log("[-] لا يوجد هاتف متصل. تأكد من توصيل الكابل وتفعيل ADB أو وضع TWRP.")

    def start_adb_rescue(self):
        name = self.customer_entry.get()
        self.btn_pull_adb.config(state=tk.DISABLED)
        self.log_box.delete(1.0, tk.END)
        threading.Thread(target=self._run_adb, args=(name,), daemon=True).start()

    def _run_adb(self, name):
        self.engine.rescue_via_adb(name, self.base_output, self.log)
        self.root.after(0, lambda: self.btn_pull_adb.config(state=tk.NORMAL))

    def start_carving(self):
        source = self.source_entry.get().strip()
        if not source:
            messagebox.showwarning("تنبيه", "يرجى إدخال مسار القرص أو اختيار ملف Dump أولاً.")
            return
        self.btn_start_carve.config(state=tk.DISABLED)
        self.log_box.delete(1.0, tk.END)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        out_dir = os.path.join(self.base_output, f"Carved_{timestamp}")
        threading.Thread(target=self._run_carve, args=(source, out_dir), daemon=True).start()

    def _run_carve(self, source, out_dir):
        self.engine.carve_raw_data(source, out_dir, self.log)
        self.root.after(0, lambda: self.btn_start_carve.config(state=tk.NORMAL))

if __name__ == "__main__":
    root = tk.Tk()
    app = PhoneRescueApp(root)
    root.mainloop()
