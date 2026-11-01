import ctypes
import pyautogui
import keyboard

pyautogui.FAILSAFE = False

class MouseController:
    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.curr_x = float(screen_w // 2)
        self.curr_y = float(screen_h // 2)
        
        # Flags for if the mouse is pressed
        self.is_dragging = False
        self.is_sleeping = False

    def move_cursor(self, vel_x, vel_y):
        self.curr_x += vel_x
        self.curr_y += vel_y
        
        # Making sure the mouse doesn't go out of the screen window
        self.curr_x = max(0.0, min(self.curr_x, float(self.screen_w - 1)))
        self.curr_y = max(0.0, min(self.curr_y, float(self.screen_h - 1)))
        
        ctypes.windll.user32.SetCursorPos(int(self.curr_x), int(self.curr_y))

    def scroll(self, direction_y, direction_x=0):
        if abs(direction_y) > 0:
            pyautogui.scroll(int(direction_y))
        if abs(direction_x) > 0:
            pyautogui.hscroll(int(direction_x))

    def left_click(self):
        pyautogui.click()
        print("[ACTUATOR] Left Click")

    def right_click(self):
        pyautogui.click(button='right')
        print("[ACTUATOR] Right Click")

    def double_click(self):
        pyautogui.doubleClick()
        print("[ACTUATOR] Double Click")

    def toggle_drag(self):
        self.is_dragging = not self.is_dragging
        if self.is_dragging:
            pyautogui.mouseDown()
            print("[ACTUATOR] Drag click STARTED (mouse kept pressed)")
        else:
            pyautogui.mouseUp()
            print("[ACTUATOR] Drop Executed (freed mouse)")

    def toggle_sleep(self):
        self.is_sleeping = not self.is_sleeping
        if self.is_sleeping:
            print("[ACTUATOR] SLEEP MODE ACTIVATED- The mouse is in pause")
        else:
            print("[ACTUATOR] SLEEP MODE DEACTIVATED - Mouse is activ")

    def check_failsafe(self):
        try:
            if keyboard.is_pressed('space'):
                if self.is_dragging:
                    pyautogui.mouseUp()
                    self.is_dragging = False
                print("\n[KILL-SWITCH] Space was pressed")
                return True
        except Exception:
            pass
        return False
