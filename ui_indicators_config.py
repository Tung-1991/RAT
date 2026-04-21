# -*- coding: utf-8 -*-
# FILE: ui_indicators_config.py
# V3.0: DYNAMIC INDICATOR CONFIG BUILDER (KAISER EDITION)

import customtkinter as ctk
from tkinter import messagebox

def open_indicator_config_popup(parent, ind_name, current_params, save_callback):
    """
    Hàm tạo Popup động cho bất kỳ Indicator nào.
    - parent: Window gọi popup (ui_bot_strategy)
    - ind_name: Tên indicator (vd: rsi, macd)
    - current_params: Dict chứa params hiện tại (vd: {"period": 14, "upper": 70})
    - save_callback: Hàm thực thi khi nhấn Lưu (nhận vào dict params mới)
    """
    top = ctk.CTkToplevel(parent)
    top.title(f"⚙️ Cấu hình thông số: {ind_name.upper()}")
    top.geometry("450x550")
    top.attributes("-topmost", True)
    top.focus_force()

    # Header
    ctk.CTkLabel(top, text=f"THÔNG SỐ KỸ THUẬT: {ind_name.upper()}", font=("Roboto", 15, "bold"), text_color="#E040FB").pack(pady=(20, 10))

    # Nếu không có params nào
    if not current_params:
        ctk.CTkLabel(top, text="Chỉ báo này không có thông số tùy chỉnh.", font=("Roboto", 13, "italic"), text_color="gray").pack(pady=30)
        ctk.CTkButton(top, text="ĐÓNG", fg_color="#424242", command=top.destroy).pack(pady=20)
        return

    # Frame cuộn chứa các ô nhập liệu
    scroll_frame = ctk.CTkScrollableFrame(top, fg_color="#2b2b2b", corner_radius=8)
    scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    scroll_frame.columnconfigure(0, weight=1)
    scroll_frame.columnconfigure(1, weight=1)

    entries = {}
    row = 0
    for key, value in current_params.items():
        # Label tên thông số
        lbl = ctk.CTkLabel(scroll_frame, text=key.upper(), font=("Roboto", 12, "bold"))
        lbl.grid(row=row, column=0, padx=15, pady=12, sticky="w")
        
        # Ô nhập liệu
        ent = ctk.CTkEntry(scroll_frame, width=120, justify="center", font=("Consolas", 13))
        ent.insert(0, str(value))
        ent.grid(row=row, column=1, padx=15, pady=12, sticky="e")
        
        entries[key] = {"widget": ent, "original_type": type(value)}
        
        # Dòng kẻ ngang phân cách
        ctk.CTkFrame(scroll_frame, height=1, fg_color="#444").grid(row=row+1, column=0, columnspan=2, sticky="ew", padx=10)
        row += 2

    # Hàm xử lý lưu
    def on_save():
        new_params = {}
        try:
            for k, data in entries.items():
                val_str = data["widget"].get()
                orig_type = data["original_type"]
                
                # Ép kiểu dữ liệu tự động theo kiểu gốc để không bị lỗi Type Error lúc tính toán
                if orig_type == bool:
                    new_params[k] = val_str.lower() in ['true', '1', 't', 'y', 'yes']
                elif orig_type == float:
                    new_params[k] = float(val_str)
                elif orig_type == int:
                    new_params[k] = int(val_str)
                else:
                    new_params[k] = val_str # Default fallback là string
            
            # Trả dữ liệu về hàm callback
            save_callback(new_params)
            top.destroy()
            
        except ValueError:
            messagebox.showerror("Lỗi dữ liệu", "Vui lòng nhập đúng định dạng số (Int/Float) cho các trường yêu cầu!", parent=top)

    # Khung nút bấm
    btn_frame = ctk.CTkFrame(top, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=20)
    
    ctk.CTkButton(btn_frame, text="HỦY", fg_color="#D50000", hover_color="#B71C1C", width=120, height=40, font=("Roboto", 13, "bold"), command=top.destroy).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="LƯU THÔNG SỐ", fg_color="#00C853", hover_color="#009624", height=40, font=("Roboto", 13, "bold"), command=on_save).pack(side="right", padx=10, fill="x", expand=True)