import requests
import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
EIA_API_KEY = os.getenv("EIA_API_KEY")
CARBON_INTERFACE_API_KEY = os.getenv("CARBON_INTERFACE_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
OPENROUTESERVICE_API_KEY = os.getenv("OPENROUTESERVICE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Function to get petroleum price data from EIA API (for gasoline and diesel)
def get_energy_data():
    eia_url = "https://api.eia.gov/v2/petroleum/pri/gnd/data/?frequency=weekly&data[0]=value&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000"
    eia_url = f"{eia_url}&api_key={EIA_API_KEY}"
    
    response = requests.get(eia_url)
    if response.status_code == 200:
        data = response.json()
        latest_data = data['response']['data'][0]  # Get the latest data point
        price_value = latest_data['value']  # The value key contains the price
        period = latest_data['period']  # Get the time period of the data
        return {
            "price_per_gallon": price_value,  # Price per gallon for gasoline/diesel
            "period": period
        }
    else:
        print(f"Failed to get petroleum price data: {response.status_code}")
    return None

# Function to calculate carbon emissions using Carbon Interface API
def calculate_emissions(distance_km):
    url = "https://www.carboninterface.com/api/v1/estimates"
    headers = {
        "Authorization": f"Bearer {CARBON_INTERFACE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Hardcoded Toyota Corolla vehicle model ID
    vehicle_model_id = "7268a9b7-17e8-4c8d-acca-57059252afe9"  # Toyota Corolla example ID

    # Define the payload for the POST request
    payload = {
        "type": "vehicle",
        "distance_unit": "km",
        "distance_value": distance_km,
        "vehicle_model_id": vehicle_model_id  # Hardcoded Toyota Corolla vehicle model ID
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        emissions_data = response.json()
        return {
            "carbon_kg": emissions_data['data']['attributes']['carbon_kg'],
            "carbon_g": emissions_data['data']['attributes']['carbon_g'],
            "carbon_lb": emissions_data['data']['attributes']['carbon_lb'],
            "carbon_mt": emissions_data['data']['attributes']['carbon_mt']
        }
    else:
        print(f"Failed to calculate carbon emissions: {response.status_code}, {response.text}")
        return None

# Function to get weather data from OpenWeatherMap API
def get_weather_data(location):
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(weather_url)
    if response.status_code == 200:
        weather_data = response.json()
        return {
            "temperature": weather_data['main']['temp'],
            "weather": weather_data['weather'][0]['description'],
            "wind_speed": weather_data['wind']['speed']
        }
    else:
        print(f"Failed to get weather data: {response.status_code}")
    return None

# Function to get eco-friendly route using OpenRouteService API
def get_eco_route(origin_coords, destination_coords):
    headers = {
        "Authorization": f"Bearer {OPENROUTESERVICE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "coordinates": [origin_coords, destination_coords],
        "profile": "driving-car",
        "format": "json"
    }
    ors_url = "https://api.openrouteservice.org/v2/directions/driving-car/json"

    response = requests.post(ors_url, headers=headers, json=payload)
    if response.status_code == 200:
        route_data = response.json()

        # Extract route summary (distance and duration)
        if "routes" in route_data and len(route_data["routes"]) > 0:
            route_info = route_data['routes'][0]['summary']
            distance = route_info['distance'] / 1000  # Convert meters to kilometers
            duration = route_info['duration'] / 60  # Convert seconds to minutes

            # Extract turn-by-turn directions
            directions = []
            for segment in route_data['routes'][0]['segments']:
                for step in segment['steps']:
                    if 'instruction' in step:
                        directions.append(step['instruction'])

            # Print the route details
            print(f"Distance: {distance} km")
            print(f"Duration: {duration} minutes")
            print("Turn-by-turn Directions:")
            for i, direction in enumerate(directions):
                print(f"{i+1}. {direction}")

            # Return route data in case it needs further processing
            return {
                "distance_km": distance,
                "duration_minutes": duration,
                "directions": directions
            }
        else:
            print("No routes found in the response.")
            return None
    else:
        print(f"Failed to get route from OpenRouteService API: {response.status_code}, {response.text}")
        return None

# Function to generate OpenAI API prompt
def generate_openai_prompt(route_data, energy_data, carbon_emissions, weather_origin, weather_destination, vehicle):
    prompt = (
        f"Based on the following information:\n"
        f"- Distance: {route_data['distance_km']} km\n"
        f"- Estimated Travel Time: {route_data['duration_minutes']} minutes\n"
        f"- Energy Price: ${energy_data['price_per_gallon']} per gallon\n"
        f"- Estimated Carbon Emissions: {carbon_emissions} kg of CO₂\n"
        f"- Weather at Origin: {weather_origin['weather']}, Temperature: {weather_origin['temperature']}°C, Wind Speed: {weather_origin['wind_speed']} m/s\n"
        f"- Weather at Destination: {weather_destination['weather']}, Temperature: {weather_destination['temperature']}°C, Wind Speed: {weather_destination['wind_speed']} m/s\n"
        f"- Vehicle Type: {vehicle['type']}, Fuel Efficiency: {vehicle['efficiency']} km/l, Fuel Type: {vehicle['fuel_type']}\n"
        f"Provide a recommendation for reducing emissions and optimizing energy consumption for this route."
    )
    return prompt

# Function to call OpenAI API for generating recommendations
def get_openai_recommendation(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI assistant that provides route and energy optimization advice."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            n=1,
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return "Failed to generate recommendation."

# Function to integrate all the APIs and get final recommendation
def get_route_recommendation_with_openai(origin_coords, destination_coords, vehicle):
    # 1. Get eco-friendly route data from OpenRouteService
    route_data = get_eco_route(origin_coords, destination_coords)
    if not route_data:
        return "Failed to retrieve route data."

    # 2. Get energy price data from EIA API
    energy_data = get_energy_data()
    if not energy_data:
        return "Failed to retrieve energy data."

    # 3. Get weather data for origin and destination
    weather_origin = get_weather_data("San Francisco")  # Example location for origin
    weather_destination = get_weather_data("Los Angeles")  # Example location for destination
    if not weather_origin or not weather_destination:
        return "Failed to retrieve weather data."

    # 4. Calculate carbon emissions using Carbon Interface API
    carbon_emissions = calculate_emissions(route_data["distance_km"])
    if carbon_emissions is None:
        return "Failed to calculate carbon emissions."

    # 5. Generate a prompt for OpenAI using the retrieved data
    prompt = generate_openai_prompt(route_data, energy_data, carbon_emissions, weather_origin, weather_destination, vehicle)

    # 6. Call OpenAI API to generate recommendation
    recommendation = get_openai_recommendation(prompt)
    return recommendation

# Example usage
if __name__ == "__main__":
    origin_coords = [-122.4194, 37.7749]  # Coordinates for San Francisco
    destination_coords = [-118.2437, 34.0522]  # Coordinates for Los Angeles

    # Vehicle characteristics (Assuming Gas/Diesel vehicle)
    vehicle = {
        "type": "gasoline_vehicle",
        "model": "toyota_corolla",
        "efficiency": 15.0,  # Fuel efficiency in km/l
        "fuel_type": "gasoline"
    }

    recommendation = get_route_recommendation_with_openai(origin_coords, destination_coords, vehicle)
    print(f"AI-Generated Recommendation: {recommendation}")
