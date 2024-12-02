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
    Fetch hourly weather data from NOAA's API.
    """
    # Get the forecast office and gridpoints
    point_url = f"{BASE_URL}/points/{lat},{lon}"
    point_response = requests.get(point_url)
    if point_response.status_code != 200:
        raise Exception(f"Error fetching point data: {point_response.json().get('detail', 'Unknown error')}")
    point_data = point_response.json()

    # Get the hourly forecast URL
    forecast_hourly_url = point_data["properties"]["forecastHourly"]
    forecast_response = requests.get(forecast_hourly_url)
    if forecast_response.status_code != 200:
        raise Exception(f"Error fetching hourly forecast: {forecast_response.json().get('detail', 'Unknown error')}")

    forecast_data = forecast_response.json()
    return forecast_data

def download_and_process_icon(icon_url):
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

    # Resize icon to fit (e.g., 64x64 pixels)
    icon_image = icon_image.resize((64, 64), Image.LANCZOS)

    # Convert to 1-bit pixels
    icon_image = icon_image.convert("1")

    return icon_image

def create_weather_image(weather_data):
    """
    Create a detailed weather forecast image with hourly data and icons.
    """
    # Create a black-and-white image in landscape mode
    image = Image.new("1", (IMAGE_WIDTH, IMAGE_HEIGHT), 1)  # '1' for 1-bit pixels
    draw = ImageDraw.Draw(image)

    # Load font
    font_size_title = 48
    font_size_text = 32
    font_title = ImageFont.truetype(FONT_PATH, font_size_title)
    font_text = ImageFont.truetype(FONT_PATH, font_size_text)

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

    # Prepare hourly data
    periods = weather_data["properties"]["periods"][:8]  # Next 8 hours
    start_x = 50
    start_y = header_y + header_height + 20  # Spacing after header
    box_width = (IMAGE_WIDTH - 100) // 8  # 100 for margins
    box_height = IMAGE_HEIGHT - start_y - 50  # 50 for bottom margin

    for i, period in enumerate(periods):
        # Calculate box position
        box_x = start_x + i * box_width
        box_y = start_y

        # Get time
        period_time = datetime.datetime.fromisoformat(period["startTime"]).strftime("%I %p")

        # Get temperature
        temperature = period["temperature"]
        temperature_unit = period["temperatureUnit"]

        # Get precipitation chance (if available)
        precipitation = period.get("probabilityOfPrecipitation", {}).get("value")
        if precipitation is not None:
            precipitation = f"{int(precipitation)}%"
        else:
            precipitation = "N/A"

        # Get icon
        icon_url = period["icon"]
        icon_image = download_and_process_icon(icon_url)

        # Draw the icon
        icon_x = box_x + (box_width - 64) // 2
        icon_y = box_y + 10
        image.paste(icon_image, (icon_x, icon_y))

        # Prepare text
        time_text = period_time
        temp_text = f"{temperature}°{temperature_unit}"
        precip_text = f"Precip: {precipitation}"

        # Calculate text positions using textbbox
        text_y_start = icon_y + 64 + 10  # Spacing after icon
        line_spacing = 5

        # Draw time
        time_bbox = draw.textbbox((0, 0), time_text, font=font_text)
        time_width = time_bbox[2] - time_bbox[0]
        time_height = time_bbox[3] - time_bbox[1]
        time_x = box_x + (box_width - time_width) // 2
        draw.text((time_x, text_y_start), time_text, font=font_text, fill=0)

        # Draw temperature
        temp_bbox = draw.textbbox((0, 0), temp_text, font=font_text)
        temp_width = temp_bbox[2] - temp_bbox[0]
        temp_height = temp_bbox[3] - temp_bbox[1]
        temp_x = box_x + (box_width - temp_width) // 2
        draw.text((temp_x, text_y_start + time_height + line_spacing), temp_text, font=font_text, fill=0)

        # Draw precipitation chance
        precip_bbox = draw.textbbox((0, 0), precip_text, font=font_text)
        precip_width = precip_bbox[2] - precip_bbox[0]
        precip_height = precip_bbox[3] - precip_bbox[1]
        precip_x = box_x + (box_width - precip_width) // 2
        draw.text((precip_x, text_y_start + time_height + temp_height + 2 * line_spacing), precip_text, font=font_text, fill=0)

    # Save the image
    image.save("weather_forecast_detailed.png")

def main():
    try:
        weather_data = fetch_weather_data(LAT, LON)
        create_weather_image(weather_data)
        print("Detailed weather image generated successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
