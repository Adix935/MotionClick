# main.py
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GLOG_minloglevel'] = '2'

import cv2
import math
import mediapipe as mp
import winsound
import threading
import time
from PIL import Image
import customtkinter as ctk

import pyautogui
from mouse_engine import MouseController
from gesture_logic import GestureProcessor
from debug import DebugMonitor
from overlay import JoystickOverlay

from voice_engine import VoiceTyper 

screen_w, screen_h = pyautogui.size()
mouse = MouseController(screen_w, screen_h)
logic = GestureProcessor()

voice = VoiceTyper(language="ro-RO")
voice.start_background()

mp_face_mesh = mp.solutions.face_mesh

current_state = {
    "nose_x": 0.0, "nose_y": 0.0, 
    "left_eye_ratio": 0.3, "right_eye_ratio": 0.3, "mouth_ratio": 0.1,
}

# JoyStick Settings
CENTER_X, CENTER_Y = 0.5, 0.5
DEADZONE = 0.04   
MAX_SPEED = 150
MIN_SPEED = 4.0

# Scrolling Multiplier
SCROLL_MULTIPLIER = 3

is_calibrated = False
calibration_frames = []
CALIBRATION_FRAME_COUNT = 45  

def euclidean_distance(p1, p2):
    return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2 + (p2.z - p1.z)**2)

NOSE_TIP = 1
EYE_TOP, EYE_BOTTOM = 159, 145
EYE_LEFT, EYE_RIGHT = 33, 133
RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM = 386, 374
RIGHT_EYE_LEFT, RIGHT_EYE_RIGHT = 362, 263
MOUTH_TOP, MOUTH_BOTTOM = 13, 14
MOUTH_LEFT, MOUTH_RIGHT = 78, 308

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

HELP = (
    "Tilt head — nose moves the cursor. Stays still in the joystick center.\n"
    "Left wink — left click. Right wink — right click.\n"
    "Double blink with both eyes — double click.\n"
    "Both eyes closed for over 3 seconds — sleep or wake up.\n"
    "Both eyes closed for 0.4s, until you hear a beep — grab. Open eyes and move with nose.\n"
    "Left wink drops the object.\n"
    "Open mouth and nose — scroll up, down, left, right.\n"
    "Puckered lips — joystick center moves to where the head is."
)

