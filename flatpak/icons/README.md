# SigmaVault Desktop Icons

This directory contains application icons in various formats and sizes for desktop integration.

## Icon Specifications

### Required Sizes (PNG)

- 16x16 - Small icon for menus
- 32x32 - Medium icon for toolbars
- 48x48 - Standard icon size
- 64x64 - High DPI displays
- 128x128 - Large icon for preferences
- 256x256 - Extra large for app stores

### Scalable (SVG)

- Recommended for best quality at any size
- Must be placed in `hicolor/scalable/apps/`

## File Naming

All icons must follow the pattern:

- **PNG**: `{size}x{size}/com.sigmavault.desktop.png`
- **SVG**: `scalable/com.sigmavault.desktop.svg`

## Icon Design Guidelines

The SigmaVault icon should represent:

- Storage/NAS functionality (disk, server)
- Security/protection (shield, lock)
- Modern, clean design following GNOME HIG
- Works well in both light and dark themes

## Creating Icons

If you have an SVG source file:

```bash
# Install inkscape or imagemagick
sudo apt install inkscape  # or imagemagick

# Generate PNG sizes from SVG
for size in 16 32 48 64 128 256; do
  mkdir -p ${size}x${size}
  inkscape -w ${size} -h ${size} \
    com.sigmavault.desktop.svg \
    -o ${size}x${size}/com.sigmavault.desktop.png
done
```

Or using ImageMagick:

```bash
for size in 16 32 48 64 128 256; do
  mkdir -p ${size}x${size}
  convert com.sigmavault.desktop.svg \
    -resize ${size}x${size} \
    ${size}x${size}/com.sigmavault.desktop.png
done
```

## Placeholder Icons

Until custom icons are created, the Flatpak build will fall back to generic storage icons from the icon theme.

## TODO

- [ ] Design custom SigmaVault icon concept
- [ ] Create SVG master file
- [ ] Generate PNG sizes (16, 32, 48, 64, 128, 256)
- [ ] Test icon rendering in various contexts
- [ ] Test on light and dark themes
