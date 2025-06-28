import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
import datetime
import io
import textwrap
import math

# Configuration
BASE_URL = "https://api.weather.gov"
LAT = "41.998886"  # Replace with your latitude
LON = "-87.660972"  # Replace with your longitude
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Update if necessary

# Adjusted for landscape mode
IMAGE_WIDTH = 1872
IMAGE_HEIGHT = 1404

# Todoist token (store securely!)
TODOIST_API_TOKEN = "f3b99ffdbde9e7a30d9cd20a8da80db4d147ebda"

def fetch_weather_data(lat, lon):
    """
    Fetch daily forecast, hourly forecast, and grid data from NOAA's API.
    """
    # Get the forecast office and gridpoints
    point_url = f"{BASE_URL}/points/{lat},{lon}"
    point_response = requests.get(point_url)
    if point_response.status_code != 200:
        raise Exception(f"Error fetching point data: {point_response.json().get('detail', 'Unknown error')}")
    point_data = point_response.json()

    # Get the forecast URLs
    forecast_url = point_data["properties"]["forecast"]
    forecast_hourly_url = point_data["properties"]["forecastHourly"]
    grid_data_url = point_data["properties"]["forecastGridData"]

    # Fetch daily forecast
    forecast_response = requests.get(forecast_url)
    if forecast_response.status_code != 200:
        raise Exception(f"Error fetching forecast: {forecast_response.json().get('detail', 'Unknown error')}")
    daily_forecast_data = forecast_response.json()

    # Fetch hourly forecast
    forecast_hourly_response = requests.get(forecast_hourly_url)
    if forecast_hourly_response.status_code != 200:
        raise Exception(f"Error fetching hourly forecast: {forecast_hourly_response.json().get('detail', 'Unknown error')}")
    hourly_forecast_data = forecast_hourly_response.json()

    # Fetch grid data for humidity
    grid_data_response = requests.get(grid_data_url)
    if grid_data_response.status_code != 200:
        raise Exception(f"Error fetching grid data: {grid_data_response.json().get('detail', 'Unknown error')}")
    grid_data = grid_data_response.json()

    return daily_forecast_data, hourly_forecast_data, grid_data


def download_and_process_icon(icon_url, size):
    """
    Download the weather icon and process it for grayscale display.
    """
    # NOAA provides icons with multiple sizes; we'll select the first one
    icon_url = icon_url.split(",")[0]

    # Download the icon
    response = requests.get(icon_url)
    if response.status_code != 200:
        raise Exception(f"Error fetching icon: {icon_url}")

    # Open the image
    icon_image = Image.open(io.BytesIO(response.content))

    # Convert to grayscale
    icon_image = icon_image.convert("L")

    # Optionally invert if you want white on black:
    # icon_image = ImageOps.invert(icon_image)

    # Resize icon to fit
    icon_image = icon_image.resize((size, size), Image.LANCZOS)

    # We do NOT convert to "1" so we can keep grayscale
    return icon_image


def fetch_todoist_tasks(api_token):
    """
    Fetch tasks from Todoist, filter to get tasks due today and overdue tasks.
    Return two lists: (tasks_for_today, tasks_overdue).
    """
    headers = {
        "Authorization": f"Bearer {api_token}"
    }
    # Get all open tasks
    response = requests.get("https://api.todoist.com/rest/v2/tasks", headers=headers)
    response.raise_for_status()
    all_tasks = response.json()  # list of tasks (dicts)

    today_date_str = datetime.date.today().isoformat()  # e.g. "2025-01-31"
    tasks_for_today = []
    tasks_overdue = []

    for task in all_tasks:
        due_info = task.get("due")  # e.g. {"date": "2025-01-31", ...}
        if not due_info:
            # No due date, ignore or handle differently if desired
            continue

        due_date_str = due_info.get("date")  # "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SSZ"
        if not due_date_str:
            continue

        # Parse the date portion (strip time if any)
        due_date = datetime.datetime.fromisoformat(due_date_str.split("T")[0]).date()
        # Compare to today's date
        if due_date == datetime.date.today():
            tasks_for_today.append(task["content"])
        elif due_date < datetime.date.today():
            tasks_overdue.append(task["content"])

    return tasks_for_today, tasks_overdue


