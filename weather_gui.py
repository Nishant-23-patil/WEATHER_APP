#!/usr/bin/env python3
"""
weather_gui.py

A modern, graphical weather application in Python using Tkinter and Pillow.
Fetches detailed weather, hourly forecasts, and 3-day daily forecasts.
Supports location search, IP-based auto-detection, and Celsius/Fahrenheit units.
"""

import sys
import os
import io
import threading
import requests
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

# Enable UTF-8 encoding on standard streams to avoid Unicode issues
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Default Configurations
DEFAULT_API_KEY = "18edfac773c34c538a794825252607"
BASE_URL = "http://api.weatherapi.com/v1/forecast.json"
IP_GEOLOCATION_URL = "http://ip-api.com/json/"

# Color Palette (Dark Theme / Slate & Sky)
COLOR_BG = "#0f172a"          # Slate 900
COLOR_CARD = "#1e293b"        # Slate 800
COLOR_CARD_INNER = "#334155"  # Slate 700
COLOR_TEXT_PRIMARY = "#f8fafc"# Slate 50
COLOR_TEXT_MUTED = "#94a3b8"  # Slate 400
COLOR_ACCENT = "#38bdf8"      # Sky 400
COLOR_ACCENT_ALT = "#3b82f6"  # Blue 500
COLOR_WARN = "#fb923c"        # Orange 400
COLOR_SUCCESS = "#4ade80"     # Green 400
COLOR_ERROR = "#f87171"       # Red 400

# Resampling Filter Compatibility
try:
    IMG_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    try:
        IMG_FILTER = Image.LANCZOS
    except AttributeError:
        IMG_FILTER = Image.ANTIALIAS

class WeatherAppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Dashboard")
        self.root.geometry("850x780")
        self.root.minsize(800, 720)
        self.root.configure(bg=COLOR_BG)

        # Application State
        self.api_key = DEFAULT_API_KEY
        self.unit = "C"  # "C" or "F"
        self.weather_data = None
        self.icon_cache = {}
        
        # UI Setup
        self.create_widgets()
        
        # Auto-detect location on startup in a separate thread
        self.auto_detect_location()

    def create_widgets(self):
        # Master container with padding
        self.main_container = tk.Frame(self.root, bg=COLOR_BG, padx=20, pady=20)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # ----------------- 1. Top Search Bar -----------------
        self.search_frame = tk.Frame(self.main_container, bg=COLOR_BG)
        self.search_frame.pack(fill=tk.X, pady=(0, 15))

        # Styled Entry Frame for custom border color
        self.entry_border = tk.Frame(self.search_frame, bg=COLOR_CARD_INNER, bd=1, padx=2, pady=2)
        self.entry_border.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.location_entry = tk.Entry(
            self.entry_border,
            bg=COLOR_CARD,
            fg=COLOR_TEXT_PRIMARY,
            insertbackground=COLOR_TEXT_PRIMARY,
            font=("Segoe UI", 11),
            bd=0,
            highlightthickness=0
        )
        self.location_entry.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.location_entry.bind("<Return>", lambda e: self.trigger_search())
        self.location_entry.insert(0, "London")  # Default placeholder

        # Search Button
        self.search_btn = tk.Button(
            self.search_frame,
            text="🔍 Search",
            command=self.trigger_search,
            bg=COLOR_ACCENT,
            fg=COLOR_BG,
            activebackground="#7dd3fc",
            activeforeground=COLOR_BG,
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=15,
            pady=6,
            relief="flat",
            cursor="hand2"
        )
        self.search_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Auto Detect Button
        self.detect_btn = tk.Button(
            self.search_frame,
            text="📍 Auto-Detect",
            command=self.auto_detect_location,
            bg=COLOR_CARD_INNER,
            fg=COLOR_TEXT_PRIMARY,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=12,
            pady=6,
            relief="flat",
            cursor="hand2"
        )
        self.detect_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Unit Toggle Button
        self.unit_btn = tk.Button(
            self.search_frame,
            text="°C",
            command=self.toggle_unit,
            bg=COLOR_CARD_INNER,
            fg=COLOR_TEXT_PRIMARY,
            activebackground=COLOR_CARD,
            activeforeground=COLOR_TEXT_PRIMARY,
            font=("Segoe UI", 10, "bold"),
            bd=0,
            padx=12,
            pady=6,
            relief="flat",
            cursor="hand2",
            width=3
        )
        self.unit_btn.pack(side=tk.LEFT)

        # ----------------- 2. Status Label (Loading/Error) -----------------
        self.status_lbl = tk.Label(
            self.main_container,
            text="Starting up...",
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG,
            font=("Segoe UI", 9, "italic")
        )
        self.status_lbl.pack(anchor=tk.W, pady=(0, 10))

        # ----------------- 3. Weather Dashboard Frame (Grid Layout) -----------------
        self.dashboard_frame = tk.Frame(self.main_container, bg=COLOR_BG)
        self.dashboard_frame.pack(fill=tk.BOTH, expand=True)
        self.dashboard_frame.columnconfigure(0, weight=2)  # Current weather & Details
        self.dashboard_frame.columnconfigure(1, weight=1)  # 3-Day Forecast
        self.dashboard_frame.rowconfigure(0, weight=1)

        # LEFT SIDE: Current Weather & Stats Grid
        self.left_column = tk.Frame(self.dashboard_frame, bg=COLOR_BG)
        self.left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Left Side - Card 1: Main Current Weather Card
        self.current_card = tk.Frame(self.left_column, bg=COLOR_CARD, bd=0, padx=20, pady=18)
        self.current_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # City Name Label
        self.city_lbl = tk.Label(
            self.current_card,
            text="City Name",
            font=("Segoe UI", 22, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD
        )
        self.city_lbl.pack(anchor=tk.W)

        # Country & Region Label
        self.region_lbl = tk.Label(
            self.current_card,
            text="Region, Country",
            font=("Segoe UI", 11),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD
        )
        self.region_lbl.pack(anchor=tk.W, pady=(0, 15))

        # Temp & Condition Layout Frame
        self.temp_cond_frame = tk.Frame(self.current_card, bg=COLOR_CARD)
        self.temp_cond_frame.pack(fill=tk.X, anchor=tk.W)

        # Temperature
        self.temp_lbl = tk.Label(
            self.temp_cond_frame,
            text="--°C",
            font=("Segoe UI", 48, "bold"),
            fg=COLOR_ACCENT,
            bg=COLOR_CARD
        )
        self.temp_lbl.pack(side=tk.LEFT)

        # Weather Icon Label
        self.icon_lbl = tk.Label(self.temp_cond_frame, bg=COLOR_CARD)
        self.icon_lbl.pack(side=tk.LEFT, padx=20)

        # Condition Text (e.g. Sunny)
        self.condition_lbl = tk.Label(
            self.current_card,
            text="--",
            font=("Segoe UI", 14, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD
        )
        self.condition_lbl.pack(anchor=tk.W, pady=(5, 5))

        # Feels Like
        self.feels_lbl = tk.Label(
            self.current_card,
            text="Feels like: --°C",
            font=("Segoe UI", 10),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD
        )
        self.feels_lbl.pack(anchor=tk.W, pady=(0, 10))

        # Local Time & Date
        self.time_lbl = tk.Label(
            self.current_card,
            text="As of: --:--",
            font=("Segoe UI", 9, "italic"),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD
        )
        self.time_lbl.pack(anchor=tk.W)

        # Left Side - Card 2: Details Grid Card (Humidity, Wind, UV, AQI)
        self.details_card = tk.Frame(self.left_column, bg=COLOR_CARD, padx=20, pady=18)
        self.details_card.pack(fill=tk.X)

        self.details_card.columnconfigure(0, weight=1)
        self.details_card.columnconfigure(1, weight=1)

        # Detail Boxes
        self.detail_humidity = self.create_detail_box(self.details_card, 0, 0, "💦 HUMIDITY", "-- %")
        self.detail_wind = self.create_detail_box(self.details_card, 0, 1, "💨 WIND", "-- km/h")
        self.detail_uv = self.create_detail_box(self.details_card, 1, 0, "☀️ UV INDEX", "--")
        self.detail_aqi = self.create_detail_box(self.details_card, 1, 1, "🍃 AIR QUALITY", "--")

        # RIGHT SIDE: 3-Day Forecast Column
        self.right_column = tk.Frame(self.dashboard_frame, bg=COLOR_CARD, padx=20, pady=18)
        self.right_column.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self.forecast_title = tk.Label(
            self.right_column,
            text="📅 3-DAY FORECAST",
            font=("Segoe UI", 12, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD
        )
        self.forecast_title.pack(anchor=tk.W, pady=(0, 15))

        # Containers for each of the 3 days
        self.day_frames = []
        for i in range(3):
            day_f = tk.Frame(self.right_column, bg=COLOR_CARD_INNER, padx=12, pady=12)
            day_f.pack(fill=tk.X, pady=(0, 10))
            self.day_frames.append(day_f)
            
            # Setup widgets inside day frame
            day_f.lbl_date = tk.Label(day_f, text="--", font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT_PRIMARY, bg=COLOR_CARD_INNER)
            day_f.lbl_date.pack(anchor=tk.W)

            day_f.bottom_row = tk.Frame(day_f, bg=COLOR_CARD_INNER)
            day_f.bottom_row.pack(fill=tk.X, pady=(5, 0))

            day_f.lbl_icon = tk.Label(day_f.bottom_row, bg=COLOR_CARD_INNER)
            day_f.lbl_icon.pack(side=tk.LEFT)

            day_f.lbl_cond = tk.Label(day_f.bottom_row, text="--", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD_INNER)
            day_f.lbl_cond.pack(side=tk.LEFT, padx=10)

            day_f.lbl_temp = tk.Label(day_f.bottom_row, text="-- / --", font=("Segoe UI", 10, "bold"), fg=COLOR_ACCENT, bg=COLOR_CARD_INNER)
            day_f.lbl_temp.pack(side=tk.RIGHT)

        # ----------------- 4. Hourly Forecast horizontal display -----------------
        self.hourly_frame = tk.Frame(self.main_container, bg=COLOR_CARD, padx=20, pady=15)
        self.hourly_frame.pack(fill=tk.X, pady=(15, 0))

        self.hourly_title = tk.Label(
            self.hourly_frame,
            text="⏰ HOURLY FORECAST (Next 8 Hours)",
            font=("Segoe UI", 11, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD
        )
        self.hourly_title.pack(anchor=tk.W, pady=(0, 10))

        # Horizontal Scroll Container
        self.hourly_scroll_frame = tk.Frame(self.hourly_frame, bg=COLOR_CARD)
        self.hourly_scroll_frame.pack(fill=tk.X)
        
        self.hourly_cards = []
        for i in range(8):
            card = tk.Frame(self.hourly_scroll_frame, bg=COLOR_CARD_INNER, padx=10, pady=8, width=80)
            card.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 8 if i < 7 else 0))
            
            card.lbl_time = tk.Label(card, text="--:--", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_PRIMARY, bg=COLOR_CARD_INNER)
            card.lbl_time.pack()

            card.lbl_icon = tk.Label(card, bg=COLOR_CARD_INNER)
            card.lbl_icon.pack(pady=4)

            card.lbl_temp = tk.Label(card, text="--°", font=("Segoe UI", 10, "bold"), fg=COLOR_ACCENT, bg=COLOR_CARD_INNER)
            card.lbl_temp.pack()
            self.hourly_cards.append(card)

    def create_detail_box(self, parent, r, c, title, value):
        """
        Creates a custom detail layout box inside the grid.
        """
        box = tk.Frame(parent, bg=COLOR_CARD_INNER, padx=12, pady=10)
        box.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
        
        lbl_title = tk.Label(
            box,
            text=title,
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD_INNER
        )
        lbl_title.pack(anchor=tk.W)

        lbl_val = tk.Label(
            box,
            text=value,
            font=("Segoe UI", 13, "bold"),
            fg=COLOR_TEXT_PRIMARY,
            bg=COLOR_CARD_INNER
        )
        lbl_val.pack(anchor=tk.W, pady=(4, 0))

        return lbl_val

    def set_status(self, text, color=COLOR_TEXT_MUTED):
        """
        Sets the status bar text and color.
        """
        self.status_lbl.configure(text=text, fg=color)

    def toggle_unit(self):
        """
        Toggles the temperature unit between C and F and refreshes the display.
        """
        if self.unit == "C":
            self.unit = "F"
            self.unit_btn.configure(text="°F")
        else:
            self.unit = "C"
            self.unit_btn.configure(text="°C")
            
        if self.weather_data:
            self.update_ui()

    def trigger_search(self):
        """
        Triggers a location query based on user entry.
        """
        location = self.location_entry.get().strip()
        if not location:
            messagebox.showwarning("Warning", "Please enter a location.")
            return
        self.fetch_weather_async(location)

    def auto_detect_location(self):
        """
        Performs IP-based geolocation and fetches local weather asynchronously.
        """
        self.set_status("Detecting your location...")
        
        def job():
            try:
                r = requests.get(IP_GEOLOCATION_URL, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") == "success":
                        city = data.get("city")
                        lat = data.get("lat")
                        lon = data.get("lon")
                        
                        # Set search bar to detected city
                        self.root.after(0, lambda: self.location_entry.delete(0, tk.END))
                        self.root.after(0, lambda: self.location_entry.insert(0, city))
                        
                        # Query weather by coordinates for exact mapping
                        coords = f"{lat},{lon}"
                        self.fetch_weather_async(coords)
                        return
                
                # Geolocation failed, fallback to default search
                self.root.after(0, lambda: self.set_status("Could not auto-detect location. Defaulting to London.", COLOR_WARN))
                self.fetch_weather_async("London")
            except Exception as e:
                self.root.after(0, lambda: self.set_status(f"Location detection error: {e}. Defaulting to London.", COLOR_WARN))
                self.fetch_weather_async("London")

        threading.Thread(target=job, daemon=True).start()

    def fetch_weather_async(self, location):
        """
        Initiates a background thread to fetch forecast weather data.
        """
        self.set_status("Fetching weather data...")
        self.search_btn.configure(state=tk.DISABLED)
        self.detect_btn.configure(state=tk.DISABLED)

        def job():
            params = {
                "key": self.api_key,
                "q": location,
                "days": 3,
                "aqi": "yes"
            }
            try:
                response = requests.get(BASE_URL, params=params, timeout=10)
                if response.status_code == 200:
                    self.weather_data = response.json()
                    self.root.after(0, self.update_ui)
                    self.root.after(0, lambda: self.set_status("Data updated successfully.", COLOR_SUCCESS))
                else:
                    try:
                        err_msg = response.json().get("error", {}).get("message", "Unknown error")
                    except Exception:
                        err_msg = f"Server returned code {response.status_code}"
                    self.root.after(0, lambda: self.set_status(f"Error: {err_msg}", COLOR_ERROR))
                    self.root.after(0, lambda: messagebox.showerror("Weather API Error", err_msg))
            except Exception as e:
                self.root.after(0, lambda: self.set_status(f"Network error: {e}", COLOR_ERROR))
                self.root.after(0, lambda: messagebox.showerror("Network Error", "Could not connect to weather service."))
            finally:
                self.root.after(0, lambda: self.search_btn.configure(state=tk.NORMAL))
                self.root.after(0, lambda: self.detect_btn.configure(state=tk.NORMAL))

        threading.Thread(target=job, daemon=True).start()

    def get_weather_icon(self, icon_url, size=(64, 64)):
        """
        Fetches an icon from WeatherAPI.com, resizes it, and caches it.
        Uses a thread-safe download if it's a new icon. Returns PhotoImage.
        """
        if not icon_url:
            return None
            
        full_url = "https:" + icon_url if icon_url.startswith("//") else icon_url
        cache_key = (full_url, size)
        
        # Return cached image if exists
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]

        # Download synchronously since this helper is called during UI updates 
        # (icons are small files, but to prevent lags we wrap it in try/except)
        try:
            r = requests.get(full_url, timeout=5)
            if r.status_code == 200:
                img = Image.open(io.BytesIO(r.content))
                img = img.resize(size, IMG_FILTER)
                photo = ImageTk.PhotoImage(img)
                self.icon_cache[cache_key] = photo
                return photo
        except Exception:
            pass
            
        return None

    def update_ui(self):
        """
        Updates all GUI widgets with the current state of self.weather_data.
        """
        if not self.weather_data:
            return

        # 1. Parse Location
        loc = self.weather_data.get("location", {})
        city = loc.get("name", "Unknown")
        region = loc.get("region", "")
        country = loc.get("country", "")
        local_time_str = loc.get("localtime", "")
        
        # Display Location
        self.city_lbl.configure(text=city)
        region_text = f"{region}, {country}" if region else country
        self.region_lbl.configure(text=region_text)

        # Format Date
        try:
            dt = datetime.strptime(local_time_str, "%Y-%m-%d %H:%M")
            date_formatted = dt.strftime("%A, %b %d, %Y  •  %I:%M %p")
            self.time_lbl.configure(text=f"Local Time: {date_formatted}")
        except Exception:
            self.time_lbl.configure(text=f"Local Time: {local_time_str}")

        # 2. Parse Current Weather
        current = self.weather_data.get("current", {})
        temp_c = current.get("temp_c", 0.0)
        temp_f = current.get("temp_f", 0.0)
        feelslike_c = current.get("feelslike_c", 0.0)
        feelslike_f = current.get("feelslike_f", 0.0)
        
        humidity = current.get("humidity", 0)
        wind_kph = current.get("wind_kph", 0.0)
        wind_mph = current.get("wind_mph", 0.0)
        wind_dir = current.get("wind_dir", "")
        uv = current.get("uv", 0.0)
        
        cond = current.get("condition", {})
        cond_text = cond.get("text", "")
        cond_icon_url = cond.get("icon", "")

        # Set main weather icon
        photo_main = self.get_weather_icon(cond_icon_url, (80, 80))
        if photo_main:
            self.icon_lbl.configure(image=photo_main)
            self.icon_lbl.image = photo_main  # Keep reference
        else:
            self.icon_lbl.configure(image="")

        # Set values based on C/F Unit
        if self.unit == "C":
            self.temp_lbl.configure(text=f"{temp_c:.1f}°C")
            self.feels_lbl.configure(text=f"Feels like: {feelslike_c:.1f}°C")
            self.detail_wind.configure(text=f"{wind_kph:.1f} km/h ({wind_dir})")
        else:
            self.temp_lbl.configure(text=f"{temp_f:.1f}°F")
            self.feels_lbl.configure(text=f"Feels like: {feelslike_f:.1f}°F")
            self.detail_wind.configure(text=f"{wind_mph:.1f} mph ({wind_dir})")

        self.condition_lbl.configure(text=cond_text)
        self.detail_humidity.configure(text=f"{humidity} %")
        
        # UV Index description
        uv_desc = "Low"
        if uv > 2: uv_desc = "Mod"
        if uv > 5: uv_desc = "High"
        if uv > 7: uv_desc = "Very High"
        self.detail_uv.configure(text=f"{uv} ({uv_desc})")

        # AQI
        aqi_val = "--"
        aqi_info = current.get("air_quality", {})
        if aqi_info:
            epa_idx = aqi_info.get("us-epa-index", 0)
            epa_map = {
                1: "Good",
                2: "Moderate",
                3: "Sensitive",
                4: "Unhealthy",
                5: "V. Unhealthy",
                6: "Hazardous"
            }
            aqi_val = f"{epa_idx} - {epa_map.get(epa_idx, 'Unknown')}"
        self.detail_aqi.configure(text=aqi_val)

        # 3. Parse Daily Forecast (3 Days)
        forecast = self.weather_data.get("forecast", {})
        forecastdays = forecast.get("forecastday", [])
        
        for idx, day_f in enumerate(self.day_frames):
            if idx >= len(forecastdays):
                day_f.pack_forget()
                continue
            
            day_f.pack(fill=tk.X, pady=(0, 10))
            f_day = forecastdays[idx]
            date_str = f_day.get("date", "")
            
            # Format day name
            try:
                day_dt = datetime.strptime(date_str, "%Y-%m-%d")
                if idx == 0:
                    day_name = "Today"
                else:
                    day_name = day_dt.strftime("%A, %b %d")
            except Exception:
                day_name = date_str
                
            day_f.lbl_date.configure(text=day_name)
            
            # Day weather stats
            day_details = f_day.get("day", {})
            max_c = day_details.get("maxtemp_c", 0.0)
            min_c = day_details.get("mintemp_c", 0.0)
            max_f = day_details.get("maxtemp_f", 0.0)
            min_f = day_details.get("mintemp_f", 0.0)
            
            day_cond = day_details.get("condition", {})
            day_cond_text = day_cond.get("text", "")
            day_icon_url = day_cond.get("icon", "")
            
            # Weather Icon
            day_photo = self.get_weather_icon(day_icon_url, (40, 40))
            if day_photo:
                day_f.lbl_icon.configure(image=day_photo)
                day_f.lbl_icon.image = day_photo
            else:
                day_f.lbl_icon.configure(image="")
                
            # Condition summary
            day_f.lbl_cond.configure(text=day_cond_text)
            
            # Temps
            if self.unit == "C":
                day_f.lbl_temp.configure(text=f"{max_c:.0f}° / {min_c:.0f}°")
            else:
                day_f.lbl_temp.configure(text=f"{max_f:.0f}° / {min_f:.0f}°")

        # 4. Parse Hourly Forecast (Next 8 Hours)
        # We need to find current hour index in forecastday[0]['hour']
        # Let's extract hour lists
        today_hours = forecastdays[0].get("hour", [])
        tomorrow_hours = forecastdays[1].get("hour", []) if len(forecastdays) > 1 else []
        combined_hours = today_hours + tomorrow_hours
        
        # Find index matching current time or next hour
        current_epoch = current.get("last_updated_epoch", datetime.now().timestamp())
        
        start_hour_idx = 0
        for hour_idx, hour_data in enumerate(combined_hours):
            if hour_data.get("time_epoch", 0) >= current_epoch:
                start_hour_idx = hour_idx
                break
                
        # Fill the 8 hourly cards starting from start_hour_idx
        for idx, card in enumerate(self.hourly_cards):
            target_idx = start_hour_idx + idx
            if target_idx >= len(combined_hours):
                card.pack_forget()
                continue
                
            card.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 8 if idx < 7 else 0))
            h_data = combined_hours[target_idx]
            
            h_time_str = h_data.get("time", "")
            h_temp_c = h_data.get("temp_c", 0.0)
            h_temp_f = h_data.get("temp_f", 0.0)
            h_cond = h_data.get("condition", {})
            h_icon_url = h_cond.get("icon", "")
            
            # Format time (e.g. "15:00" -> "3 PM")
            try:
                h_dt = datetime.strptime(h_time_str, "%Y-%m-%d %H:%M")
                formatted_time = h_dt.strftime("%I %p").lstrip('0')
            except Exception:
                formatted_time = h_time_str.split(" ")[-1]
                
            card.lbl_time.configure(text=formatted_time)
            
            # Icon
            h_photo = self.get_weather_icon(h_icon_url, (36, 36))
            if h_photo:
                card.lbl_icon.configure(image=h_photo)
                card.lbl_icon.image = h_photo
            else:
                card.lbl_icon.configure(image="")
                
            # Temp
            if self.unit == "C":
                card.lbl_temp.configure(text=f"{h_temp_c:.0f}°")
            else:
                card.lbl_temp.configure(text=f"{h_temp_f:.0f}°")


if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherAppGUI(root)
    root.mainloop()
