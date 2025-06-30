#!/bin/sh
###############################################################################
# Wakes the reMarkable once a day at 04:00 Central time (CST/CDT),
# using ONLY BusyBox-compatible date syntax.
###############################################################################

RTC=/sys/class/rtc/rtc0/wakealarm

# --- 0. clear any previous alarm -------------------------------------------
echo 0 > "$RTC"

# --- 1. work in Central time ------------------------------------------------
export TZ="America/Chicago"

# today's calendar date, e.g. 2025-06-30
today=$(date +%Y-%m-%d)

# epoch seconds for today 04:00 local
four_today=$(date -d "$today 03:59" +%s)

# current epoch seconds (UTC, value is the same in any TZ)
now=$(date +%s)

# --- 2. decide whether to use today or tomorrow -----------------------------
if [ "$now" -ge "$four_today" ]; then
    # we're already past 04:00 → wake at 04:00 tomorrow
    target=$((four_today + 86400))   # add 24 h (DST edge cases ignored)
else
    target=$four_today
fi

# --- 3. arm the RTC ---------------------------------------------------------
echo "$target" > "$RTC"
