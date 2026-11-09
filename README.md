# lazyremote

Turn an Xbox-style (XInput) gamepad into a couch remote for your Windows PC: mouse, scroll, media keys, and browser/window switching. One Python file, no dependencies.

## Requirements

- Windows 10/11
- [Python 3](https://www.python.org/downloads/) installed and available as `python`
- A controller that Windows sees as an Xbox 360/One/Series controller (XInput)

No `pip install` needed. The script only uses Python's standard library and Windows APIs.

## Run

Double-click `start-remote.bat`, or from a terminal:

```
python gamepad_remote.py
```

Press `Ctrl+C` in the window (or close it) to quit.

## Controls

| Button | Action |
|---|---|
| Left stick | Move mouse |
| LT (hold) | Slow, precise cursor |
| RT (hold) | Fast cursor |
| Right stick | Scroll (vertical and horizontal) |
| A | Left click (hold to drag) |
| B | Right click |
| X | Space (play/pause) |
| Y | `F` (fullscreen in most players) |
| LB / RB | Previous / next browser tab |
| D-pad left / right | Left / right arrow (seek) |
| D-pad up / down | Volume up / down |
| Start | Alt+Tab |
| Back | Task View (Win+Tab) |
| Left stick click | On-screen keyboard |
| Right stick click | Mute |

## Don't break your games

Hold **Start + Back** for one second to toggle the remote.

- One vibration: remote **on**
- Two vibrations: remote **off** (the script stops sending any input)

The remote starts **on** when the script launches, so turn it off or close it before gaming.

## Tweaking

Settings are at the top of `gamepad_remote.py`: dead zone, cursor speed, slow/fast multipliers, scroll speed, key-repeat timing, and whether the remote starts enabled. Button mappings are in the main loop.

## Notes

- Uses the first connected controller.
- Some games or apps running as administrator may ignore the simulated input unless the script is also run as administrator.
- Windows only.
