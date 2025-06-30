#!/usr/bin/env bash
###############################################################################
# upload_rm_wakeup.sh  –  Copy wake-up helper files to a reMarkable-1
#   • Expects set-next-wakeup.sh, rm-wakeup.service, rm-wakeup.timer
#     in the same directory
#   • Pushes them via scp, sets permissions, reloads systemd, enables timer
###############################################################################

RM1_CONFIG_NAME='remarkable'
RM1_IP='192.168.4.168'   # Replace with the IP address of your RM1 device
RM1_USER='root'
RM_HOST='remarkable'

### ── Where the helper files live locally ────────────────────────────────
SRC_DIR="rtc_alarm_scripts"

### ── Remote writable base directory ─────────────────────────────────────
REMOTE_BASE="/home/root/wi"
REMOTE_BIN="$REMOTE_BASE"
REMOTE_SYSD="$REMOTE_BASE"

### ──  Ensure files are present locally ───────────────────────────────────
for f in set_next_wakeup.sh rm_wakeup.service rm_wakeup.timer; do
  [[ -f "$SRC_DIR/$f" ]] || { echo "Missing file: $SRC_DIR/$f"; exit 1; }
done

### ── 5.  Create remote directories & upload  ────────────────────────────────
echo "→ Creating remote directories …"
ssh "$RM_HOST" "mkdir -p '$REMOTE_BIN' '$REMOTE_SYSD'"

echo "→ Uploading helper script …"
scp "$SRC_DIR/set_next_wakeup.sh" "$RM_HOST:$REMOTE_BIN/"

echo "→ Uploading systemd unit & timer …"
scp "$SRC_DIR/rm_wakeup.service" "$SRC_DIR/rm_wakeup.timer" \
    "$RM_HOST:$REMOTE_SYSD/"

### ── 6.  Create (or refresh) soft links in standard locations  ──────────────
echo "→ Linking into standard paths …"
ssh "$RM_HOST" <<EOF
# make script executable
chmod +x "$REMOTE_BIN/set_next_wakeup.sh"

# link script
ln -sfn "$REMOTE_BIN/set_next_wakeup.sh" /usr/bin/set_next_wakeup.sh

# link systemd unit & timer
ln -sfn "$REMOTE_SYSD/rm_wakeup.service" /etc/systemd/system/rm_wakeup.service
ln -sfn "$REMOTE_SYSD/rm_wakeup.timer"   /etc/systemd/system/rm_wakeup.timer
ln -sfn ../rm_wakeup.timer              /etc/systemd/system/multi-user.target.wants/rm_wakeup.timer

# activate
systemctl daemon-reload
systemctl start rm_wakeup.timer
EOF

echo "✓ Installation complete – the tablet will wake daily at 04:00 AM Central."
echo "  (If even creating the tiny symlinks fails, you’ll need to free a few kB on /.)"