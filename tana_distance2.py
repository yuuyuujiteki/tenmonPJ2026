import asyncio
import threading
import tkinter as tk
import customtkinter as ctk
from bleak import BleakClient, BleakScanner

# --- BLE設定 ---
SERVICE_UUID = "12345678-1234-1234-1234-1234567890ab"
CHARACTERISTIC_UUID = "87654321-4321-4321-4321-ba0987654321"
DEVICE_NAME = "ESP32S3_Sensor"

# UIのテーマ設定
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class DistanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ESP32-S3 距離モニター")
        # 400x350 の2倍に設定
        self.geometry("800x700")
        self.resizable(False, False)

        # タイトルラベル（フォント 20 -> 40, pady 20 -> 40）
        self.title_label = ctk.CTkLabel(self, text="VL53L1X センサーモニター", font=ctk.CTkFont(size=40, weight="bold"))
        self.title_label.pack(pady=40)

        # 接続ステータス表示（フォント 14 -> 28, pady 5 -> 10）
        self.status_label = ctk.CTkLabel(self, text="ステータス: スキャン中...", font=ctk.CTkFont(size=28), text_color="orange")
        self.status_label.pack(pady=10)

        # 距離表示フレーム（pady 20 -> 40）
        self.dist_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.dist_frame.pack(pady=40)

        # 数値ラベル（フォント 54 -> 108, padx 5 -> 10）
        self.dist_value_label = ctk.CTkLabel(self.dist_frame, text="---", font=ctk.CTkFont(size=108, weight="bold"))
        self.dist_value_label.pack(side="left", padx=10)

        # 単位ラベル（フォント 20 -> 40, pady 10 -> 20）
        self.dist_unit_label = ctk.CTkLabel(self.dist_frame, text="cm", font=ctk.CTkFont(size=40))
        self.dist_unit_label.pack(side="bottom", pady=20)

        # 状態（NEAR / FAR）バッジ（フォント 16 -> 32, width 150->300, height 35->70, corner_radius 6->12, pady 10->20）
        self.state_label = ctk.CTkLabel(self, text="待機中", font=ctk.CTkFont(size=32, weight="bold"), 
                                        fg_color="gray", corner_radius=12, width=300, height=70)
        self.state_label.pack(pady=20)

        # バックグラウンドでBLE通信を走らせるためのスレッド開始
        self.loop_thread = threading.Thread(target=self.start_ble_thread, daemon=True)
        self.loop_thread.start()

    def update_ui(self, distance_str, status_str):
        # メインスレッドから安全にUIを更新
        self.dist_value_label.configure(text=distance_str)
        
        if "NEAR" in status_str:
            self.state_label.configure(text="棚がいっぱいだよ！もう持ってこないで！", fg_color="#2b8a3e") # 緑色
        else:
            self.state_label.configure(text="空いてます！まだまだ置けるよ！", fg_color="#364fc7") # 青色

    def set_connection_status(self, text, color):
        self.status_label.configure(text=text, text_color=color)

    def start_ble_thread(self):
        asyncio.run(self.ble_main_loop())

    async def ble_main_loop(self):
        while True:
            try:
                self.set_connection_status(f"ステータス: '{DEVICE_NAME}' をスキャン中...", "orange")
                device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=5.0)
                
                if not device:
                    await asyncio.sleep(2.0)
                    continue

                self.set_connection_status(f"ステータス: 接続中...", "orange")

                async def notification_handler(sender, data):
                    message = data.decode("utf-8")
                    # 受信データ例: "Distance:45cm, Status:FAR"
                    try:
                        # 簡易パース
                        parts = message.split(",")
                        dist_part = parts[0].split(":")[1].replace("cm", "")
                        status_part = parts[1].split(":")[1]
                        
                        # UIへ反映
                        self.after(0, lambda: self.update_ui(dist_part, status_part))
                    except Exception as e:
                        print(f"パースエラー: {e}")

                async with BleakClient(device) as client:
                    self.set_connection_status(f"ステータス: 接続完了 (オンライン)", "green")
                    await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
                    
                    while client.is_connected:
                        await asyncio.sleep(1.0)

            except Exception as e:
                print(f"BLE接続エラー: {e}")
                self.set_connection_status("ステータス: 切断されました（再接続中...）", "red")
                await asyncio.sleep(3.0)

if __name__ == "__main__":
    app = DistanceApp()
    app.mainloop()