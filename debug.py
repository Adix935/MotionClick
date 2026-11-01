import cv2
import time

class DebugMonitor:
    def __init__(self, print_interval=0.2):
        self.last_print_time = 0
        self.print_interval = print_interval

    def draw_hud(self, image, state, vx, vy):
        y_offset = 80
        color = (255, 255, 255) # Alb
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.5
        thickness = 1

        cv2.putText(image, "--- STATS ---", (20, y_offset), font, scale, (0, 255, 255), thickness)
        cv2.putText(image, f"Nose X, Y: {state['nose_x']:.3f}, {state['nose_y']:.3f}", (20, y_offset + 20), font, scale, color, thickness)
        cv2.putText(image, f"Vx, Vy:   {vx:.1f}, {vy:.1f}", (20, y_offset + 40), font, scale, color, thickness)
        cv2.putText(image, f"Left Eye: {state['left_eye_ratio']:.3f}", (20, y_offset + 60), font, scale, color, thickness)
        cv2.putText(image, f"Right Eye: {state['right_eye_ratio']:.3f}", (20, y_offset + 80), font, scale, color, thickness)
        cv2.putText(image, f"Mouth:     {state['mouth_ratio']:.3f}", (20, y_offset + 100), font, scale, color, thickness)
        
        return image

    def print_terminal(self, state, vx, vy):
        """Showing logs at fixed intervals."""
        current_time = time.time()
        if current_time - self.last_print_time > self.print_interval:
            print(f"[DEBUG] Nose:({state['nose_x']:.2f}, {state['nose_y']:.2f}) | "
                  f"Speed:({vx:5.1f}, {vy:5.1f}) | "
                  f"Eye:(Left:{state['left_eye_ratio']:.2f}, Right:{state['right_eye_ratio']:.2f}) | "
                  f"Mouth:{state['mouth_ratio']:.2f}")
            self.last_print_time = current_time