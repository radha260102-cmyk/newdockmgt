# Zone Configuration Guide

This guide explains how to configure the dock zone and parking line using the interactive configuration tool.

## Quick Start

1. Run the configuration script:
   ```bash
   python configure_zones.py
   ```

2. The script will open a video window showing your video file (`1.mp4` by default).

3. Use the following controls:
   - **'z'** - Switch to ZONE mode (green polygon)
   - **'p'** - Switch to PARKING LINE mode (yellow line)
   - **Click** - Add points on the video
   - **'c'** - Clear current mode's points
   - **'s'** - Save configuration to `zone_config.json`
   - **'q'** - Quit

## Step-by-Step Instructions

### 1. Configure Dock Zone

1. Press **'z'** to enter ZONE mode
2. Click on the video to mark the corners of your dock zone
   - You need at least 3 points to form a polygon
   - Click around the perimeter of the dock area
   - The zone will be shown in green
3. Continue clicking until you've marked all corners of the zone
4. The zone polygon will be automatically drawn

### 2. Configure Parking Line

1. Press **'p'** to enter PARKING LINE mode
2. Click on the video to mark the parking line
   - You need at least 2 points to form a line
   - Click along the parking line (usually a horizontal line)
   - The line will be shown in yellow
3. Continue clicking to mark the full length of the parking line

### 3. Save Configuration

1. Press **'s'** to save your configuration
2. The configuration will be saved to `zone_config.json`
3. The main application will automatically load this configuration

## Configuration File Format

The configuration is saved as JSON in `zone_config.json`:

```json
{
    "zone_coordinates": [
        [x1, y1],
        [x2, y2],
        [x3, y3],
        ...
    ],
    "parking_line_points": [
        [x1, y1],
        [x2, y2],
        ...
    ]
}
```

## Manual Configuration (Alternative)

If you prefer to manually edit the JSON file:

1. Create or edit `zone_config.json`
2. Add zone coordinates as a list of `[x, y]` pairs
3. Add parking line points as a list of `[x, y]` pairs
4. Save the file

Example:
```json
{
    "zone_coordinates": [
        [100, 100],
        [500, 100],
        [500, 400],
        [100, 400]
    ],
    "parking_line_points": [
        [100, 300],
        [500, 300]
    ]
}
```

## Tips

- **Zone**: Draw the zone to cover the entire dock area where trucks should park
- **Parking Line**: Draw the line where trucks should align (usually the front edge of the parking spot)
- **Multiple Points**: For curved lines, add more points for better accuracy
- **Video Frame**: Use 'n' for next frame and 'b' to go back to beginning if needed
- **Clear**: Use 'c' to clear and restart if you make a mistake

## Troubleshooting

1. **Video not opening**: Check that `1.mp4` exists, or pass video path as argument:
   ```bash
   python configure_zones.py path/to/your/video.mp4
   ```

2. **Points not saving**: Make sure you have at least 3 points for zone and 2 points for parking line

3. **Configuration not loading**: Check that `zone_config.json` is in the project root directory

4. **Zone not visible in main app**: Restart the main application after saving configuration

## Notes

- Coordinates are in pixels relative to the video resolution
- The configuration is automatically loaded when you run `main.py`
- You can reconfigure zones anytime by running `configure_zones.py` again

