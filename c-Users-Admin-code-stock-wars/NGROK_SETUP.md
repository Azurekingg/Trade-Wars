# Ngrok Setup Guide

## What is Ngrok?
Ngrok creates a secure tunnel from the internet to your local Flask server, allowing others to connect to your game from anywhere.

## Quick Start

### 1. Install Ngrok
- Download from: https://ngrok.com/download
- Or use package manager:
  - Windows: `choco install ngrok`
  - Mac: `brew install ngrok`
  - Linux: Download and extract to PATH

### 2. Get Auth Token (Free Account)
1. Sign up at https://dashboard.ngrok.com/signup
2. Get your auth token from: https://dashboard.ngrok.com/get-started/your-authtoken
3. Run: `ngrok config add-authtoken YOUR_TOKEN`

### 3. Start Your App

**Option A: Manual Start**
1. Start Flask: `python app.py`
2. In another terminal: `ngrok http 5000`
3. Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)
4. Share this URL with players

**Option B: Use Script**
- Windows: Run `start_with_ngrok.bat`
- Mac/Linux: Run `chmod +x start_with_ngrok.sh && ./start_with_ngrok.sh`

### 4. Share the URL
- The ngrok URL will look like: `https://abc123.ngrok-free.app`
- Players can access your game using this URL
- **Note**: Free ngrok URLs change each time you restart (unless you have a paid plan)

## Important Notes

### Free Plan Limitations
- URLs change on each restart
- Session timeout after inactivity
- Limited bandwidth
- ngrok branding page (can be skipped)

### Paid Plan Benefits
- Static domain (same URL every time)
- No session timeouts
- More bandwidth
- Custom domains

### Security
- Your Flask app already handles HTTPS upgrade when behind ngrok
- The `upgrade_protocol()` function in `app.py` ensures HTTPS works correctly

## Troubleshooting

### Port Already in Use
If port 5000 is busy, use a different port:
```bash
# Start Flask on different port
python app.py --port 8080

# Then ngrok that port
ngrok http 8080
```

### Ngrok Not Found
Make sure ngrok is in your PATH or use full path:
```bash
# Windows
C:\path\to\ngrok.exe http 5000

# Mac/Linux
/path/to/ngrok http 5000
```

### Connection Refused
- Make sure Flask is running before starting ngrok
- Check that Flask is listening on the correct port (default: 5000)
- Verify firewall isn't blocking connections

## Alternative: Use ngrok Python Package

You can also use pyngrok to start ngrok programmatically:

```python
from pyngrok import ngrok

# Start ngrok tunnel
public_url = ngrok.connect(5000)
print(f"Public URL: {public_url}")
```

Then add `pyngrok` to requirements.txt and install it.









