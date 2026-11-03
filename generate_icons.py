import os
import math
from PIL import Image, ImageDraw

ICU_DIR = r"D:\Sandbox\SmartWardICU"
os.makedirs(ICU_DIR, exist_ok=True)

monitor_ico_path = os.path.join(ICU_DIR, "SmartWardMonitor.ico")
dispatcher_ico_path = os.path.join(ICU_DIR, "EmergencyDispatcher.ico")

def create_monitor_icon():
    # 256x256 high-res icon
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded rectangle (Dark Navy/Slate #0b0f19 with cyan border)
    margin = 12
    draw.rounded_rectangle([margin, margin, size[0] - margin, size[1] - margin], radius=44, fill=(11, 15, 25, 255), outline=(56, 189, 248, 255), width=6)

    # Inner subtle glow ring
    draw.rounded_rectangle([margin + 8, margin + 8, size[0] - margin - 8, size[1] - margin - 8], radius=38, outline=(16, 185, 129, 120), width=2)

    # Red medical heart in upper-middle
    cx, cy = 128, 105
    scale = 3.6
    coords = []
    for deg in range(0, 360, 5):
        rad = math.radians(deg)
        x = 16 * (math.sin(rad) ** 3)
        y = -(13 * math.cos(rad) - 5 * math.cos(2*rad) - 2 * math.cos(3*rad) - math.cos(4*rad))
        coords.append((cx + x * scale, cy + y * scale))
    draw.polygon(coords, fill=(239, 68, 68, 255), outline=(255, 255, 255, 220))

    # Cyan ECG Pulse Wave traversing the lower-middle
    ecg_y = 190
    wave_pts = [
        (30, ecg_y),
        (70, ecg_y),
        (85, ecg_y - 12),
        (95, ecg_y),
        (108, ecg_y),
        (114, ecg_y + 14),
        (128, ecg_y - 65),  # R peak
        (138, ecg_y + 26),  # S dip
        (148, ecg_y),
        (160, ecg_y),
        (175, ecg_y - 18),  # T wave
        (190, ecg_y),
        (226, ecg_y)
    ]
    # Draw thicker glow line
    draw.line(wave_pts, fill=(56, 189, 248, 140), width=9, joint="round")
    draw.line(wave_pts, fill=(255, 255, 255, 255), width=4, joint="round")

    # Save multiple resolutions in ICO
    img.save(monitor_ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Created: {monitor_ico_path}")

def create_dispatcher_icon():
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 12
    # Dark Crimson badge #1c0808 with glowing red outline #ef4444
    draw.rounded_rectangle([margin, margin, size[0] - margin, size[1] - margin], radius=44, fill=(28, 8, 8, 255), outline=(239, 68, 68, 255), width=6)
    draw.rounded_rectangle([margin + 8, margin + 8, size[0] - margin - 8, size[1] - margin - 8], radius=38, outline=(245, 158, 11, 140), width=2)

    # Location Beacon Pin (Top center)
    pin_cx, pin_cy = 128, 100
    pin_r = 42
    # Pin head
    draw.ellipse([pin_cx - pin_r, pin_cy - pin_r, pin_cx + pin_r, pin_cy + pin_r], fill=(239, 68, 68, 255), outline=(255, 255, 255, 255), width=4)
    # Inner center hole
    draw.ellipse([pin_cx - 16, pin_cy - 16, pin_cx + 16, pin_cy + 16], fill=(28, 8, 8, 255))
    # Pin needle triangle pointing down
    draw.polygon([(pin_cx - 26, pin_cy + 22), (pin_cx + 26, pin_cy + 22), (pin_cx, pin_cy + 75)], fill=(239, 68, 68, 255), outline=(255, 255, 255, 255))

    # Sound / Radio Dispatch Waves on sides (Arcs)
    draw.arc([pin_cx - 80, pin_cy - 50, pin_cx + 80, pin_cy + 50], start=140, end=220, fill=(56, 189, 248, 255), width=5)
    draw.arc([pin_cx - 100, pin_cy - 70, pin_cx + 100, pin_cy + 70], start=140, end=220, fill=(56, 189, 248, 180), width=4)
    draw.arc([pin_cx - 80, pin_cy - 50, pin_cx + 80, pin_cy + 50], start=320, end=40, fill=(56, 189, 248, 255), width=5)
    draw.arc([pin_cx - 100, pin_cy - 70, pin_cx + 100, pin_cy + 70], start=320, end=40, fill=(56, 189, 248, 180), width=4)

    # Emergency SOS Badge Bar at bottom
    draw.rounded_rectangle([44, 186, 212, 224], radius=10, fill=(220, 38, 38, 255), outline=(255, 255, 255, 220), width=2)
    
    # Save multiple resolutions in ICO
    img.save(dispatcher_ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Created: {dispatcher_ico_path}")

def create_launcher_icon():
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 12
    launcher_ico_path = os.path.join(ICU_DIR, "SmartWardLauncher.ico")
    # Deep warm obsidian/slate background with Claude Amber border
    draw.rounded_rectangle([margin, margin, size[0] - margin, size[1] - margin], radius=44, fill=(15, 23, 42, 255), outline=(217, 119, 6, 255), width=6)
    draw.rounded_rectangle([margin + 8, margin + 8, size[0] - margin - 8, size[1] - margin - 8], radius=38, outline=(245, 158, 11, 120), width=2)

    # Rocket / Command Launch Arrow Emblem in Claude Amber & Emerald
    draw.polygon([(128, 48), (84, 138), (172, 138)], fill=(245, 158, 11, 255), outline=(255, 255, 255, 255), width=2)
    draw.rounded_rectangle([104, 142, 152, 190], radius=8, fill=(16, 185, 129, 255), outline=(255, 255, 255, 255), width=2)
    draw.polygon([(84, 138), (56, 178), (84, 172)], fill=(217, 119, 6, 255))
    draw.polygon([(172, 138), (200, 178), (172, 172)], fill=(217, 119, 6, 255))
    draw.polygon([(116, 192), (140, 192), (128, 226)], fill=(239, 68, 68, 255))

    img.save(launcher_ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Created: {launcher_ico_path}")

if __name__ == "__main__":
    create_monitor_icon()
    create_dispatcher_icon()
    create_launcher_icon()