def draw_todoist_tasks(
    draw,
    tasks_for_today,
    tasks_overdue,
    x,
    y,
    max_width,
    max_height,
    font_text,
    font_header
):
    """
    Draw a "tasks box" with a 'Today' header and tasks,
    then an 'Overdue' header and tasks, numbering each.
    Truncates with '+X additional items' if space is exceeded.
    """
    # Outline the entire tasks region (optional)
    outline_color = 0  # black
    draw.rectangle([x, y, x + max_width, y + max_height], outline=outline_color, width=2)

    # Helper function to wrap text to a specified width in pixels
    def wrap_text_to_fit(text, font, max_px_width):
        lines = []
        words = text.split()
        current_line = ""
        for w in words:
            test_line = w if not current_line else (current_line + " " + w)
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if (bbox[2] - bbox[0]) <= max_px_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = w
        if current_line:
            lines.append(current_line)
        return lines

    def draw_section_header(header_text, top_y):
        """
        Draw a light gray background with black text for a section header.
        Returns the height used (header box height).
        """
        header_height = 40
        header_bg_color = 230  # light gray
        draw.rectangle([x, top_y, x + max_width, top_y + header_height], fill=header_bg_color)
        # Write the header text
        text_x = x + 10
        text_y = top_y + 5
        draw.text((text_x, text_y), header_text, font=font_header, fill=0)
        return header_height

    # We'll keep track of how many tasks we've drawn total (for the truncation logic).
    tasks_drawn_count = 0
    tasks_total_count = len(tasks_for_today) + len(tasks_overdue)

    # Where we start drawing lines inside the box (some padding from edges)
    current_y = y + 5
    left_margin = x + 10
    right_boundary = x + max_width - 10

    # Draw "Today" header
    section_header_height = draw_section_header("Today", current_y)
    current_y += section_header_height + 5  # gap below header

    # Draw today's tasks
    for i, task_text in enumerate(tasks_for_today, start=1):
        # Numbering the task
        numbered_line = f"{i}. {task_text}"
        # Wrap if needed
        wrapped_lines = wrap_text_to_fit(numbered_line, font_text, right_boundary - left_margin)

        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=font_text)
            line_height = bbox[3] - bbox[1]
            if current_y + line_height > (y + max_height - 20):
                # Not enough space; show how many are left
                remaining = tasks_total_count - tasks_drawn_count
                draw.text((left_margin, current_y), f"+{remaining} additional items", font=font_text, fill=0)
                return
            # Draw the line
            draw.text((left_margin, current_y), line, font=font_text, fill=0)
            current_y += (line_height + 5)

        tasks_drawn_count += 1

    # Draw "Overdue" header (only if we have any overdue tasks)
    if tasks_overdue:
        current_y += 10  # gap above next header
        section_header_height = draw_section_header("Overdue", current_y)
        current_y += section_header_height + 5

        for j, task_text in enumerate(tasks_overdue, start=1):
            # Overdue numbering separate (or continue from i if you prefer)
            numbered_line = f"{j}. {task_text}"
            wrapped_lines = wrap_text_to_fit(numbered_line, font_text, right_boundary - left_margin)

            for line in wrapped_lines:
                bbox = draw.textbbox((0, 0), line, font=font_text)
                line_height = bbox[3] - bbox[1]
                if current_y + line_height > (y + max_height - 20):
                    remaining = tasks_total_count - tasks_drawn_count
                    draw.text((left_margin, current_y), f"+{remaining} additional items", font=font_text, fill=0)
                    return
                draw.text((left_margin, current_y), line, font=font_text, fill=0)
                current_y += (line_height + 5)

            tasks_drawn_count += 1


def create_weather_image(daily_data, hourly_data, grid_data, tasks_for_today, tasks_overdue):
    """
    Create a detailed weather forecast image with hourly data.
    Then add a 'tasks box' in the lower-left corner with 
    today's tasks and overdue tasks from Todoist.
    """
    # Create a grayscale image in landscape mode
    # 255 = white background
    image = Image.new("L", (IMAGE_WIDTH, IMAGE_HEIGHT), 255)
    draw = ImageDraw.Draw(image)

    # Load fonts
    font_size_title = 80
    font_size_text = 45
    font_size_small_text = 36
    font_title = ImageFont.truetype(FONT_PATH, font_size_title)
    font_text = ImageFont.truetype(FONT_PATH, font_size_text)
    font_small_text = ImageFont.truetype(FONT_PATH, font_size_small_text)

    # Extra font for section headers in tasks
    font_size_header = 40
    font_header = ImageFont.truetype(FONT_PATH, font_size_header)

    # Fonts for hourly forecast
    font_size_time = 50  # Largest
    font_size_temp = 45  # Medium
    font_size_main = 40  # Precipitation
    font_size_humidity = 36  # Slightly smaller
    font_time = ImageFont.truetype(FONT_PATH, font_size_time)
    font_temp = ImageFont.truetype(FONT_PATH, font_size_temp)
    font_main = ImageFont.truetype(FONT_PATH, font_size_main)
    font_humidity = ImageFont.truetype(FONT_PATH, font_size_humidity)

    # Prepare the header text
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    header_text = f"{date_str}"

    # Draw the header
    header_bbox = draw.textbbox((0, 0), header_text, font=font_title)
    header_width = header_bbox[2] - header_bbox[0]
    header_height = header_bbox[3] - header_bbox[1]
    header_x = (IMAGE_WIDTH - header_width) // 2
    header_y = 20  # Top margin
    draw.text((header_x, header_y), header_text, font=font_title, fill=0)

    # Reserve space in top-left corner for general overview
    overview_x = 50
    overview_y = header_y + header_height + 20
    overview_width = IMAGE_WIDTH // 3  # Reserve 1/3 of the width
    overview_height = IMAGE_HEIGHT - overview_y - 50  # 50 for bottom margin

