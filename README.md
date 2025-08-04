# Earthquake and Notification Analytics Dashboard 
This project is a multi-tab Dash application designed to visualize and analyze data related to earthquake events, user silent notifications, and user token statistics. It provides three distinct dashboards for a detailed overview of the system's performance and user engagement. 

## Features 

The application is organized into three main tabs: 

### 1. Users Dashboard (`dashboard_users.py`) 
This dashboard provides analytics on user acquisition and growth for both Android (FCM) and iOS (APNs) platforms. 

* **Total User Counts:** Displays the total number of unique Android and iOS users. 
* **New Users Over Time:** A line chart showing the number of new users acquired over a selected time period.
* **New Users per Period:** A bar chart visualizing new user acquisition per day or hour. 
* **Cumulative User Growth:** A line chart illustrating the cumulative growth of the user base over time. 
* **Filtering:** Data can be filtered by predefined time ranges (e.g., Last 24 hours, Last 7 days) or a custom date range. 
* **Multi-language Support:** English and Spanish languages are supported. 

### 2. Silent Notifications Dashboard (`dashboard_silent.py`) 
This dashboard focuses on analyzing the delivery and performance of silent notifications sent to users. 
* **Notification Map:** A map visualizing the geographical distribution of users who received a silent notification, colored by the delivery delay. 
* **Delay Distribution:** A histogram showing the distribution of notification delivery delays. 
* **Delay vs. Time:** A scatter plot showing the trend of notification delivery delay over time. 
* **Users vs. Time:** A line chart showing the number of users who received silent notifications over time. 
* **Filtering:** Data can be filtered by OS version, specific notification send times, and date ranges. 
* **Multi-language Support:** English and Spanish languages are supported. 

### 3. Events Dashboard (`dashboard_events.py`) 
This dashboard is dedicated to the in-depth analysis of specific earthquake events. 

* **Event Summary:** Displays key information about a selected earthquake, including magnitude, depth, origin time, and description. 
* **Intensity Map:** Visualizes user-reported intensities on a map, along with the event's epicenter. 
* **Intensity vs. Distance:** Plots reported intensities against hypocentral distance and compares it with the Allen (2012) IPE model. 
* **Notification Delay Distribution:** Shows the distribution of alert notification delays for different update numbers and OS versions. 
* **Alert Types:** A stacked bar chart showing the types of alerts (Red, Orange, Green, etc.) sent for each update.
* **S-Wave Arrival Analysis:** A map and a scatter plot analyzing the alert arrival time relative to the S-wave arrival time (S-wave Leadtime). 
* **Filtering:** Users can select a specific `eventid` to analyze, and further filter by update number and OS version. 
* **Caching:** Implements server-side caching with Flask-Caching to speed up data loading for frequently accessed events. 

## Project Structure

* **main.py** # Main application entry point 
* **dashboard_users.py** # Layout and callbacks for the Users tab
* **dashboard_silent.py** # Layout and callbacks for the Silent Notifications tab
* **dashboard_events.py** # Layout and callbacks for the Events tab 
* **config.json.sample** # Sample configuration file

## Setup and Installation 

1. **Clone the repository:** 

```bash 
git clone https://github.com/ATTAC-EEW-in-Central-America/app-view.git 
cd app-view
``` 

2. **Install dependencies:**

```bash 
pip install dash pandas dash-bootstrap-components plotly flask-caching scipy 
``` 
 It is optional the usage of virtual environment. 

3. **Configure the application:** 
4. 
* Rename `config.json.sample` to `config.json`. 
* Update the `config.json` file with the correct paths to your SQLite databases and desired cache folder. 

```json
{ 
 "database_path_tokens": "/path/to/your/tokensDB.db", 
 "database_path_events_silent": "/path/to/your/dashboard.db", 
 "cache_size_days": 30, 
 "cache_folder": "/path/to/your/cache_folder/" 
 } 
 ``` 

* In `dashboard_silent.py`, replace `'your_mapbox_token_here'` with your actual Mapbox access token if you intend to use Mapbox maps. 

4. **Run the application:** 

```bash 
python main.py 
``` 

The application will be available at `http://0.0.0.0:8055` by default. 

## Usage 

* Navigate to `http://<your-server-ip>:8055` in your web browser. 
* Use the tabs at the top to switch between the **Users**, **Silent Notif.**, and **Events** dashboards. 
* Use the dropdowns, date pickers, and other controls within each tab to filter and analyze the data. 
* To view a specific event, you can pass the `eventid` as a URL parameter. For example: `http://<your-server-ip>:8055/?eventid=insi2025ovbm`. This will automatically switch to the "Events" tab and load the data for the specified event.
