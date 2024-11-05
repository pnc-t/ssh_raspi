import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinter import ttk
import paramiko
from PIL import ImageColor
import threading
import socket
from PIL import Image, ImageTk
import time


# アプリ全体のテーマ設定
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class TerminalApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # SSH接続情報
        self.hostname = "raspberrypi.local"
        self.username = "pi"
        self.password = "raspberry"
        self.ssh = None
        self.sftp = None
        self.shell = None

        # フォント設定
        self.output_font = ("Courier", 12)
        self.tree_font = ("Arial", 9)

        # カラーテーマ
        self.THEME_COLOR = "#1A1A1A"
        self.HOVER_COLOR = "#333333"
        self.ACTIVE_COLOR = "#444444"
        self.TEXT_COLOR = "#FFFFFF"
        self.BG_COLOR = "#000000"
        self.WINDOW_COLOR = "#000000"
        self.SHELL_COLOR = "#000000"

        self.current_dir = os.path.dirname(os.path.abspath(__file__))

        self.iconfile = "ssh_raspi/icon/icon.ico"

        self.light_connect_image = Image.open("ssh_raspi/icon/con_b.png")
        self.dark_connect_image = Image.open("ssh_raspi/icon/con_w.png")
        self.light_select_image = Image.open("ssh_raspi/icon/fol_b.png")
        self.dark_select_image = Image.open("ssh_raspi/icon/fol_w.png")
        self.light_exucute_image = Image.open("ssh_raspi/icon/sta_b.png")
        self.dark_exucute_image = Image.open("ssh_raspi/icon/sta_w.png")
        self.light_stop_image = Image.open("ssh_raspi/icon/stop_b.png")
        self.dark_stop_image = Image.open("ssh_raspi/icon/stop_w.png")

        self.create_widgets()
        self.setup_window_style()
        self.setup_treeview_style()

        self.current_process = None
        self.process_running = False

        # shellをchannelに変更
        self.channel = None  # 以前のself.shell = Noneから変更

        # 新しい変数追加
        self.shell_running = False
        self.receive_buffer = ""

        # コマンド履歴用の変数を追加
        self.command_history = []
        self.history_index = -1

    def setup_window_style(self):
        self.configure(fg_color=self.WINDOW_COLOR)
        self.title("Terminal SSH")
        self.iconbitmap(default=self.iconfile)
        self.geometry("1200x700")
        self.option_add("*Font", self.output_font)

    def setup_treeview_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Custom.Treeview",
            font=self.tree_font,
            background=self.lighten_color(self.BG_COLOR),
            foreground=self.TEXT_COLOR,
            rowheight=25,
            fieldbackground=self.lighten_color(self.SHELL_COLOR),
            borderwidth=0,
            relief="solid",
        )
        style.map(
            "Custom.Treeview",
            background=[("selected", self.HOVER_COLOR)],
            foreground=[("selected", self.TEXT_COLOR)],
        )

    def create_widgets(self):
        # 左側のフレーム（ツリービュー）
        self.left_frame = ctk.CTkFrame(self, width=300, fg_color=self.BG_COLOR)
        self.left_frame.pack(side="left", fill="y")

        # 右側のフレーム（出力ボックス）
        self.right_frame = ctk.CTkFrame(self, fg_color=self.BG_COLOR)
        self.right_frame.pack(side="right", fill="both", expand=True)

        # ボタンフレーム
        self.button_frame = ctk.CTkFrame(self.right_frame, fg_color=self.BG_COLOR)
        self.button_frame.pack(fill="x", padx=5, pady=5)

        # ボタンのスタイル設定
        button_style = {
            "font": self.output_font,
            "text_color": self.TEXT_COLOR,
            "fg_color": self.THEME_COLOR,
            "hover_color": self.HOVER_COLOR,
            "corner_radius": 0,
            "border_width": 1,
            "border_color": self.TEXT_COLOR,
            "height": 32,
        }

        self.connect_image = ctk.CTkImage(
            light_image=self.light_connect_image,
            dark_image=self.dark_connect_image,
            size=(20, 20),
        )

        self.select_image = ctk.CTkImage(
            light_image=self.light_select_image,
            dark_image=self.dark_select_image,
            size=(20, 20),
        )
        self.exucute_image = ctk.CTkImage(
            light_image=self.light_exucute_image,
            dark_image=self.dark_exucute_image,
            size=(20, 20),
        )
        self.stop_image = ctk.CTkImage(
            light_image=self.light_stop_image,
            dark_image=self.dark_stop_image,
            size=(20, 20),
        )
        # コネクトsshボタン
        self.connect_button = ctk.CTkButton(
            self.button_frame,
            text="Connect",
            command=self.connect_ssh,
            **button_style,
            image=self.connect_image,
        )
        self.connect_button.pack(padx=5, pady=5, side="left")

        # ディレクトリ選択ボタン
        self.select_button = ctk.CTkButton(
            self.button_frame,
            text="Select Dir",
            command=self.select_directory,
            **button_style,
            image=self.select_image,
        )
        self.select_button.pack(padx=5, pady=5, side="left")

        # 実行ボタン
        self.execute_button = ctk.CTkButton(
            self.button_frame,
            text="Run",
            command=self.execute_file,
            **button_style,
            image=self.exucute_image,
        )
        self.execute_button.pack(padx=5, pady=5, side="right")

        # ストップボタン
        self.stop_button = ctk.CTkButton(
            self.button_frame,
            text="Stop",
            command=self.stop_execution,
            **button_style,
            image=self.stop_image,
        )
        self.stop_button.pack(padx=5, pady=5, side="right")
        self.stop_button.configure(state="disabled")

        # ツリービュー（左側）
        self.tree = ttk.Treeview(
            self.left_frame, show="tree", selectmode="browse", style="Custom.Treeview"
        )
        self.tree.pack(padx=10, pady=10, fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # 出力ボックス（右側）
        self.output_box = ctk.CTkTextbox(
            self.right_frame,
            fg_color=self.BG_COLOR,
            text_color=self.TEXT_COLOR,
            font=self.output_font,
        )
        self.output_box.pack(padx=10, pady=10, fill="both", expand=True)
        self.output_box.configure(state="disabled")

        # シェルコマンド入力
        self.command_entry = ctk.CTkEntry(
            self.right_frame,
            fg_color=self.THEME_COLOR,
            text_color=self.TEXT_COLOR,
            font=self.output_font,
            border_color=self.TEXT_COLOR,
            border_width=1,
            corner_radius=0,
        )
        self.command_entry.pack(padx=10, pady=5, fill="x")
        self.command_entry.bind("<Return>", self.execute_command)
        # command_entryのバインド追加
        self.command_entry.bind("<Up>", self.on_up_key)
        self.command_entry.bind("<Down>", self.on_down_key)

    def connect_ssh(self):
        self.append_to_output("Connecting...\n")
        thread = threading.Thread(target=self.client)
        thread.daemon = True
        thread.start()

    def client(self):
        try:
            if self.ssh:
                self.ssh.close()
            if self.sftp:
                self.sftp.close()
            if self.channel:
                self.channel.close()

            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                self.hostname, username=self.username, password=self.password
            )

            # インタラクティブシェルの設定
            self.channel = self.ssh.invoke_shell()
            self.channel.settimeout(0.1)
            self.sftp = self.ssh.open_sftp()

            # シェル監視スレッドの開始
            self.shell_running = True
            threading.Thread(target=self.monitor_shell, daemon=True).start()

            self.append_to_output("Connection successful\n")

        except Exception as e:
            self.ssh = None
            self.sftp = None
            self.channel = None
            self.append_to_output(f"Connection failed: {str(e)}\n")

    def monitor_shell(self):
        while self.shell_running and self.channel:
            try:
                if self.channel.recv_ready():
                    data = self.channel.recv(1024).decode("utf-8", errors="ignore")
                    self.receive_buffer += data
                    self.process_buffer()
                time.sleep(0.1)
            except socket.timeout:
                continue
            except Exception as e:
                if self.shell_running:
                    self.append_to_output(f"Shell error: {str(e)}\n")
                break

    def process_buffer(self):
        while "\n" in self.receive_buffer:
            line, self.receive_buffer = self.receive_buffer.split("\n", 1)
            # プロンプト行とコマンド行を無視
            if (
                not line.endswith("$ ")
                and not line.endswith("# ")
                and not line.startswith("pi@")
                and line.strip()
            ):  # 空行も無視
                self.append_to_output(line + "\n")

        # バッファをクリア
        if self.receive_buffer.endswith("$ ") or self.receive_buffer.endswith("# "):
            self.receive_buffer = ""

    def select_directory(self):
        self.directory = filedialog.askdirectory()
        if self.directory:
            self.append_to_output(f"Selected directory: {self.directory}\n")
            self.load_files(self.directory)
        else:
            self.append_to_output("No directory selected.\n")

    def load_files(self, path):
        for item in self.tree.get_children():
            self.tree.delete(item)

        root_node = self.tree.insert(
            "", "end", text=os.path.basename(path), open=True, values=(path,)
        )
        self.populate_tree(root_node, path)

    def populate_tree(self, parent, path):
        try:
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                isdir = os.path.isdir(full_path)
                oid = self.tree.insert(
                    parent, "end", text=entry, open=False, values=(full_path,)
                )
                if isdir:
                    self.populate_tree(oid, full_path)
        except PermissionError:
            pass

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            selected_item = selected_items[0]
            item = self.tree.item(selected_item)
            self.selected_path = item["values"][0]
            self.append_to_output(f"Selected: {self.selected_path}\n")

    def on_tree_double_click(self, event):
        item = self.tree.selection()[0]
        if self.tree.item(item, "open"):
            self.tree.item(item, open=False)
        else:
            self.tree.item(item, open=True)

    def stop_execution(self):
        if self.process_running and self.current_process:
            try:
                # プロセスの強制終了
                self.append_to_output("Stopping execution...\n")
                if not self.current_process.closed:
                    self.current_process.close()

                # プロセスのクリーンアップ
                stdin, stdout, stderr = self.ssh.exec_command("pkill -f python3")
                self.append_to_output("Execution stopped.\n")

            except Exception as e:
                self.append_to_output(f"Error stopping execution: {str(e)}\n")
            finally:
                self.process_running = False
                self.current_process = None
                self.stop_button.configure(state="disabled")
                self.execute_button.configure(state="normal")

    def execute_file(self):
        if not self.ssh:
            self.append_to_output("Warning: Please connect SSH first.\n")
            messagebox.showwarning("Warning", "Please connect SSH first")
            return

        selected_items = self.tree.selection()
        if not selected_items:
            self.append_to_output("Warning: Please select a file first.\n")
            messagebox.showwarning("Warning", "Please select a file first")
            return

        selected_item = selected_items[0]
        item = self.tree.item(selected_item)
        full_path = item["values"][0]

        # 実行処理を別スレッドで行う
        self.execute_thread = threading.Thread(
            target=self._execute_file_thread, args=(full_path,)
        )
        self.execute_thread.daemon = True
        self.execute_thread.start()

        self.stop_button.configure(state="normal")
        self.execute_button.configure(state="disabled")

    def on_closing(self):
        if self.process_running:
            if messagebox.askokcancel(
                "Quit", "A process is still running. Do you want to stop it and quit?"
            ):
                self.stop_execution()
            else:
                return
        self.quit()

    def _execute_file_thread(self, full_path):
        remote_path = None
        try:
            self.process_running = True
            self.after(0, lambda: self.stop_button.configure(state="normal"))
            self.after(0, lambda: self.execute_button.configure(state="disabled"))

            remote_path = f"/home/pi/{os.path.basename(full_path)}"

            # ファイル転送
            self.append_to_output(f"Uploading to: {remote_path}\n")
            self.sftp.put(full_path, remote_path)

            self.ssh.exec_command(f"chmod +x {remote_path}")

            # スクリプト実行
            self.append_to_output("Executing script...\n")
            stdin, stdout, stderr = self.ssh.exec_command(f"python3 {remote_path}")
            self.current_process = stdout.channel

            # バッファーを使用して出力を処理
            output_buffer = ""
            error_buffer = ""

            while (
                not self.current_process.exit_status_ready()
                and not self.current_process.closed
            ):
                # 出力の読み取りとバッファリング
                if self.current_process.recv_ready():
                    output = self.current_process.recv(1024).decode()
                    output_buffer += output

                    # バッファが一定量たまったら、または改行を含む場合に出力
                    if len(output_buffer) > 1024 or "\n" in output_buffer:
                        self.after(0, lambda x=output_buffer: self.append_to_output(x))
                        output_buffer = ""

                if self.current_process.recv_stderr_ready():
                    error = self.current_process.recv_stderr(1024).decode()
                    error_buffer += error

                    if len(error_buffer) > 1024 or "\n" in error_buffer:
                        self.after(
                            0,
                            lambda x=error_buffer: self.append_to_output(f"Error: {x}"),
                        )
                        error_buffer = ""

                # UIの応答性を維持するためのスリープ
                time.sleep(0.01)

            # 残りのバッファーを処理
            if output_buffer:
                self.after(0, lambda: self.append_to_output(output_buffer))
            if error_buffer:
                self.after(0, lambda: self.append_to_output(f"Error: {error_buffer}"))

        except Exception as e:
            self.after(
                0, lambda: self.append_to_output(f"Error during operation: {str(e)}\n")
            )
            self.after(
                0,
                lambda: messagebox.showerror(
                    "Error", f"Error during operation: {str(e)}"
                ),
            )
        finally:
            # プロセスのクリーンアップ
            if self.current_process and not self.current_process.closed:
                self.current_process.close()

            # リモートファイルの削除
            if remote_path:
                try:
                    self.ssh.exec_command(f"rm -f {remote_path}")
                    stdin, stdout, stderr = self.ssh.exec_command(f"ls {remote_path}")
                    if not stdout.read():
                        self.after(
                            0,
                            lambda: self.append_to_output(
                                f"Remote file removed: {remote_path}\n"
                            ),
                        )
                    else:
                        self.after(
                            0,
                            lambda: self.append_to_output(
                                f"Warning: Could not confirm file removal: {remote_path}\n"
                            ),
                        )
                except Exception as e:
                    self.after(
                        0,
                        lambda: self.append_to_output(
                            f"Error during cleanup: {str(e)}\n"
                        ),
                    )

            self.process_running = False
            self.current_process = None
            self.after(0, lambda: self.stop_button.configure(state="disabled"))
            self.after(0, lambda: self.execute_button.configure(state="normal"))
            self.after(0, lambda: self.append_to_output("Operation completed.\n"))

    def execute_command(self, event=None):
        if not self.ssh or not self.channel:
            messagebox.showwarning("Warning", "Please connect SSH first")
            self.append_to_output("Warning: Please connect SSH first\n")
            return

        command = self.command_entry.get().strip()
        if not command:
            return

        # コマンド履歴に追加
        self.command_history.append(command)
        self.history_index = len(self.command_history)

        thread = threading.Thread(target=self._execute_command_thread, args=(command,))
        thread.daemon = True
        thread.start()

        self.command_entry.delete(0, ctk.END)

    def _execute_command_thread(self, command):
        try:
            # コマンドに改行を追加して送信
            self.channel.send(command + "\n")

        except Exception as e:
            self.append_to_output(f"Error executing command: {str(e)}\n")

    def on_up_key(self, event):
        """コマンド履歴を遡る"""
        if self.command_history:
            self.history_index = max(0, self.history_index - 1)
            if 0 <= self.history_index < len(self.command_history):
                self.command_entry.delete(0, ctk.END)
                self.command_entry.insert(0, self.command_history[self.history_index])
        return "break"  # イベントの伝播を停止

    def on_down_key(self, event):
        """コマンド履歴を進める"""
        if self.command_history:
            self.history_index = min(len(self.command_history), self.history_index + 1)
            self.command_entry.delete(0, ctk.END)
            if self.history_index < len(self.command_history):
                self.command_entry.insert(0, self.command_history[self.history_index])
        return "break"  # イベントの伝播を停止

    def append_to_output(self, text):
        def _update():
            self.output_box.configure(state="normal")
            self.output_box.insert(ctk.END, text)
            self.output_box.configure(state="disabled")
            self.output_box.see(ctk.END)

        self.after(0, _update)

    def lighten_color(self, color):
        rgb_code = []
        default_color = color
        rgb_before = ImageColor.getcolor(default_color, "RGB")

        for rgb in rgb_before:
            new_rgb = min(rgb + 30, 255)
            rgb_code.append(new_rgb)

        return "#{:02x}{:02x}{:02x}".format(*rgb_code)

    def darken_color(self, color):
        rgb_code = []
        default_color = color
        rgb_before = ImageColor.getcolor(default_color, "RGB")

        for rgb in rgb_before:
            new_rgb = max(rgb - 30, 0)
            rgb_code.append(new_rgb)

        return "#{:02x}{:02x}{:02x}".format(*rgb_code)


if __name__ == "__main__":
    app = TerminalApp()
    app.mainloop()