# --- DAILY FORECAST (TODAY -OR- TOMORROW) --------------------------------
    #
    # If we’re running late in the evening (≥ 22:00) we want the screen to
    # show the *next* calendar day instead of a day that’s almost over.
    #
    target_date = now.date()
    if now.hour >= 19:                 # 7 PM threshold
        target_date += datetime.timedelta(days=1)

    # Grab the daytime and nighttime periods that belong to the target date
    periods = daily_data["properties"]["periods"]
    day_period   = None   # first daytime block for the target date
    night_period = None   # first nighttime block for the target date
    for p in periods:
        p_date = datetime.datetime.fromisoformat(p["startTime"]).date()
        if p_date == target_date:
            # Keep the first match of each kind
            if p["isDaytime"] and day_period is None:
                day_period = p
            elif not p["isDaytime"] and night_period is None:
                night_period = p
        if day_period and night_period:
            break

    if not day_period or not night_period:
        raise Exception(f"Forecast data for {target_date.isoformat()} is incomplete.")

    # Overall forecast information
    temp_high = day_period["temperature"]
    temp_low = night_period["temperature"]
    temp_unit = day_period["temperatureUnit"]
    short_forecast = day_period["shortForecast"]
    icon_url = day_period["icon"]

    # Download and process the larger icon for daily forecast
    icon_size = 256
    icon_image = download_and_process_icon(icon_url, icon_size)

    # Place daily forecast icon
    icon_x = overview_x + 10
    icon_y = overview_y + 10
    image.paste(icon_image, (icon_x, icon_y))

    # Utility: wrap text
    def wrap_text(text, font, max_width, draw_obj):
        lines = []
        words = text.split()
        while words:
            line = ''
            while words:
                word = words[0]
                test_line = line + ' ' + word if line else word
                bbox = draw_obj.textbbox((0, 0), test_line, font=font)
                w = bbox[2] - bbox[0]
                if w <= max_width:
                    line = test_line
                    words.pop(0)
                else:
                    break
            if not line:
                line = words.pop(0)
            lines.append(line)
        return '\n'.join(lines)

    # Prepare daily text
    text_x = icon_x + icon_size + 20
    text_y = icon_y
    max_text_width = (overview_x + overview_width) - text_x - 10
    wrapped_short_forecast = wrap_text(short_forecast, font_text, max_text_width, draw)
    overview_text = (
        f"{wrapped_short_forecast}\n"
        f"High: {temp_high}°{temp_unit}\n"
        f"Low: {temp_low}°{temp_unit}"
    )

    # Draw overview text next to icon
    draw.multiline_text((text_x, text_y), overview_text, font=font_text, fill=0, spacing=4)
    
    # Measure how tall that text block is, to place the tasks box below it
    daily_text_bbox = draw.textbbox((text_x, text_y), overview_text, font=font_text)
    daily_text_bottom = daily_text_bbox[3]

    # The overall daily forecast section might be as tall as the icon if icon is bigger
    daily_forecast_bottom = max(icon_y + icon_size, daily_text_bottom) + 20

    # --- TASKS BOX ---
    # We'll place the tasks box underneath the daily forecast within the same left column.
    tasks_box_x = overview_x
    tasks_box_y = daily_forecast_bottom
    tasks_box_width = overview_width
    # We'll let it extend down to the bottom margin of that column
    tasks_box_height = (overview_y + overview_height) - tasks_box_y

    # Draw the tasks in that box
    draw_todoist_tasks(
        draw,
        tasks_for_today,
        tasks_overdue,
        tasks_box_x,
        tasks_box_y,
        tasks_box_width,
        tasks_box_height,
        font_small_text,  # For task lines
        font_header       # For section headers "Today"/"Overdue"
    )

    # --- HOURLY FORECAST ---
    hourly_start_x = overview_x + overview_width + 20  # Start after overview area
    hourly_start_y = overview_y

    # Prepare hourly data for hours from 5 AM to 5 PM (or later if run later)
    start_hour = 5
    end_hour = start_hour + 11
    periods = hourly_data["properties"]["periods"]
    filtered_periods = []
    for period in periods:
        period_time = datetime.datetime.fromisoformat(period["startTime"])
        # Additional logic if code is run at night to get next days data:
        forecast_date = now.date()
        print(forecast_date)
        if now.hour >= end_hour:
            forecast_date += datetime.timedelta(days=1)
            print(forecast_date)
        if period_time.date() == forecast_date and 5 <= period_time.hour <= end_hour:
            print("Filtered Period Length: ", len(filtered_periods))
            filtered_periods.append(period)
    print(filtered_periods)

    if not filtered_periods:
        raise Exception("No hourly data available for the specified time range.")

    # Fetch humidity data from grid data
    humidity_values = grid_data["properties"]["relativeHumidity"]["values"]

    # Create a mapping from time to humidity
    humidity_dict = {}
    for entry in humidity_values:
        valid_time = entry["validTime"]
        value = entry["value"]
        time_str = valid_time.split("/")[0]
        time_dt = datetime.datetime.fromisoformat(time_str.rstrip('Z'))
        humidity_dict[time_dt] = value

    # Determine size for each hourly box
    total_width = IMAGE_WIDTH - hourly_start_x - 50
    max_box_height = IMAGE_HEIGHT - hourly_start_y - 50
    box_width = total_width // 2  # Two columns
    icon_size_small = 80
    vertical_spacing = 30

    # Estimate content height per hourly forecast
    sample_lines = [
        ("12 PM", font_time),
        ("75°F", font_temp),
        ("Precip: 20%", font_main),
        ("Humidity: 60%", font_humidity)
    ]
    total_text_height = 0
    for text_line, fnt in sample_lines:
        bbox = draw.textbbox((0, 0), text_line, font=fnt)
        line_height = bbox[3] - bbox[1]
        total_text_height += line_height + int(fnt.size * 0.1)
    content_height = max(icon_size_small, total_text_height) + 20
    content_height += vertical_spacing

    # Calculate how many periods fit in one column
    num_periods = len(filtered_periods)
    periods_per_column = int((max_box_height + vertical_spacing) // content_height)
    print(periods_per_column)
    periods_per_column = min(periods_per_column, (num_periods + 1) // 2)
    print(periods_per_column)

    # Start positions for columns
    column_positions = [
        (hourly_start_x, hourly_start_y),
        (hourly_start_x + box_width, hourly_start_y)
    ]

    for idx, period in enumerate(filtered_periods):
        column = idx // periods_per_column
        position_in_column = idx % periods_per_column

        box_x, base_y = column_positions[column]
        box_y = base_y + position_in_column * content_height

        # Time
        period_time = datetime.datetime.fromisoformat(period["startTime"])
        time_str = period_time.strftime("%I %p")

        # Temperature
        temperature = period["temperature"]
        temperature_unit = period["temperatureUnit"]

        # Precipitation
        precipitation_value = period.get("probabilityOfPrecipitation", {}).get("value")
        if precipitation_value is not None:
            precipitation = f"{int(precipitation_value)}%"
        else:
            precipitation = "N/A"

        # Humidity
        humidity_value = humidity_dict.get(period_time)
        if humidity_value is not None:
            humidity = f"{int(humidity_value)}%"
        else:
            humidity = "N/A"

        # Icon
        icon_url = period["icon"]
        small_icon_image = download_and_process_icon(icon_url, icon_size_small)

        # Positions
        icon_x = box_x + 10
        icon_y = box_y + 10
        text_x = icon_x + icon_size_small + 10
        text_y = box_y + 10

        # Draw icon
        image.paste(small_icon_image, (icon_x, icon_y))

        # Lines
        lines = [
            (time_str, font_time),
            (f"{temperature}°{temperature_unit}", font_temp),
            (f"Precip: {precipitation}", font_main),
            (f"Humidity: {humidity}", font_humidity)
        ]

        current_y = text_y
        for text_line, fnt in lines:
            draw.text((text_x, current_y), text_line, font=fnt, fill=0)
            bbox = draw.textbbox((text_x, current_y), text_line, font=fnt)
            line_height = bbox[3] - bbox[1]
            current_y += line_height + int(fnt.size * 0.1)

    # Rotate and save
    final_image = image.rotate(90, expand=True)
    final_image.save(
        "weather_forecast.png",
        optimize=True,
        compress_level=9,
        dpi=(226, 226)
    )


def main():
    try:
        # 1) Fetch NOAA weather data
        daily_data, hourly_data, grid_data = fetch_weather_data(LAT, LON)

        # 2) Fetch tasks from Todoist
        tasks_for_today, tasks_overdue = fetch_todoist_tasks(TODOIST_API_TOKEN)

        # 3) Build and save the combined image
        create_weather_image(daily_data, hourly_data, grid_data, tasks_for_today, tasks_overdue)

        print("Detailed weather image (with Todoist tasks) generated successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
