# Quick Reference: Adding Videos & VFX

## 📁 File Locations

- **Videos**: `static/videos/`
- **VFX Configs**: `static/vfx/`
- **Thumbnails**: `static/images/video_thumbnails/`
- **Config File**: `trading_buddy_videos.json`

## 🎬 Adding a Video (3 Steps)

### Step 1: Add Video File
Place your video in `static/videos/`
- Format: MP4 (recommended), WebM, or OGG
- Size: Max 100MB
- Resolution: 1920x1080 recommended

### Step 2: Add to JSON Config
Open `trading_buddy_videos.json` and add to `videos` array:

```json
{
  "id": "your_video_id",
  "title": "Your Video Title",
  "description": "Description",
  "video_file": "static/videos/your_file.mp4",
  "thumbnail": "static/images/video_thumbnails/your_thumb.png",
  "vfx_file": "static/vfx/effect.json",  // Optional
  "category": "win|loss|general",
  "enabled": true,
  "order": 1,
  "tier_requirement": 3
}
```

### Step 3: Restart Server
Restart Flask server to load new video.

## ✨ Adding VFX (3 Steps)

### Step 1: Create VFX JSON
Create file in `static/vfx/your_effect.json`

### Step 2: Choose Type

**Particle Effect:**
```json
{
  "type": "particle",
  "particles": {
    "count": 100,
    "size": {"min": 2, "max": 8},
    "lifetime": {"min": 500, "max": 2000}
  },
  "colors": ["#fbbf24", "#f59e0b"]
}
```

**Animation Effect:**
```json
{
  "type": "animation",
  "keyframes": [
    {"time": 0, "scale": 1.0, "opacity": 0.0},
    {"time": 500, "scale": 1.2, "opacity": 1.0}
  ]
}
```

### Step 3: Add to JSON Config
Add to `vfx` array in `trading_buddy_videos.json`

## 📋 Common Categories

- **win**: After winning trades
- **loss**: After losing trades  
- **general**: Educational content

## 🎨 VFX Types Available

1. **profit_glow** - Golden glow for wins
2. **warning_pulse** - Red pulse for losses
3. **success_sparkle** - Sparkles for big wins
4. **market_crash** - Dramatic effect for big losses
5. **tech_glitch** - Tech-themed glitch effect

## 🔧 Quick Tips

- Use descriptive IDs: `win_risk_management` not `video1`
- Test videos before adding to production
- Keep VFX subtle - don't distract from content
- Match VFX colors to video category
- Update `last_updated` in JSON when making changes

## 📖 Full Documentation

See `VIDEO_VFX_MANAGEMENT.md` for complete guide.



