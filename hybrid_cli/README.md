# Hybrid CLI Agent (Desktop + Mobile)

Two modes in one CLI:
- **Desktop**: screenshot via `mss`, planner = SEA-LION 32B (text), action = Qwen3-VL-8B (vision), executes with `pyautogui` + on-screen overlay.
- **Mobile**: screenshot via `adb`, planner = SEA-LION 32B (text), action = Qwen3-VL-8B (vision), executes with `adb input` taps/swipes/typing.

## Setup
```
pip install openai mss pillow pyautogui
# for mobile mode: install adb and have device authorized
```

## Run
Desktop (full screen):
```
python main.py "open calculator"
```
Desktop with region and dry run:
```
python main.py "click start" --region 0,0,1280,720 --dry-run
```
Mobile (default device):
```
python main.py "open settings" --target mobile
```
Mobile specific device:
```
python main.py "open chrome" --target mobile --device-id emulator-5554
```

## Notes
- Uses HF router; token from env `HF_TOKEN` or built-in fallback.
- Start button clicks on desktop are biased to bottom-left hotspot.
- Mobile coordinates from action model are normalized 0-1 and converted to pixels before adb input.
