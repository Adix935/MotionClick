# MotionClick

**Software-based Edge AI accessibility system for individuals with spinal cord injuries.**

*This project was developed during a 2026 Hackathon organized by the RDCC (Romanian Diversity Chamber of Commerce).*

MotionClick is an alternative OS control interface that transforms a standard webcam into a tool for digital independence. The project enables full mouse and keyboard control using exclusively facial gestures and voice commands, eliminating the need for expensive eye-tracking hardware.

---

## Technical Architecture & Performance

We developed this project with a strong focus on efficiency and data privacy, entirely avoiding the use of Generative AI models. 

*   **Applied AI (Computer Vision):** Utilizes the predictive machine learning model **Google MediaPipe Face Mesh** to extract and track **468 3D facial landmarks** with mathematical precision in real-time. Processing is 100% local, so biometric data privacy is guaranteed.
*   **Multi-Threading Architecture:** The application handles 3 parallel execution threads (Main GUI Thread, Video Worker Thread, Background Voice Thread). This separation ensures smooth camera and interface rendering at **~30 FPS**, preventing voice recognition or audio feedback loops from blocking the visual processing pipeline.
*   **Stability & UX:** The system integrates a mathematically calculated neutral tolerance area (*Deadzone*). This acts as a dampener to absorb natural head jitter and muscle spasms, allowing the user to perfectly stabilize the cursor and rest without losing control of the screen.
*   **Speech-to-Text:** Integrated with **Google Speech Recognition** for keyboard automation, text dictation, and OS-level shortcuts (OS Automation via PyAutoGUI).

---

## Control Scheme (Gestures & Actions)

The system continuously reads facial expressions and instantly translates them into physical OS commands.

| Gesture / Input | On-Screen Result (OS Action) |
| :--- | :--- |
| **Head Movement (Up/Down/Left/Right)** | Moves the mouse cursor. |
| **Head in Screen Center** | Cursor remains stationary (inside the Deadzone). |
| **Short Blink - Left Eye** | Left Click. |
| **Short Blink - Right Eye** | Right Click. |
| **Eyes Closed for 0.4s (Until Beep)** | Activates **Drag & Drop** (holds the item). |
| **Mouth Open + Head Movement** | Scroll (Up/Down/Left/Right). Cursor movement freezes. |
| **Puckered Lips (in 'O' shape)** | Instantly recalibrates the face center (Joystick Reset). |
| **Eyes Closed > 3 seconds** | **Sleep Mode** (Application Pause / Wake-up). |
| **Voice Commands ("Type...", "Delete")** | Automated typing and shortcut execution. |
| **SPACE Key** | **Kill-Switch** (Emergency actuator override/stop). |

*(Note: Movement sensitivity, minimum/maximum cursor speed, and the Deadzone radius can be adjusted in real-time via the CustomTkinter graphical interface).*

---

## Installation & Setup

### Prerequisites
* **Python 3.11** (Required for compatibility)
* A functional webcam and microphone.

### Installation Steps

**1. Clone the repository**
```bash
git clone https://github.com/Adix935/MotionClick.git
cd MotionClick
```

**2. Create a virtual environment**

# Windows:
```bash
py -3.11 -m venv myvenv
source myvenv/Scripts/activate
```

**3. Install dependencies**
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**4. Running the app**
```bash
python main.py
```

# Thanks for reading!