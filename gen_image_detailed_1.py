import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
import datetime
import io

# Configuration
BASE_URL = "https://api.weather.gov"
LAT = "38.8951"  # Replace with your latitude
LON = "-77.0364"  # Replace with your longitude
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Update if necessary

# Adjusted for landscape mode
IMAGE_WIDTH = 1872
IMAGE_HEIGHT = 1404

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
    Download the weather icon and process it for black-and-white display.
    """
    # NOAA provides icons with multiple sizes; we'll select the first one
    icon_url = icon_url.split(",")[0]

    # Download the icon
    response = requests.get(icon_url)
    if response.status_code != 200:
        raise Exception(f"Error fetching icon: {icon_url}")

    # Open the image
    icon_image = Image.open(io.BytesIO(response.content))

    # Convert to black and white
    icon_image = icon_image.convert("L")  # Convert to grayscale
    icon_image = ImageOps.invert(icon_image)  # Invert colors for better visibility on e-ink

    # Resize icon to fit
    icon_image = icon_image.resize((size, size), Image.LANCZOS)

    # Convert to 1-bit pixels
    icon_image = icon_image.convert("1")

    return icon_image

def create_weather_image(daily_data, hourly_data, grid_data):
    """
    Create a detailed weather forecast image with hourly data.
    """
    # Create a black-and-white image in landscape mode
    image = Image.new("1", (IMAGE_WIDTH, IMAGE_HEIGHT), 1)  # '1' for 1-bit pixels
    draw = ImageDraw.Draw(image)

    # Load fonts
    font_size_title = 64
    font_size_text = 36
    font_size_small_text = 28
    font_title = ImageFont.truetype(FONT_PATH, font_size_title)
    font_text = ImageFont.truetype(FONT_PATH, font_size_text)
    font_small_text = ImageFont.truetype(FONT_PATH, font_size_small_text)

    # Prepare the header text
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    header_text = f"Weather Forecast for {date_str}"

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

    # Get today's forecast from daily data
    periods = daily_data["properties"]["periods"]
    today_daytime = None
    today_nighttime = None
    for period in periods:
        start_date = datetime.datetime.fromisoformat(period["startTime"]).date()
        if start_date == now.date():
            if period["isDaytime"]:
                today_daytime = period
            else:
                today_nighttime = period

    if not today_daytime or not today_nighttime:
        raise Exception("Today's forecast data is incomplete.")

    # Get overall forecast information
    temp_high = today_daytime["temperature"]
    temp_low = today_nighttime["temperature"]
    temp_unit = today_daytime["temperatureUnit"]
    short_forecast = today_daytime["shortForecast"]
    detailed_forecast = today_daytime["detailedForecast"]
    icon_url = today_daytime["icon"]

    # Download and process larger icon
    icon_size = 256  # Larger icon size
    icon_image = download_and_process_icon(icon_url, icon_size)

    # Draw the icon
    icon_x = overview_x + 10
    icon_y = overview_y + 10
    image.paste(icon_image, (icon_x, icon_y))

    # Prepare text
    overview_text = f"{short_forecast}\nHigh: {temp_high}°{temp_unit}\nLow: {temp_low}°{temp_unit}"

    # Draw text next to icon
    text_x = icon_x + icon_size + 20
    text_y = icon_y
    draw.multiline_text((text_x, text_y), overview_text, font=font_text, fill=0)

    # Adjust start position for hourly data
    hourly_start_x = overview_x + overview_width + 20  # Start after the overview area
    hourly_start_y = overview_y

    # Prepare hourly data for hours from 5 AM to 5 PM
    periods = hourly_data["properties"]["periods"]
    filtered_periods = []
    for period in periods:
        period_time = datetime.datetime.fromisoformat(period["startTime"])
        if period_time.date() == now.date() and 5 <= period_time.hour <= 17:
            filtered_periods.append(period)

    # Number of periods to display (from 5 AM to 5 PM)
    num_periods = len(filtered_periods)

    if num_periods == 0:
        raise Exception("No hourly data available for the specified time range.")

    # Fetch humidity data from grid data
    humidity_values = grid_data["properties"]["relativeHumidity"]["values"]

    # Create a mapping from time to humidity
    humidity_dict = {}
    for entry in humidity_values:
        valid_time = entry["validTime"]
        value = entry["value"]
        # Extract the datetime from validTime (format: '2023-09-18T06:00:00+00:00/PT1H')
        time_str = valid_time.split("/")[0]
        time_dt = datetime.datetime.fromisoformat(time_str.rstrip('Z'))
        humidity_dict[time_dt] = value

    # Adjust box width and height
    total_width = IMAGE_WIDTH - hourly_start_x - 50  # 50 for right margin
    max_box_height = IMAGE_HEIGHT - hourly_start_y - 50  # 50 for bottom margin
    box_width = total_width // 2  # Two columns
    box_height = None  # We'll calculate based on content

    # Prepare to split periods into rows
    periods_per_column = (num_periods + 1) // 2  # Distribute periods evenly between two columns

    # Start positions for columns
    column_positions = [
        (hourly_start_x, hourly_start_y),
        (hourly_start_x + box_width, hourly_start_y)
    ]

    for idx, period in enumerate(filtered_periods):
        column = idx // periods_per_column
        position_in_column = idx % periods_per_column

        box_x, base_y = column_positions[column]
        box_y = base_y + position_in_column * (max_box_height // periods_per_column)

        # Get time
        period_time = datetime.datetime.fromisoformat(period["startTime"])
        time_str = period_time.strftime("%I %p")

        # Get temperature
        temperature = period["temperature"]
        temperature_unit = period["temperatureUnit"]

        # Get precipitation chance
        precipitation = period.get("probabilityOfPrecipitation", {}).get("value")
        if precipitation is not None:
            precipitation = f"{int(precipitation)}%"
        else:
            precipitation = "N/A"

        # Get humidity
        humidity_value = humidity_dict.get(period_time)
        if humidity_value is not None:
            humidity = f"{int(humidity_value)}%"
        else:
            humidity = "N/A"

        # Prepare text
        forecast_text = (
            f"Time: {time_str}\n"
            f"Temp: {temperature}°{temperature_unit}\n"
            f"Precipitation: {precipitation}\n"
            f"Humidity: {humidity}"
        )

        # Draw text block
        draw.multiline_text(
            (box_x + 10, box_y + 10),
            forecast_text,
            font=font_small_text,
            fill=0,
            spacing=4
        )

    # Save the image
    image.save("weather_forecast_detailed.png")

def main():
    try:
        daily_data, hourly_data, grid_data = fetch_weather_data(LAT, LON)
        create_weather_image(daily_data, hourly_data, grid_data)
        print("Detailed weather image generated successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
