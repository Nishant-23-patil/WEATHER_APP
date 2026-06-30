#!/usr/bin/env python3
"""
weather.py

A command-line weather application that fetches and displays current weather
data for a specified location using the WeatherAPI.com API.
"""

import sys
import os
import argparse
import requests

# Enable ANSI codes on Windows cmd/powershell
if os.name == 'nt':
    os.system('')

# Reconfigure stdout/stderr to UTF-8 to prevent UnicodeEncodeError on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


# Default Configuration
DEFAULT_API_KEY = "18edfac773c34c538a794825252607"
BASE_URL = "http://api.weatherapi.com/v1/current.json"

# ANSI Colors & Styles
STYLE_RESET = "\033[0m"
STYLE_BOLD = "\033[1m"
STYLE_DIM = "\033[2m"
STYLE_ITALIC = "\033[3m"
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[96m"
COLOR_WHITE = "\033[97m"

def get_weather_emoji(condition_text, is_day):
    """
    Returns an appropriate emoji based on the condition text and time of day.
    """
    text = condition_text.lower()
    
    if "thunder" in text or "storm" in text:
        return "🌩️"
    elif "snow" in text or "sleet" in text or "ice" in text or "blizzard" in text or "hail" in text:
        return "❄️"
    elif "rain" in text or "drizzle" in text or "shower" in text:
        return "🌧️"
    elif "mist" in text or "fog" in text or "haze" in text or "overcast" in text:
        return "🌫️"
    elif "cloud" in text:
        return "⛅" if "partly" in text else "☁️"
    elif "sunny" in text:
        return "☀️"
    elif "clear" in text:
        return "☀️" if is_day == 1 else "🌙"
    
    # Default fallback
    return "☀️" if is_day == 1 else "🌙"

def get_epa_aqi_description(index):
    """
    Translates US EPA Air Quality Index value into qualitative description.
    """
    mapping = {
        1: (COLOR_GREEN + "Good" + STYLE_RESET),
        2: (COLOR_YELLOW + "Moderate" + STYLE_RESET),
        3: (COLOR_YELLOW + "Unhealthy for sensitive groups" + STYLE_RESET),
        4: (COLOR_RED + "Unhealthy" + STYLE_RESET),
        5: (COLOR_RED + STYLE_BOLD + "Very Unhealthy" + STYLE_RESET),
        6: (COLOR_RED + STYLE_BOLD + "Hazardous" + STYLE_RESET)
    }
    return mapping.get(index, "Unknown")

def get_uv_description(uv):
    """
    Translates UV index into a descriptive string with colors.
    """
    if uv <= 2:
        return f"{uv} ({COLOR_GREEN}Low{STYLE_RESET})"
    elif uv <= 5:
        return f"{uv} ({COLOR_YELLOW}Moderate{STYLE_RESET})"
    elif uv <= 7:
        return f"{uv} ({COLOR_RED}High{STYLE_RESET})"
    elif uv <= 10:
        return f"{uv} ({COLOR_RED}{STYLE_BOLD}Very High{STYLE_RESET})"
    else:
        return f"{uv} ({COLOR_RED}{STYLE_BOLD}Extreme{STYLE_RESET})"

def fetch_weather(location, api_key, include_aqi=True):
    """
    Fetches raw weather data from the weather API.
    """
    params = {
        "key": api_key,
        "q": location,
        "aqi": "yes" if include_aqi else "no"
    }
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        return response
    except requests.exceptions.Timeout:
        sys.stderr.write(f"{COLOR_RED}Error: Request timed out. Please check your connection.{STYLE_RESET}\n")
        return None
    except requests.exceptions.ConnectionError:
        sys.stderr.write(f"{COLOR_RED}Error: Could not connect to the weather service. Check your internet.{STYLE_RESET}\n")
        return None
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"{COLOR_RED}Error: An unexpected network error occurred: {e}{STYLE_RESET}\n")
        return None