class App:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.stop_event = threading.Event()
        self.recal_event = threading.Event()
        self.lock = threading.Lock()
        
        self.latest_frame = None
        self.worker = None

        root.title("MotionClick - Produs Final")
        root.geometry("520x950")
        root.minsize(480, 850)

        # --- GUI Elements ---
        ctk.CTkLabel(root, text="MotionClick", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(16, 4))
        self.status = ctk.CTkLabel(root, text="Stopped", text_color="gray", font=ctk.CTkFont(size=16, weight="bold"))
        self.status.pack()
        self.detail = ctk.CTkLabel(root, text="Open the camera and keep your head still for calibration.", justify="left")
        self.detail.pack(pady=(4, 8))
        
        self.video = ctk.CTkLabel(root, text="Camera closed", width=440, height=330, fg_color="#141414")
        self.video.pack(padx=20, pady=(0, 10))

        # Sliders
        self.zone_label = ctk.CTkLabel(root, text=f"Neutral zone (Deadzone): {DEADZONE:.2f}")
        self.zone_label.pack(anchor="w", padx=24)
        self.zone_slider = ctk.CTkSlider(root, from_=0.02, to=0.15, number_of_steps=26, command=self._update_deadzone)
        self.zone_slider.set(DEADZONE)
        self.zone_slider.pack(fill="x", padx=24, pady=(0, 12))

        self.min_speed_label = ctk.CTkLabel(root, text=f"Minimum starting speed: {MIN_SPEED:.1f}")
        self.min_speed_label.pack(anchor="w", padx=24)
        self.min_speed_slider = ctk.CTkSlider(root, from_=1.0, to=20.0, number_of_steps=19, command=self._update_min_speed)
        self.min_speed_slider.set(MIN_SPEED)
        self.min_speed_slider.pack(fill="x", padx=24, pady=(0, 12))

        self.max_speed_label = ctk.CTkLabel(root, text=f"Maximum Speed: {MAX_SPEED:.0f}")
        self.max_speed_label.pack(anchor="w", padx=24)
        self.max_speed_slider = ctk.CTkSlider(root, from_=50.0, to=300.0, number_of_steps=50, command=self._update_max_speed)
        self.max_speed_slider.set(MAX_SPEED)
        self.max_speed_slider.pack(fill="x", padx=24, pady=(0, 12))

        self.start_btn = ctk.CTkButton(
            root, text="Start", height=44, fg_color="#2FA572", hover_color="#107C41",
            font=ctk.CTkFont(size=16, weight="bold"), command=self._toggle,
        )
        self.start_btn.pack(fill="x", padx=24, pady=(4, 6))
        
        ctk.CTkLabel(root, text=HELP, justify="left", wraplength=470, text_color="#bdbdbd").pack(padx=24, pady=(0, 12))

        # Keybinds
        root.bind_all("<space>", self._space_key)
        
        self._refresh()

    def _update_deadzone(self, value):
        global DEADZONE
        DEADZONE = round(float(value), 3)
        self.zone_label.configure(text=f"Neutral Zone (Deadzone): {DEADZONE:.2f}")

    def _update_min_speed(self, value):
        global MIN_SPEED
        MIN_SPEED = round(float(value), 1)
        self.min_speed_label.configure(text=f"Minimum Cursor Starting Speed: {MIN_SPEED:.1f}")

    def _update_max_speed(self, value):
        global MAX_SPEED
        MAX_SPEED = round(float(value), 0)
        self.max_speed_label.configure(text=f"Maximum Cursor speed: {MAX_SPEED:.0f}")

    def _toggle(self):
        if self.running:
            self.stop_event.set()
            return
        
        self.stop_event.clear()
        self.running = True
        self.start_btn.configure(text="Close", fg_color="#E81123", hover_color="#B50E1B")
        self.status.configure(text="Opening Camera...", text_color="#F5C542")
        self.worker = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker.start()

    def _recalibrate(self):
        self.recal_event.set()

    def _recal_key(self, _event):
        self._recalibrate()
        return "break"

    def _space_key(self, _event):
        if self.running:
            self.stop_event.set()
        return "break"

    def _close(self):
        self.stop_event.set()
        if self.worker is not None:
            self.worker.join(timeout=2.0)
        voice.stop()
        self.root.destroy()

    def _worker_loop(self):
        global CENTER_X, CENTER_Y, is_calibrated, calibration_frames, current_state
        global MIN_SPEED, MAX_SPEED
        
        # Initializing modules
        screen_w, screen_h = pyautogui.size()
        mouse = MouseController(screen_w, screen_h)
        logic = GestureProcessor() 
        debugger = DebugMonitor(print_interval=0.3)
        hud_overlay = JoystickOverlay(size=160, deadzone_ratio=DEADZONE, max_reach=0.15)
        
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        print("=== MotionClick ===")
        status_msg = "Opening Camera..."
        status_col = "#F5C542"
        status_timer = 0

        try:
            while cap.isOpened() and not self.stop_event.is_set():
                success, image = cap.read()
                if not success: 
                    break

                image = cv2.flip(image, 1)
                h, w, _ = image.shape
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb_image)

                if results.multi_face_landmarks:
                    comenzi = {}
                    for face_landmarks in results.multi_face_landmarks:

                        # Nose Coordinates
                        nose = face_landmarks.landmark[NOSE_TIP]
                        current_state["nose_x"] = nose.x
                        current_state["nose_y"] = nose.y

                        if not is_calibrated:
                            calibration_frames.append((nose.x, nose.y))
                            cv2.putText(image, f"Calibrating Neutral Position... {len(calibration_frames)}/{CALIBRATION_FRAME_COUNT}",
                                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                            if len(calibration_frames) >= CALIBRATION_FRAME_COUNT:
                                CENTER_X = sum(f[0] for f in calibration_frames) / len(calibration_frames)
                                CENTER_Y = sum(f[1] for f in calibration_frames) / len(calibration_frames)
                                is_calibrated = True
                                print(f">> Calibration Finished! New Center: ({CENTER_X:.3f}, {CENTER_Y:.3f}) <<")
                            
                        
                        # Ratios
                        l_eye_v = euclidean_distance(face_landmarks.landmark[EYE_TOP], face_landmarks.landmark[EYE_BOTTOM])
                        l_eye_h = euclidean_distance(face_landmarks.landmark[EYE_LEFT], face_landmarks.landmark[EYE_RIGHT])
                        if l_eye_h > 0: current_state["left_eye_ratio"] = l_eye_v / l_eye_h
                            
                        r_eye_v = euclidean_distance(face_landmarks.landmark[RIGHT_EYE_TOP], face_landmarks.landmark[RIGHT_EYE_BOTTOM])
                        r_eye_h = euclidean_distance(face_landmarks.landmark[RIGHT_EYE_LEFT], face_landmarks.landmark[RIGHT_EYE_RIGHT])
                        if r_eye_h > 0: current_state["right_eye_ratio"] = r_eye_v / r_eye_h
                            
                        mouth_v_dist = euclidean_distance(face_landmarks.landmark[MOUTH_TOP], face_landmarks.landmark[MOUTH_BOTTOM])
                        mouth_h_dist = euclidean_distance(face_landmarks.landmark[MOUTH_LEFT], face_landmarks.landmark[MOUTH_RIGHT])
                        if mouth_h_dist > 0: current_state["mouth_ratio"] = mouth_v_dist / mouth_h_dist

                        face_width = euclidean_distance(face_landmarks.landmark[33], face_landmarks.landmark[263])
                        
                        if face_width > 0:
                            mouth_width_ratio = mouth_h_dist / face_width
                            
                            # Pluckered lips
                            if mouth_width_ratio < 0.33:
                                CENTER_X = current_state["nose_x"]
                                CENTER_Y = current_state["nose_y"]

                        # JoyStick
                        dx = current_state["nose_x"] - CENTER_X
                        dy = current_state["nose_y"] - CENTER_Y

                        mouse_velocity_x = 0.0
                        mouse_velocity_y = 0.0

                        if abs(dx) > DEADZONE:
                            active_dx = dx - (DEADZONE if dx > 0 else -DEADZONE)
                            sign_x = 1 if dx > 0 else -1
                            mouse_velocity_x = sign_x * (abs(active_dx) * MAX_SPEED + MIN_SPEED)

                        if abs(dy) > DEADZONE:
                            active_dy = dy - (DEADZONE if dy > 0 else -DEADZONE)
                            sign_y = 1 if dy > 0 else -1
                            mouse_velocity_y = sign_y * (abs(active_dy) * MAX_SPEED + MIN_SPEED)

                        # INTEGRAREA ACTUATORULUI ȘI A LOGICII
                        if is_calibrated:
                            comenzi = logic.process(
                                current_state["left_eye_ratio"], 
                                current_state["right_eye_ratio"], 
                                current_state["mouth_ratio"], 
                                mouse_velocity_x, 
                                mouse_velocity_y
                            )
                            
                            if comenzi["move"] != (0.0, 0.0):
                                mouse.move_cursor(comenzi["move"][0], comenzi["move"][1])
                                
                            if comenzi["scroll"] != (0.0, 0.0):
                                mouse.scroll(
                                    comenzi["scroll"][1] * SCROLL_MULTIPLIER, 
                                    comenzi["scroll"][0] * SCROLL_MULTIPLIER 
                                )
                                
                            if comenzi["left_click"]: mouse.left_click()
                            if comenzi["right_click"]: mouse.right_click()
                            if comenzi["double_click"]: mouse.double_click()
                            if comenzi["toggle_drag"]: 
                                mouse.toggle_drag()
                                if logic.is_dragging:
                                    winsound.Beep(1500, 200) 
                                else:
                                    winsound.Beep(2500, 200) 

                            if comenzi["drag_ready_beep"]:
                                print(">>>>> BEEPING FOR DRAG CLICK! <<<<<")
                                threading.Thread(target=winsound.Beep, args=(1500, 100), daemon=True).start()
                            
                            if comenzi["toggle_sleep"]: 
                                mouse.toggle_sleep()
                                if logic.is_sleeping:
                                    def double_beep():
                                        winsound.Beep(1000, 150)
                                        time.sleep(0.05)
                                        winsound.Beep(1000, 150)
                                    threading.Thread(target=double_beep, daemon=True).start()
                                else:
                                    threading.Thread(target=winsound.Beep, args=(1500, 250), daemon=True).start()

                            # Kill-Switch on Space key
                            if mouse.check_failsafe():
                                print("! Failsafe !")
                                raise KeyboardInterrupt

                        center_px = (int(CENTER_X * w), int(CENTER_Y * h))
                        nose_px = (int(current_state["nose_x"] * w), int(current_state["nose_y"] * h))
                        deadzone_radius_px = int(DEADZONE * w)

                        cv2.circle(image, center_px, deadzone_radius_px, (255, 120, 0), 2)
                        cv2.circle(image, center_px, 3, (0, 0, 255), -1)

                        in_deadzone = (abs(dx) <= DEADZONE and abs(dy) <= DEADZONE)
                        nose_color = (0, 255, 0) if in_deadzone else (0, 0, 255)
                        cv2.circle(image, nose_px, 5, nose_color, -1)
                        hud_overlay.update(dx, dy, in_deadzone)
  
                        if not in_deadzone:
                            cv2.line(image, center_px, nose_px, (0, 165, 255), 2)

                        # HUD
                        if is_calibrated:
                            if logic.is_sleeping:
                                cv2.putText(image, "SLEEP MODE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                            elif logic.is_dragging:
                                cv2.putText(image, "DRAG MODE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                            else:
                                cv2.putText(image, "ACTIVE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                        debugger.draw_hud(image, current_state, mouse_velocity_x, mouse_velocity_y)
                        debugger.print_terminal(current_state, mouse_velocity_x, mouse_velocity_y)

                current_time = time.time()
                        
                if not is_calibrated:
                    status_msg = "Calibration..."
                    status_col = "#F5C542"
                elif is_calibrated and logic.is_sleeping:
                    status_msg = "SLEEP MODE"
                    status_col = "#F5C542"
                elif is_calibrated and logic.is_dragging:
                    status_msg = "DRAG MODE"
                    status_col = "#FFA500"
                elif 'mouth_width_ratio' in locals() and mouth_width_ratio < 0.33:
                    status_msg = "Pluckered lips (Centrare)"
                    status_col = "#D58BFF"
                elif is_calibrated and comenzi.get("scroll") != (0.0, 0.0):
                    status_msg = "Scroll..."
                    status_col = "#7EB6FF"
                else:
                    # Stări tranzitorii (rapide)
                    if is_calibrated:
                        if comenzi.get("double_click"):
                            status_msg = "Double Click!"
                            status_col = "#FFFFFF"
                            status_timer = current_time + 0.8
                        elif comenzi.get("left_click"):
                            status_msg = "Left Click"
                            status_col = "#FFFFFF"
                            status_timer = current_time + 0.8
                        elif comenzi.get("right_click"):
                            status_msg = "Right Click"
                            status_col = "#FFFFFF"
                            status_timer = current_time + 0.8
                    
                    if current_time > status_timer:
                        status_msg = "Active"
                        status_col = "#2FA572"
        
                if self.recal_event.is_set():
                    CENTER_X = current_state["nose_x"]
                    CENTER_Y = current_state["nose_y"]
                    print(f">> Manual Recalibration Completed: New Center ({CENTER_X:.3f}, {CENTER_Y:.3f}) <<")
                    self.recal_event.clear()

                rgb_render = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                with self.lock:
                    self.latest_frame = rgb_render
                    self.current_status_msg = status_msg
                    self.current_status_col = status_col

        except KeyboardInterrupt:
            print("\nProgram ended by used (Kill-Switch).")
        except Exception as e:
            print(f"\n[EROARE] Program Stopped: {e}")
            import traceback
            traceback.print_exc()
        finally:
            cap.release()
            hud_overlay.close()
            voice.stop()
            print("Camera stopped. Goodbye!")
            # Resseting GUI Buttons
            self.running = False

    def _refresh(self):
        # Updating UI with new data
        try:
            if self.running:
                with self.lock:
                    frame = getattr(self, "latest_frame", None)
                    # Getting message from atributes
                    s_msg = getattr(self, "current_status_msg", "Activ")
                    s_col = getattr(self, "current_status_col", "#2FA572")
                
                # Modifying GUI status
                self.status.configure(text=s_msg, text_color=s_col)
                
                if frame is not None:
                    pil_img = Image.fromarray(frame)
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(pil_img.width, pil_img.height))
                    self.video.configure(image=ctk_img, text="")
            else:
                self.status.configure(text="Oprit", text_color="gray")
                self.start_btn.configure(text="Pornește", fg_color="#2FA572", hover_color="#107C41")
        except Exception as e:
            pass

        if self.root.winfo_exists():
            self.root.after(33, self._refresh)

def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    
    root = ctk.CTk()
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()