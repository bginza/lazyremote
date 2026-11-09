"""Gamepad -> PC remote (mouse, scroll, media keys, browser tabs). Windows only, no deps.

Toggle ON/OFF: tahan Start + Back selama ~1 detik (controller getar sebagai tanda).
  - 1 getar pendek  = remote AKTIF
  - 2 getar         = remote MATI (aman buat gaming)
"""
import ctypes
import sys
import time
from ctypes import wintypes

# ---------------------------------------------------------------- config
DEADZONE = 0.18
CURSOR_SPEED = 1500.0      # px/detik pada stick penuh
SLOW_FACTOR = 0.22         # tahan LT = kursor pelan/presisi
FAST_FACTOR = 2.2          # tahan RT = kursor ngebut
SCROLL_SPEED = 14.0        # tick wheel/detik pada stick penuh
REPEAT_DELAY = 0.40
REPEAT_RATE = 0.09
TOGGLE_HOLD = 1.0
START_ENABLED = True
# ----------------------------------------------------------------------

xinput = None
for name in ("xinput1_4", "xinput1_3", "xinput9_1_0"):
    try:
        xinput = ctypes.windll.LoadLibrary(name)
        break
    except OSError:
        pass
if xinput is None:
    sys.exit("XInput tidak ditemukan.")


class GAMEPAD(ctypes.Structure):
    _fields_ = [("wButtons", wintypes.WORD), ("bLeftTrigger", ctypes.c_ubyte),
                ("bRightTrigger", ctypes.c_ubyte), ("sThumbLX", ctypes.c_short),
                ("sThumbLY", ctypes.c_short), ("sThumbRX", ctypes.c_short),
                ("sThumbRY", ctypes.c_short)]


class XSTATE(ctypes.Structure):
    _fields_ = [("dwPacketNumber", wintypes.DWORD), ("Gamepad", GAMEPAD)]


class XVIB(ctypes.Structure):
    _fields_ = [("wLeftMotorSpeed", wintypes.WORD), ("wRightMotorSpeed", wintypes.WORD)]


# --- SendInput
ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _U(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


user32 = ctypes.windll.user32
user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)

M_MOVE, M_LDOWN, M_LUP, M_RDOWN, M_RUP = 0x0001, 0x0002, 0x0004, 0x0008, 0x0010
M_WHEEL, M_HWHEEL = 0x0800, 0x1000
K_EXT, K_UP = 0x0001, 0x0002

VK = dict(
    TAB=0x09, ENTER=0x0D, SHIFT=0x10, CTRL=0x11, ALT=0x12, ESC=0x1B, SPACE=0x20,
    LEFT=0x25, UP=0x26, RIGHT=0x27, DOWN=0x28, WIN=0x5B, F=0x46, O=0x4F, W=0x57, T=0x54,
    MUTE=0xAD, VOLDOWN=0xAE, VOLUP=0xAF, NEXT=0xB0, PREV=0xB1, PLAY=0xB3,
)
EXTENDED = {VK["LEFT"], VK["UP"], VK["RIGHT"], VK["DOWN"], VK["WIN"]}


def _send(inp):
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def mouse(flags, dx=0, dy=0, data=0):
    i = INPUT(type=0)
    i.u.mi = MOUSEINPUT(dx, dy, data & 0xFFFFFFFF, flags, 0, 0)
    _send(i)


def key(vk, up=False):
    i = INPUT(type=1)
    flags = (K_EXT if vk in EXTENDED else 0) | (K_UP if up else 0)
    i.u.ki = KEYBDINPUT(vk, 0, flags, 0, 0)
    _send(i)


def combo(*names):
    vks = [VK[n] for n in names]
    for v in vks:
        key(v)
    for v in reversed(vks):
        key(v, up=True)


def tap(name):
    combo(name)


# --- Buttons
B = dict(UP=0x0001, DOWN=0x0002, LEFT=0x0004, RIGHT=0x0008, START=0x0010, BACK=0x0020,
         L3=0x0040, R3=0x0080, LB=0x0100, RB=0x0200, A=0x1000, B=0x2000, X=0x4000, Y=0x8000)


def vibrate(pad, ms=120, strength=40000):
    xinput.XInputSetState(pad, ctypes.byref(XVIB(strength, strength)))
    time.sleep(ms / 1000)
    xinput.XInputSetState(pad, ctypes.byref(XVIB(0, 0)))


def norm_stick(x, y):
    fx, fy = x / 32768.0, y / 32768.0
    mag = (fx * fx + fy * fy) ** 0.5
    if mag < DEADZONE:
        return 0.0, 0.0
    scale = min(1.0, (mag - DEADZONE) / (1.0 - DEADZONE)) / mag
    return fx * scale, fy * scale


def find_pad():
    st = XSTATE()
    for i in range(4):
        if xinput.XInputGetState(i, ctypes.byref(st)) == 0:
            return i
    return None


