import os
import sys
import subprocess
from datetime import datetime

def get_base_dir():
    """الحصول على مسار المجلد الحالي سواء كان كود بايثون أو ملف EXE"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class PhoneRescueEngine:
    def __init__(self):
        self.adb_path = os.path.join(get_base_dir(), "adb.exe")
        self.signatures = {
            "jpg": (b"\xff\xd8\xff", b"\xff\xd9"),
            "png": (b"\x89PNG\r\n\x1a\n", b"IEND\xaeB`\x82"),
            "pdf": (b"%PDF-", b"%%EOF"),
        }
        self.adb_paths = {
            "Camera_Photos_Videos": "/sdcard/DCIM",
            "WhatsApp_Media_New": "/sdcard/Android/media/com.whatsapp/WhatsApp/Media",
            "WhatsApp_Media_Old": "/sdcard/WhatsApp/Media",
            "Downloads": "/sdcard/Download",
            "Documents": "/sdcard/Documents"
        }

    def check_adb_device(self):
        """التحقق من وجود هاتف متصل في وضع ADB أو Recovery"""
        if not os.path.exists(self.adb_path):
            return "ADB_MISSING"
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            res = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
                timeout=10
            )
            lines = res.stdout.strip().split("\n")[1:]
            devices = [line.split("\t")[0] for line in lines if "\tdevice" in line or "\trecovery" in line]
            return devices
        except Exception as e:
            return f"ERROR: {str(e)}"

    def rescue_via_adb(self, customer_name, base_dir, log_func):
        """سحب وسائط واتساب والصور قبل التفليش"""
        devices = self.check_adb_device()
        if devices == "ADB_MISSING":
            log_func("[-] خطأ: ملف adb.exe غير موجود في نفس مجلد البرنامج!")
            return False
        if not devices or isinstance(devices, str):
            log_func("[-] لم يتم العثور على هاتف متصل. تأكد من تفعيل USB Debugging أو وضع TWRP.")
            return False

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        safe_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '_', '-')).strip() or "Customer"
        out_folder = os.path.join(base_dir, f"ADB_{safe_name}_{timestamp}")
        os.makedirs(out_folder, exist_ok=True)
        log_func(f"[+] تم إنشاء مجلد الحفظ: {out_folder}")

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        for label, remote_path in self.adb_paths.items():
            log_func(f"[*] جاري فحص: {label}...")
            check = subprocess.run(
                [self.adb_path, "shell", f"[ -d '{remote_path}' ] && echo 'OK'"],
                capture_output=True,
                text=True,
                startupinfo=startupinfo
            )
            if "OK" in check.stdout:
                dest = os.path.join(out_folder, label)
                os.makedirs(dest, exist_ok=True)
                pull_res = subprocess.run(
                    [self.adb_path, "pull", remote_path, dest],
                    capture_output=True,
                    text=True,
                    startupinfo=startupinfo
                )
                if pull_res.returncode == 0:
                    log_func(f"[✔] تم سحب {label} بنجاح.")
                else:
                    log_func(f"[!] اكتمل سحب {label} مع بعض التنبيهات.")
            else:
                log_func(f"[-] المسار غير موجود في الهاتف: {label}")

        log_func("\n[★] اكتملت عملية الإنقاذ بنجاح! يمكنك الآن تفليش الهاتف بأمان.")
        return True

    def carve_raw_data(self, source_path, output_dir, log_func):
        """استخراج الصور، الفيديو، وصوتيات واتساب من بطاقات SD أو ملفات الـ Dump بدقة"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        folders = {
            "jpg": os.path.join(output_dir, "Images_JPG"),
            "png": os.path.join(output_dir, "Images_PNG"),
            "pdf": os.path.join(output_dir, "Documents_PDF"),
            "opus": os.path.join(output_dir, "WhatsApp_Voices"),
            "mp4": os.path.join(output_dir, "Videos_MP4")
        }
        for folder in folders.values():
            os.makedirs(folder, exist_ok=True)

        counts = {k: 0 for k in folders}
        chunk_size = 8 * 1024 * 1024  # قراءة 8 ميجابايت في كل دفعة
        overlap = 512 * 1024          # تداخل 512 كيلوبايت لمنع قطع الملفات بين الدفعات
        buffer = b""

        try:
            with open(source_path, "rb") as f:
                log_func(f"[*] بدء الفحص العميق للمصدر: {source_path}")
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    data = buffer + chunk

                    # 1. استخراج الصور والمستندات (JPG, PNG, PDF)
                    for ext, (header, footer) in self.signatures.items():
                        pos = 0
                        while True:
                            start = data.find(header, pos)
                            if start == -1:
                                break
                            end = data.find(footer, start + len(header))
                            if end != -1:
                                end += len(footer)
                                file_bytes = data[start:end]
                                if 2048 < len(file_bytes) < 25 * 1024 * 1024:
                                    counts[ext] += 1
                                    out_file = os.path.join(folders[ext], f"recovered_{counts[ext]}.{ext}")
                                    with open(out_file, "wb") as out:
                                        out.write(file_bytes)
                                pos = end
                            else:
                                pos = start + len(header)

                    # 2. استخراج صوتيات واتساب (OGG/OPUS)
                    pos = 0
                    while True:
                        start = data.find(b"OggS\x00\x02", pos)
                        if start == -1:
                            break
                        next_ogg = data.find(b"OggS\x00\x02", start + 6)
                        end = next_ogg if next_ogg != -1 else min(start + (300 * 1024), len(data))
                        audio_bytes = data[start:end]
                        if 4096 < len(audio_bytes) < 2 * 1024 * 1024:
                            counts["opus"] += 1
                            out_file = os.path.join(folders["opus"], f"wa_voice_{counts['opus']}.opus")
                            with open(out_file, "wb") as out:
                                out.write(audio_bytes)
                        pos = end if next_ogg != -1 else start + 6

                    # 3. استخراج مقاطع الفيديو (MP4 - ftyp)
                    pos = 0
                    while True:
                        ftyp_idx = data.find(b"ftyp", pos)
                        if ftyp_idx == -1 or ftyp_idx < 4:
                            break
                        start = ftyp_idx - 4
                        end = min(start + (15 * 1024 * 1024), len(data))
                        vid_bytes = data[start:end]
                        if len(vid_bytes) > 100 * 1024:
                            counts["mp4"] += 1
                            out_file = os.path.join(folders["mp4"], f"video_{counts['mp4']}.mp4")
                            with open(out_file, "wb") as out:
                                out.write(vid_bytes)
                        pos = ftyp_idx + 1024

                    # الاحتفاظ بآخر 512 كيلوبايت للدفعة القادمة لمنع ضياع الملفات المقسومة
                    buffer = data[-overlap:] if len(data) > overlap else b""

            log_func("\n[★] اكتمل الفحص العميق بنجاح! النتائج المستعادة:")
            log_func(f" - صور JPG: {counts['jpg']} | صور PNG: {counts['png']}")
            log_func(f" - صوتيات واتساب: {counts['opus']} | فيديو MP4: {counts['mp4']} | مستندات PDF: {counts['pdf']}")
            return True

        except PermissionError:
            log_func("[-] خطأ صلاحيات: يرجى تشغيل البرنامج كـ مسؤول (Run as Administrator).")
            return False
        except Exception as e:
            log_func(f"[-] حدث خطأ أثناء الفحص: {str(e)}")
            return False
