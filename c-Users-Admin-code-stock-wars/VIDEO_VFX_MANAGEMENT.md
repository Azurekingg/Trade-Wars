# Video & VFX Management Guide

This guide explains how to add and manage videos and VFX effects for the Trading Buddy feature.

## File Structure

```
static/
├── videos/              # Video files directory
│   ├── win_*.mp4       # Videos for winning scenarios
│   ├── loss_*.mp4      # Videos for losing scenarios
│   └── general_*.mp4   # General educational videos
├── vfx/                # VFX configuration files
│   ├── profit_glow.json
│   ├── warning_pulse.json
│   └── ...
└── images/
    └── video_thumbnails/  # Thumbnail images for videos
```

## Configuration File: `trading_buddy_videos.json`

This JSON file manages all videos, VFX, and playlists.

### Adding a New Video

1. **Place your video file** in `static/videos/` directory
   - Supported formats: MP4, WebM, OGG
   - Recommended: MP4, H.264 codec, 1920x1080, 30fps
   - Max file size: 100MB

2. **Add video entry** to `trading_buddy_videos.json`:

```json
{
  "id": "unique_video_id",
  "title": "Video Title",
  "description": "Brief description",
  "video_file": "static/videos/your_video.mp4",
  "thumbnail": "static/images/video_thumbnails/your_thumb.png",
  "vfx_file": "static/vfx/effect.json",  // Optional
  "category": "win|loss|general",
  "subcategory": "risk_management|analysis|education",
  "tags": ["tag1", "tag2"],
  "duration_seconds": 30,
  "enabled": true,
  "order": 1,
  "tier_requirement": 3,
  "conditions": {
    "min_pnl": 0,        // Minimum PnL to show (for wins)
    "max_pnl": 0,        // Maximum PnL to show (for losses)
    "market_types": ["all"]  // or specific markets: ["tech_sector", "crypto_exchange"]
  }
}
```

### Adding a New VFX Effect

1. **Create VFX configuration file** in `static/vfx/` directory
   - Format: JSON
   - See examples below

2. **Add VFX entry** to `trading_buddy_videos.json`:

```json
{
  "id": "unique_vfx_id",
  "name": "Effect Name",
  "file": "static/vfx/your_effect.json",
  "type": "particle|animation",
  "enabled": true,
  "description": "What the effect does",
  "duration_ms": 2000,
  "intensity": "low|medium|high|extreme",
  "color_scheme": {
    "primary": "#hexcolor",
    "secondary": "#hexcolor",
    "glow": "#hexcolor"
  },
  "animation": {
    "type": "fade_in_out|pulse|sparkle|glitch|shake_crash",
    "speed": "slow|normal|fast|very_fast",
    "loop": true|false,
    // Additional properties based on type
  }
}
```

### VFX Configuration Examples

#### Particle Effect (profit_glow.json)
```json
{
  "type": "particle",
  "particles": {
    "count": 100,
    "size": {
      "min": 2,
      "max": 8
    },
    "lifetime": {
      "min": 500,
      "max": 2000
    },
    "velocity": {
      "x": {"min": -2, "max": 2},
      "y": {"min": -2, "max": 2}
    }
  },
  "colors": ["#fbbf24", "#f59e0b", "#fef3c7"],
  "blend_mode": "additive"
}
```

#### Animation Effect (warning_pulse.json)
```json
{
  "type": "animation",
  "keyframes": [
    {"time": 0, "scale": 1.0, "opacity": 0.0},
    {"time": 500, "scale": 1.2, "opacity": 1.0},
    {"time": 1000, "scale": 1.0, "opacity": 0.8},
    {"time": 1500, "scale": 1.2, "opacity": 1.0}
  ],
  "easing": "ease-in-out"
}
```

### Creating Playlists

Group related videos together:

```json
{
  "id": "playlist_id",
  "name": "Playlist Name",
  "description": "Description",
  "video_ids": ["video_id_1", "video_id_2"],
  "shuffle": true,
  "enabled": true
}
```

## Video Categories

- **win**: Shown after winning trades
- **loss**: Shown after losing trades
- **general**: Educational content shown randomly

## Conditions

Videos can be shown based on:
- **PnL**: Minimum/maximum profit/loss
- **Market Type**: Specific markets or "all"
- **Tier Requirement**: Minimum Founding Trader tier (3+)

## Best Practices

1. **Video Quality**
   - Resolution: 1920x1080 (Full HD)
   - Frame rate: 30fps
   - Codec: H.264
   - Bitrate: 5-10 Mbps

2. **Video Length**
   - Win tips: 30-60 seconds
   - Loss tips: 30-45 seconds
   - General: 60-120 seconds

3. **File Naming**
   - Use descriptive names: `win_risk_management.mp4`
   - Include category prefix: `win_`, `loss_`, `general_`

4. **Thumbnails**
   - Size: 320x180 (16:9 aspect ratio)
   - Format: PNG or JPG
   - Place in `static/images/video_thumbnails/`

5. **VFX**
   - Keep effects subtle and non-distracting
   - Match color scheme to video category
   - Test performance on different devices

## Testing

After adding videos/VFX:
1. Restart the Flask server
2. Enable Trading Buddy in Founding Traders settings
3. Complete a match (win or loss)
4. Verify video plays correctly with VFX

## Troubleshooting

- **Video not playing**: Check file path and format
- **VFX not showing**: Verify JSON syntax is valid
- **Performance issues**: Reduce video resolution or VFX particle count
- **Wrong video shown**: Check conditions and order in JSON