def main(test=False):
    enabled = START_ENABLED
    pad = None
    prev = 0
    last = time.perf_counter()
    acc_x = acc_y = acc_sv = acc_sh = 0.0
    toggle_t0 = None
    toggle_done = False
    combo_used = False
    repeat = {}   # button -> next fire time
    st = XSTATE()
    print("Gamepad remote jalan. Toggle: tahan Start+Back 1 detik. Ctrl+C untuk keluar.")

    while True:
        time.sleep(0.008)
        now = time.perf_counter()
        dt, last = now - last, now

        if pad is None or xinput.XInputGetState(pad, ctypes.byref(st)) != 0:
            pad = find_pad()
            if pad is None:
                time.sleep(1.0)
                continue
            print(f"Controller terhubung (slot {pad}).")
            xinput.XInputGetState(pad, ctypes.byref(st))
            prev = st.Gamepad.wButtons
        g = st.Gamepad
        btn = g.wButtons
        pressed = btn & ~prev
        released = prev & ~btn

        # ---- toggle (Start + Back ditahan)
        both = B["START"] | B["BACK"]
        if (btn & both) == both:
            combo_used = True
            if toggle_t0 is None:
                toggle_t0 = now
            elif not toggle_done and now - toggle_t0 >= TOGGLE_HOLD:
                enabled = not enabled
                toggle_done = True
                print("Remote", "AKTIF" if enabled else "MATI")
                vibrate(pad, 150)
                if not enabled:
                    time.sleep(0.12)
                    vibrate(pad, 150)
        else:
            toggle_t0 = None
            toggle_done = False
            if not (btn & both):
                combo_used = False

        if test:
            print(f"btn={btn:#06x} LX={g.sThumbLX} LY={g.sThumbLY} RX={g.sThumbRX} RY={g.sThumbRY} "
                  f"LT={g.bLeftTrigger} RT={g.bRightTrigger}", end="\r")

        if not enabled:
            prev = btn
            acc_x = acc_y = acc_sv = acc_sh = 0.0
            continue

        # ---- kursor (stick kiri)
        lx, ly = norm_stick(g.sThumbLX, g.sThumbLY)
        speed = CURSOR_SPEED
        if g.bLeftTrigger > 60:
            speed *= SLOW_FACTOR
        if g.bRightTrigger > 60:
            speed *= FAST_FACTOR
        # kurva kuadrat: halus di tengah, cepat di ujung
        acc_x += lx * abs(lx) * speed * dt
        acc_y += -ly * abs(ly) * speed * dt
        mx, my = int(acc_x), int(acc_y)
        if mx or my:
            acc_x -= mx
            acc_y -= my
            mouse(M_MOVE, mx, my)

        # ---- scroll (stick kanan)
        rx, ry = norm_stick(g.sThumbRX, g.sThumbRY)
        acc_sv += ry * abs(ry) * SCROLL_SPEED * dt
        acc_sh += rx * abs(rx) * SCROLL_SPEED * dt
        sv, sh = int(acc_sv), int(acc_sh)
        if sv:
            acc_sv -= sv
            mouse(M_WHEEL, data=sv * 120)
        if sh:
            acc_sh -= sh
            mouse(M_HWHEEL, data=sh * 120)

        # ---- klik
        if pressed & B["A"]:
            mouse(M_LDOWN)
        if released & B["A"]:
            mouse(M_LUP)
        if pressed & B["B"]:
            mouse(M_RDOWN)
        if released & B["B"]:
            mouse(M_RUP)

        # ---- tombol sekali tekan
        if pressed & B["X"]:
            tap("SPACE")               # play/pause (YouTube, Netflix, dll)
        if pressed & B["Y"]:
            tap("F")                   # fullscreen player
        if pressed & B["LB"]:
            combo("CTRL", "SHIFT", "TAB")   # tab sebelumnya
        if pressed & B["RB"]:
            combo("CTRL", "TAB")            # tab berikutnya
        if pressed & B["L3"]:
            combo("WIN", "CTRL", "O")       # on-screen keyboard
        if pressed & B["R3"]:
            tap("MUTE")
        if released & B["START"] and not combo_used:
            combo("ALT", "TAB")             # ganti window
        if released & B["BACK"] and not combo_used:
            combo("WIN", "TAB")             # Task View: lihat semua window

        # ---- D-pad (dengan auto-repeat)
        dmap = {B["LEFT"]: "LEFT", B["RIGHT"]: "RIGHT", B["UP"]: "VOLUP", B["DOWN"]: "VOLDOWN"}
        for mask, name in dmap.items():
            if pressed & mask:
                tap(name)
                repeat[mask] = now + REPEAT_DELAY
            elif btn & mask and now >= repeat.get(mask, 1e18):
                tap(name)
                repeat[mask] = now + REPEAT_RATE
            elif not btn & mask:
                repeat.pop(mask, None)

        prev = btn


if __name__ == "__main__":
    try:
        main(test="--test" in sys.argv)
    except KeyboardInterrupt:
        mouse(M_LUP)
        mouse(M_RUP)
        print("\nBerhenti.")
