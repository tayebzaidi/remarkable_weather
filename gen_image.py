import requests
from PIL import Image, ImageDraw, ImageFont
import datetime

# Configuration
BASE_URL = "https://api.weather.gov"
LAT = "41.998886"  # Replace with your latitude
LON = "-87.660972"  # Replace with your longitude
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Update if necessary
IMAGE_WIDTH = 1404
IMAGE_HEIGHT = 1872

def fetch_weather(lat, lon):
    """
    Fetch weather forecast from NOAA's API.
    """
    point_url = f"{BASE_URL}/points/{lat},{lon}"
    point_response = requests.get(point_url)
    if point_response.status_code != 200:
        raise Exception(f"Error fetching point data: {point_response.json().get('detail', 'Unknown error')}")

    forecast_url = point_response.json()["properties"]["forecast"]
    forecast_response = requests.get(forecast_url)
    if forecast_response.status_code != 200:
        raise Exception(f"Error fetching forecast: {forecast_response.json().get('detail', 'Unknown error')}")

    return forecast_response.json()

def create_weather_image(weather_data):
    """
    Create a black-and-white image with the weather forecast.
    """
    # Extract the forecast for today
    periods = weather_data["properties"]["periods"]
    today_forecast = periods[0]
    name = today_forecast["name"]
    temperature = today_forecast["temperature"]
    temperature_unit = today_forecast["temperatureUnit"]
    short_forecast = today_forecast["shortForecast"]

    # Create a black-and-white image
    image = Image.new("1", (IMAGE_WIDTH, IMAGE_HEIGHT), 1)  # '1' for 1-bit pixels
    draw = ImageDraw.Draw(image)

    # Load font
    font_size = 40
    font = ImageFont.truetype(FONT_PATH, font_size)

    # Prepare text
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    text = (
        f"Weather Forecast\n\n"
        f"Date: {date_str}\n"
        f"Condition: {short_forecast}\n"
        f"Temperature: {temperature}°{temperature_unit}"
    )

    # Calculate text size using textbbox
    # We need to split the text into lines because textbbox doesn't handle multiline strings directly
    lines = text.split('\n')
    max_line_width = 0
    total_height = 0
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        line_heights.append(line_height)
        max_line_width = max(max_line_width, line_width)
        total_height += line_height

    x = (IMAGE_WIDTH - max_line_width) // 2
    y = (IMAGE_HEIGHT - total_height) // 2

    # Draw text line by line
    for i, line in enumerate(lines):
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_width = line_bbox[2] - line_bbox[0]
        line_height = line_heights[i]
        line_x = (IMAGE_WIDTH - line_width) // 2
        draw.text((line_x, y), line, font=font, fill=0, align="center")
        y += line_height

    # Save the image
    image.save("weather_forecast_noaa.png")

def main():
    try:
        weather_data = fetch_weather(LAT, LON)
        create_weather_image(weather_data)
        print("Weather image generated successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()