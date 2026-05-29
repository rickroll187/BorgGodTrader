#!/bin/bash
# Install BorgGodTrader desktop launcher

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing BorgGodTrader desktop launcher..."

# Update paths in .desktop file
sed -i "s|/home/user/BorgGodTrader|$SCRIPT_DIR|g" "$SCRIPT_DIR/BorgGodTrader.desktop"

# Make scripts executable
chmod +x "$SCRIPT_DIR/launch_borggod.sh"

# Copy to applications directory
DESKTOP_FILE="$HOME/.local/share/applications/BorgGodTrader.desktop"
cp "$SCRIPT_DIR/BorgGodTrader.desktop" "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

# Also copy to Desktop if it exists
if [ -d "$HOME/Desktop" ]; then
    cp "$SCRIPT_DIR/BorgGodTrader.desktop" "$HOME/Desktop/"
    chmod +x "$HOME/Desktop/BorgGodTrader.desktop"
    # Mark as trusted (for GNOME)
    gio set "$HOME/Desktop/BorgGodTrader.desktop" metadata::trusted true 2>/dev/null || true
    echo "[+] Desktop shortcut created"
fi

# Update desktop database
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "[+] Installation complete!"
echo ""
echo "You can now:"
echo "  1. Find 'BorgGodTrader' in your application menu"
echo "  2. Double-click the desktop icon (if on Desktop)"
echo "  3. Run: ./launch_borggod.sh"
echo ""
echo "First time setup:"
echo "  1. Copy .env.example to .env"
echo "  2. Add your API keys to .env"
echo "  3. Launch the dashboard"