def display_weather(response_data, unit='C', quiet=False):
    """
    Parses and displays weather data.
    """
    if not response_data:
        return

    # Extract weather fields
    location_info = response_data.get("location", {})
    current_info = response_data.get("current", {})
    
    city = location_info.get("name", "Unknown City")
    region = location_info.get("region", "")
    country = location_info.get("country", "")
    localtime = location_info.get("localtime", "N/A")
    
    is_day = current_info.get("is_day", 1)
    temp_c = current_info.get("temp_c", 0.0)
    temp_f = current_info.get("temp_f", 0.0)
    feelslike_c = current_info.get("feelslike_c", 0.0)
    feelslike_f = current_info.get("feelslike_f", 0.0)
    
    condition = current_info.get("condition", {})
    cond_text = condition.get("text", "Unknown")
    emoji = get_weather_emoji(cond_text, is_day)
    
    humidity = current_info.get("humidity", 0)
    wind_kph = current_info.get("wind_kph", 0.0)
    wind_mph = current_info.get("wind_mph", 0.0)
    wind_dir = current_info.get("wind_dir", "N/A")
    uv = current_info.get("uv", 0.0)
    
    aqi_info = current_info.get("air_quality", None)

    # Determine units to show
    if unit.upper() == 'F':
        temp_str = f"{temp_f:.1f}°F"
        feels_str = f"{feelslike_f:.1f}°F"
        wind_str = f"{wind_mph:.1f} mph ({wind_dir})"
    else:
        temp_str = f"{temp_c:.1f}°C"
        feels_str = f"{feelslike_c:.1f}°C"
        wind_str = f"{wind_kph:.1f} km/h ({wind_dir})"

    location_str = f"{city}"
    if region:
        location_str += f", {region}"
    location_str += f", {country}"

    if quiet:
        # Simple plain output
        print(f"Location: {location_str}")
        print(f"Condition: {cond_text} {emoji}")
        print(f"Temperature: {temp_str}")
        print(f"Feels Like: {feels_str}")
        print(f"Humidity: {humidity}%")
        print(f"Wind: {wind_str}")
        print(f"UV Index: {uv}")
        if aqi_info:
            epa_idx = aqi_info.get("us-epa-index", 0)
            print(f"Air Quality (EPA): {epa_idx}")
        print(f"Local Time: {localtime}")
        return

    # Beautiful ANSI format card
    border_color = COLOR_CYAN
    label_color = COLOR_WHITE + STYLE_BOLD
    value_color = STYLE_RESET

    # Prepare rows
    rows = [
        ("Condition", f"{cond_text} {emoji}"),
        ("Temperature", f"{COLOR_YELLOW}{temp_str}{STYLE_RESET}"),
        ("Feels Like", f"{COLOR_YELLOW}{feels_str}{STYLE_RESET}"),
        ("Humidity", f"{COLOR_BLUE}{humidity}%{STYLE_RESET}"),
        ("Wind", f"{COLOR_GREEN}{wind_str}{STYLE_RESET}"),
        ("UV Index", get_uv_description(uv))
    ]

    if aqi_info:
        epa_idx = aqi_info.get("us-epa-index", 0)
        aqi_desc = get_epa_aqi_description(epa_idx)
        rows.append(("Air Quality", f"{epa_idx} - {aqi_desc}"))
        
    rows.append(("Local Time", localtime))

    # Calculate padding sizes
    title_text = f"🌦  WEATHER REPORT: {location_str.upper()}"
    width = max(len(title_text) + 4, 55)
    
    # Print the Card
    print(f"\n  {border_color}╭{'─' * (width - 2)}╮{STYLE_RESET}")
    print(f"  {border_color}│{STYLE_RESET}  {COLOR_WHITE}{STYLE_BOLD}{title_text.ljust(width - 6)}{STYLE_RESET}  {border_color}│{STYLE_RESET}")
    print(f"  {border_color}├{'─' * (width - 2)}┤{STYLE_RESET}")
    
    for label, val in rows:
        # Strip ANSI codes to calculate actual text length for padding
        clean_val = val
        for code in [STYLE_RESET, STYLE_BOLD, STYLE_DIM, STYLE_ITALIC, COLOR_RED, COLOR_GREEN, COLOR_YELLOW, COLOR_BLUE, COLOR_MAGENTA, COLOR_CYAN, COLOR_WHITE]:
            clean_val = clean_val.replace(code, "")
        
        # Adjust for wide chars/emojis in length calculation if any (emojis are typically 2 positions)
        val_display_len = len(clean_val)
        # Account for standard 2-char emoji space differences if we have an emoji
        if "☀️" in clean_val or "🌙" in clean_val or "☁️" in clean_val or "⛅" in clean_val or "🌧️" in clean_val or "❄️" in clean_val or "🌩️" in clean_val or "🌫️" in clean_val or "💨" in clean_val:
            val_display_len += 1 # Python len() treats emoji as 1 char but terminal displays as 2
            
        spacing = (width - 20 - val_display_len)
        line = f"  {border_color}│{STYLE_RESET}  {label_color}{label.ljust(12)}:{STYLE_RESET} {val}{' ' * spacing}{border_color}│{STYLE_RESET}"
        print(line)
        
    print(f"  {border_color}╰{'─' * (width - 2)}╯{STYLE_RESET}\n")

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and display weather data for a city or ZIP code.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python weather.py --location "London"
  python weather.py -l "90210" -u F
  python weather.py (Interactive mode)"""
    )
    
    parser.add_argument("-l", "--location", help="City name or ZIP code. If omitted, starts interactive mode.")
    parser.add_argument("-u", "--unit", choices=["C", "F", "c", "f"], default="C", help="Temperature unit to use (C for Celsius, F for Fahrenheit).")
    parser.add_argument("-k", "--api-key", help="Override the default WeatherAPI.com API key.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Print in quiet mode (simple key-value outputs without borders).")
    parser.add_argument("--no-aqi", action="store_true", help="Do not fetch or display Air Quality Index (AQI) data.")
    
    args = parser.parse_args()
    
    api_key = args.api_key or DEFAULT_API_KEY
    unit = args.unit.upper()
    include_aqi = not args.no_aqi
    
    # If location is specified, run once
    if args.location:
        response = fetch_weather(args.location, api_key, include_aqi)
        if response is None:
            sys.exit(1)
            
        if response.status_code == 200:
            display_weather(response.json(), unit, args.quiet)
        else:
            try:
                err_data = response.json()
                err_msg = err_data.get("error", {}).get("message", "Unknown error")
                sys.stderr.write(f"{COLOR_RED}Error from WeatherAPI (Status {response.status_code}): {err_msg}{STYLE_RESET}\n")
            except Exception:
                sys.stderr.write(f"{COLOR_RED}Error: Server returned status code {response.status_code}{STYLE_RESET}\n")
            sys.exit(1)
            
    # Otherwise, enter interactive mode
    else:
        print(f"{COLOR_CYAN}{STYLE_BOLD}============================================")
        print(f"       🌤   Welcome to CLI Weather App  🌤")
        print(f"============================================{STYLE_RESET}")
        print(f"Unit: {COLOR_YELLOW}{unit}{STYLE_RESET} | Air Quality: {COLOR_YELLOW}{'Enabled' if include_aqi else 'Disabled'}{STYLE_RESET}")
        print(f"Type {COLOR_RED}'q'{STYLE_RESET} or {COLOR_RED}'exit'{STYLE_RESET} to quit, or {COLOR_GREEN}'unit'{STYLE_RESET} to toggle Celsius/Fahrenheit.\n")
        
        while True:
            try:
                user_input = input(f"{COLOR_WHITE}{STYLE_BOLD}Enter location:{STYLE_RESET} ").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n{COLOR_CYAN}Goodbye!{STYLE_RESET}")
                break
                
            if not user_input:
                continue
                
            lowered = user_input.lower()
            if lowered in ['q', 'quit', 'exit']:
                print(f"{COLOR_CYAN}Goodbye!{STYLE_RESET}")
                break
            elif lowered == 'unit':
                unit = 'F' if unit == 'C' else 'C'
                print(f"Temperature unit changed to {COLOR_YELLOW}{unit}{STYLE_RESET}\n")
                continue
            
            # Fetch and display
            print(f"{STYLE_DIM}Fetching weather for '{user_input}'...{STYLE_RESET}")
            response = fetch_weather(user_input, api_key, include_aqi)
            if response is None:
                continue
                
            if response.status_code == 200:
                display_weather(response.json(), unit, args.quiet)
            else:
                try:
                    err_data = response.json()
                    err_msg = err_data.get("error", {}).get("message", "Unknown error")
                    sys.stderr.write(f"{COLOR_RED}Error: {err_msg}{STYLE_RESET}\n\n")
                except Exception:
                    sys.stderr.write(f"{COLOR_RED}Error: Server returned status code {response.status_code}{STYLE_RESET}\n\n")

if __name__ == "__main__":
    main()
