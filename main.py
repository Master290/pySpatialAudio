import customtkinter as ctk
from tkinter import filedialog
import math
import numpy as np
from PIL import Image
from audio_engine import AudioEngine

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SpeakerControl(ctk.CTkFrame):
    def __init__(self, parent, channel_index, channel_name, engine, compact=False):
        width = 80 if compact else 120
        height = 100 if compact else 140
        font_size = 10 if compact else 12
        slider_width = 70 if compact else 100
        
        super().__init__(parent, width=width, height=height, corner_radius=8)
        self.engine = engine
        self.output_index = channel_index
        
        self.grid_propagate(False)
        
        self.lbl_name = ctk.CTkLabel(self, text=channel_name, font=("Arial", font_size, "bold"))
        self.lbl_name.place(relx=0.5, rely=0.15, anchor="center")
        
        self.source_var = ctk.StringVar(value="None")
        self.opt_source = ctk.CTkOptionMenu(self, variable=self.source_var, 
                                          values=["None"], 
                                          width=width-10,
                                          height=18 if compact else 20,
                                          font=("Arial", font_size-2),
                                          command=self.on_source_change)
        self.opt_source.place(relx=0.5, rely=0.35, anchor="center")
        
        self.slider = ctk.CTkSlider(self, from_=0, to=1.5, number_of_steps=20, 
                                  orientation="horizontal", 
                                  width=slider_width, 
                                  height=12,
                                  command=self.on_gain_change)
        self.slider.set(1.0)
        self.slider.place(relx=0.5, rely=0.55, anchor="center")
        self.slider.bind("<Button-3>", self.reset_gain)

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.place(relx=0.5, rely=0.75, anchor="center")
        
        btn_w = 25 if compact else 40
        btn_h = 15 if compact else 20
        
        self.btn_solo = ctk.CTkButton(self.btn_frame, text="S", width=btn_w, height=btn_h, 
                                    font=("Arial", font_size-2),
                                    fg_color="#444", hover_color="#888",
                                    command=self.toggle_solo)
        self.btn_solo.pack(side="left", padx=1)
        
        self.btn_mute = ctk.CTkButton(self.btn_frame, text="M", width=btn_w, height=btn_h, 
                                    font=("Arial", font_size-2),
                                    fg_color="#444", hover_color="#888",
                                    command=self.toggle_mute)
        self.btn_mute.pack(side="left", padx=1)

        self.level_bar = ctk.CTkProgressBar(self, width=slider_width, height=6)
        self.level_bar.set(0)
        self.level_bar.place(relx=0.5, rely=0.92, anchor="center")
        
    def reset_gain(self, event):
        self.slider.set(1.0)
        self.on_gain_change(1.0)

    def toggle_solo(self):
        current_bg = self.btn_solo.cget("fg_color")
        if current_bg == "#444":
            self.btn_solo.configure(fg_color="#d6a800") 
            self.engine.set_solo(self.output_index, True)
        else:
            self.btn_solo.configure(fg_color="#444")
            self.engine.set_solo(self.output_index, False)

    def toggle_mute(self):
        current_bg = self.btn_mute.cget("fg_color")
        if current_bg == "#444":
            self.btn_mute.configure(fg_color="#b30000") 
            self.engine.set_mute(self.output_index, True)
        else:
            self.btn_mute.configure(fg_color="#444")
            self.engine.set_mute(self.output_index, False)


    def update_sources(self, input_channels):
        values = ["None"]
        for i in range(input_channels):
            values.append(f"In {i+1}")
        
        self.opt_source.configure(values=values)
        
        if self.output_index < input_channels:
            self.opt_source.set(f"In {self.output_index + 1}")
            self.on_source_change(f"In {self.output_index + 1}")
        else:
            self.opt_source.set("None")
            self.on_source_change("None")

    def on_source_change(self, choice):
        target_in_idx = -1
        if choice.startswith("In "):
            target_in_idx = int(choice.split(" ")[1]) - 1
            
        if self.engine.input_channels > 0:
            for i in range(self.engine.input_channels):
                self.engine.set_channel_gain(i, self.output_index, 0.0)
        
        if target_in_idx >= 0:
            gain = self.slider.get()
            self.engine.set_channel_gain(target_in_idx, self.output_index, gain)

    def on_gain_change(self, value):
        self.on_source_change(self.source_var.get())
        
    def update_level(self):
        try:
            val = self.engine.current_levels[self.output_index]
            visual_val = math.pow(val, 0.4) * 1.2 
            if visual_val > 1.0: visual_val = 1.0
            self.level_bar.set(visual_val)
        except:
            pass

class PlayerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.engine = AudioEngine()
        
        self.title("pySpatialAudio")
        self.geometry("900x700")
        
        self.create_widgets()
        self.update_ui_loop()

    def create_widgets(self):
        self.top_bar = ctk.CTkFrame(self, height=60)
        self.top_bar.pack(fill="x", padx=10, pady=10)
        
        self.btn_open = ctk.CTkButton(self.top_bar, text="Open File", width=100, command=self.open_file)
        self.btn_open.pack(side="left", padx=10, pady=10)
        
        self.lbl_file = ctk.CTkLabel(self.top_bar, text="No File Loaded")
        self.lbl_file.pack(side="left", padx=10)
        
        self.vol_slider = ctk.CTkSlider(self.top_bar, from_=0, to=1, width=150, command=self.set_volume)
        self.vol_slider.set(1.0)
        self.vol_slider.pack(side="right", padx=20)
        ctk.CTkLabel(self.top_bar, text="Master Vol").pack(side="right")
        
        self.main_area = ctk.CTkFrame(self)
        self.main_area.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.viz_canvas = ctk.CTkCanvas(self.main_area, bg="#212121", highlightthickness=0)
        self.viz_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        self.view_scale = 1.0
        self.view_pan_x = 0.0
        self.view_pan_y = 0.0
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        self.viz_canvas.bind("<MouseWheel>", self.on_zoom)
        self.viz_canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.viz_canvas.bind("<B1-Motion>", self.on_drag_move)
        self.viz_canvas.bind("<Button-4>", lambda e: self.on_zoom(e, 120))
        self.viz_canvas.bind("<Button-5>", lambda e: self.on_zoom(e, -120))

        try:
            pil_image = Image.open("listener.png")
            self.icon_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(64, 64))
            self.lbl_listener = ctk.CTkLabel(self.main_area, text="", image=self.icon_image)
            self.lbl_listener.place(relx=0.5, rely=0.5, anchor="center")
        except Exception as e:
            print(f"Could not load icon: {e}")
            self.lbl_listener = ctk.CTkLabel(self.main_area, text="👤\nListener", font=("Arial", 20))
            self.lbl_listener.place(relx=0.5, rely=0.5, anchor="center")
        
        self.lbl_listener.lift()

        self.bottom_bar = ctk.CTkFrame(self, height=80)
        self.bottom_bar.pack(fill="x", padx=10, pady=10)
        
        self.btn_play = ctk.CTkButton(self.bottom_bar, text="PLAY", font=("Arial", 16, "bold"), 
                                    width=120, height=40, command=self.toggle_play)
        self.btn_play.pack(side="bottom", pady=10)
        
        self.progress = ctk.CTkSlider(self.bottom_bar, from_=0, to=1, command=self.seek)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=20, pady=5)
        
        self.speakers = []
        self.speaker_base_coords = [] 
        self.init_speakers()

    def on_zoom(self, event, delta=None):
        d = delta if delta else event.delta
        if d > 0:
            self.view_scale *= 1.1
        else:
            self.view_scale /= 1.1
        
        self.view_scale = max(0.5, min(self.view_scale, 3.0))
        self.refresh_layout()

    def on_drag_start(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag_move(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        w = self.main_area.winfo_width()
        h = self.main_area.winfo_height()
        if w > 0 and h > 0:
            self.view_pan_x += dx / w
            self.view_pan_y += dy / h
            
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.refresh_layout()

    def refresh_layout(self):
        lx = 0.5 + self.view_pan_x
        ly = 0.5 + self.view_pan_y
        self.lbl_listener.place(relx=lx, rely=ly, anchor="center")
        
        for i, spk in enumerate(self.speakers):
            bx, by = self.speaker_base_coords[i]
            
            nx = 0.5 + (bx - 0.5) * self.view_scale + self.view_pan_x
            ny = 0.5 + (by - 0.5) * self.view_scale + self.view_pan_y
            
            spk.place(relx=nx, rely=ny, anchor="center")
            
        if self.engine.is_playing:
             self.draw_visualization()

    def init_speakers(self, speaker_count=None):
        for s in self.speakers:
            s.destroy()
        self.speakers = []
        self.speaker_base_coords = []

        layout_map = {
            0: ("FL", 0.3, 0.2),  
            1: ("FR", 0.7, 0.2),  
            2: ("C",  0.5, 0.15), 
            3: ("LFE",0.5, 0.85),
            4: ("SL", 0.15, 0.5),
            5: ("SR", 0.85, 0.5),  
            6: ("RL", 0.25, 0.8),
            7: ("RR", 0.75, 0.8) 
        }
        
        if speaker_count is None:
            count = self.engine.virtual_channels
        else:
            count = speaker_count
            
        if count > 24: count = 24 
        
        use_compact = (count > 12)
        
        for i in range(count):
            name = f"Out {i+1}"
            pos_x, pos_y = 0.5, 0.5
            
            if i < 8 and i in layout_map:
                name, pos_x, pos_y = layout_map[i]
            else:
                if i < 16:
                    ring_idx = i - 8
                    total_in_ring = 8
                    radius = 0.35 
                    angle = (2 * math.pi * ring_idx) / total_in_ring - math.pi/2
                else:
                    ring_idx = i - 16
                    total_in_ring = 8
                    radius = 0.18
                    angle = (2 * math.pi * ring_idx) / total_in_ring - math.pi/2

                pos_x = 0.5 + radius * 1.4 * math.cos(angle) 
                pos_y = 0.5 + radius * 1.2 * math.sin(angle)
            
            spk = SpeakerControl(self.main_area, i, name, self.engine, compact=use_compact)
            spk.place(relx=pos_x, rely=pos_y, anchor="center")
            self.speakers.append(spk)
            self.speaker_base_coords.append((pos_x, pos_y))
            
        self.refresh_layout()


    def draw_visualization(self):
        w = self.main_area.winfo_width()
        h = self.main_area.winfo_height()
        cx, cy = w/2, h/2
        
        self.viz_canvas.delete("all")
        
        cx = (0.5 + self.view_pan_x) * w
        cy = (0.5 + self.view_pan_y) * h
        
        for i, base_coord in enumerate(self.speaker_base_coords):
            try:
                bx, by = base_coord
                rel_sx = 0.5 + (bx - 0.5) * self.view_scale + self.view_pan_x
                rel_sy = 0.5 + (by - 0.5) * self.view_scale + self.view_pan_y
                
                sx = rel_sx * w
                sy = rel_sy * h

                raw_level = self.engine.current_levels[i]
                
                level = math.pow(raw_level, 0.4) * 1.5
                
                if level > 0.05:
                    
                    beam_width = 40 * level 
                    
                    dx, dy = sx - cx, sy - cy
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist == 0: continue
                    
                    nx, ny = -dy/dist, dx/dist
                    
                    p1 = (cx, cy)
                    p2 = (sx + nx*beam_width, sy + ny*beam_width)
                    p3 = (sx - nx*beam_width, sy - ny*beam_width)
                    
                    val = int(min(level * 255, 255))
                    r = int(val * 0.2)
                    g = int(val * 0.8)
                    b = 255
                    
                    hex_col = f"#{r:02x}{g:02x}{b:02x}"
                    
                    self.viz_canvas.create_polygon(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], 
                                                 fill=hex_col, outline="")
            except:
                pass


    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.flac *.mp3 *.ogg *.m4a *.eac3 *.ac3")])
        if path:
            success, msg = self.engine.load_file(path)
            if success:
                self.lbl_file.configure(text=f"{path.split('/')[-1]}")
                self.init_speakers(self.engine.input_channels)
                for spk in self.speakers:
                    spk.update_sources(self.engine.input_channels)
            else:
                self.show_error("Load Error", f"Could not load file:\n{msg}")

    def show_error(self, title, message):
        window = ctk.CTkToplevel(self)
        window.title(title)
        window.geometry("500x300")
        
        lbl = ctk.CTkLabel(window, text=title, font=("Arial", 16, "bold"), text_color="red")
        lbl.pack(pady=10)
        
        textbox = ctk.CTkTextbox(window, width=450, height=200)
        textbox.pack(padx=10, pady=5)
        textbox.insert("0.0", message)
        textbox.configure(state="disabled")

    def toggle_play(self):
        if self.engine.is_playing:
            self.engine.pause()
            self.btn_play.configure(text="PLAY")
        else:
            self.engine.play()
            self.btn_play.configure(text="PAUSE")

    def seek(self, value):
        self.engine.seek(float(value))

    def set_volume(self, value):
        self.engine.volume = float(value)

    def update_ui_loop(self):
        if self.engine.is_playing and self.engine.data is not None:
            pos = self.engine.current_frame / len(self.engine.data)
            self.progress.set(pos)
            
        if self.engine.is_playing:
             self.draw_visualization()
             
        for spk in self.speakers:
            spk.update_level()
            
        self.after(16, self.update_ui_loop)

if __name__ == "__main__":
    app = PlayerApp()
    app.mainloop()
