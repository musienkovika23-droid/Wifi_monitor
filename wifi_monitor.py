import tkinter as tk
import os
import platform
import subprocess
import time
from tkinter import messagebox

log_file = "wifi_history.txt"


def run_command(command):
    try:
        return subprocess.check_output(command, shell=True, stderr=subprocess.DEVNULL, text=True)
    except subprocess.CalledProcessError:
        return ""


def parse_windows_wifi(results):
    ssid = "Відключено"
    signal = 0
    for line in results.splitlines():
        if "SSID" in line and "BSSID" not in line:
            ssid = line.split(":", 1)[1].strip()
        if "Signal" in line:
            try:
                signal = int(line.split(":", 1)[1].replace('%', '').strip())
            except ValueError:
                signal = 0
    return ssid, signal


def parse_macos_wifi(results):
    ssid = "Відключено"
    signal = 0
    rssi = None
    for line in results.splitlines():
        if "SSID:" in line:
            ssid = line.split(":", 1)[1].strip()
        elif "agrCtlRSSI:" in line:
            try:
                rssi = int(line.split(":", 1)[1].strip())
            except ValueError:
                rssi = None
    if rssi is not None:
        signal = max(0, min(100, (rssi + 100) * 2))
    return ssid, signal


def parse_linux_wifi(results):
    ssid = "Відключено"
    signal = 0
    for line in results.splitlines():
        if line.startswith("yes:"):
            parts = line.split(":")
            if len(parts) >= 3:
                ssid = parts[1]
                try:
                    signal = int(parts[2])
                except ValueError:
                    signal = 0
            break
    return ssid, signal


def get_wifi_data():
    system = platform.system()
    if system == "Windows":
        results = run_command('netsh wlan show interfaces')
        return parse_windows_wifi(results)
    if system == "Darwin":
        airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        if os.path.exists(airport_path):
            results = run_command(f'"{airport_path}" -I')
            return parse_macos_wifi(results)

        results = run_command("networksetup -getairportnetwork en0")
        ssid = "Відключено"
        if ": " in results:
            ssid = results.split(": ", 1)[1].strip()
        return ssid, 0

    results = run_command("nmcli -t -f active,ssid,signal dev wifi")
    return parse_linux_wifi(results)


def save_to_file(ssid, signal):
    timestamp = time.strftime("%H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] Мережа: {ssid} | Сигнал: {signal}%\n")


def update_loop():
    ssid, signal = get_wifi_data()
    signal = max(0, min(int(signal), 100))

    label_ssid.config(text=f"SSID: {ssid}")
    label_percent.config(text=f"{signal}%")

    if signal > 75:
        color = "#2ecc71"
    elif signal > 40:
        color = "#f1c40f"
    else:
        color = "#e74c3c"

    width = 5 + (signal * 3.4)
    canvas.coords(bar, 5, 5, min(width, 345), 35)
    canvas.itemconfig(bar, fill=color)

    log_box.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] Сигнал: {signal}%\n")
    log_box.see(tk.END)

    if int(time.time()) % 5 == 0:
        save_to_file(ssid, signal)

    if signal < 20 and ssid != "Відключено":
        label_warning.config(text="УВАГА: НИЗЬКИЙ СИГНАЛ!", fg="red")
    else:
        label_warning.config(text="")

    root.after(1000, update_loop)


def open_log_folder():
    system = platform.system()
    cwd = os.getcwd()
    try:
        if system == "Windows":
            os.startfile(cwd)
        elif system == "Darwin":
            subprocess.Popen(["open", cwd])
        else:
            subprocess.Popen(["xdg-open", cwd])
    except Exception:
        messagebox.showerror("Помилка", "Не вдалося відкрити папку з логами.")


def clear_log():
    if os.path.exists(log_file):
        os.remove(log_file)
    log_box.delete(1.0, tk.END)
    messagebox.showinfo("Успіх", "Історія очищена!")


root = tk.Tk()
root.title("Wi-Fi Analyzer Tool")
root.geometry("400x500")
root.config(bg="#121212")

tk.Label(root, text="Wi-Fi Monitor", font=("Arial", 18, "bold"), bg="#121212", fg="#00FF00").pack(pady=10)
label_ssid = tk.Label(root, text="SSID: Пошук...", font=("Arial", 12), bg="#121212", fg="white")
label_ssid.pack()

label_percent = tk.Label(root, text="0%", font=("Arial", 40, "bold"), bg="#121212", fg="white")
label_percent.pack()

canvas = tk.Canvas(root, width=350, height=40, bg="#333", highlightthickness=0)
canvas.pack(pady=10)
bar = canvas.create_rectangle(5, 5, 5, 35, fill="green", outline="")

label_warning = tk.Label(root, text="", font=("Arial", 10, "bold"), bg="#121212")
label_warning.pack()

tk.Label(root, text="Історія сигналу:", bg="#121212", fg="gray").pack()
log_box = tk.Text(root, width=40, height=8, bg="#222", fg="#00FF00", font=("Consolas", 9))
log_box.pack(pady=5)

btn_frame = tk.Frame(root, bg="#121212")
btn_frame.pack(pady=10)

tk.Button(btn_frame, text="Файли", command=open_log_folder, width=12).grid(row=0, column=0, padx=5)
tk.Button(btn_frame, text="Очистити", command=clear_log, width=12).grid(row=0, column=1, padx=5)

update_loop()
root.mainloop()