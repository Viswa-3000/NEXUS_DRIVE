import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime, timedelta
import folium
import os

# -----------------------------
# CONFIG
# -----------------------------
TRAINING_CSV = r"C:\users\91988\desktop\test\training.csv"
DRIVERS_CSV = r"C:\users\91988\desktop\test\drivers.csv"
COORDS_CSV = r"C:\users\91988\desktop\test\coords.csv"
OUTPUT_FOLDER = r"C:\users\91988\desktop\test\chennai_taxi_output"
FORECAST_DATE = "2024-09-10 18:00"  # YYYY-MM-DD HH:MM
TOTAL_VEHICLES = 400

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
print("Files will be saved in:", OUTPUT_FOLDER)

# -----------------------------
# LOAD DATA
# -----------------------------
train_df = pd.read_csv(TRAINING_CSV)
train_df.columns = [c.strip() for c in train_df.columns]
train_df.rename(columns={
    train_df.columns[0]:"ward_no",
    train_df.columns[1]:"day",
    train_df.columns[2]:"time",
    train_df.columns[3]:"demand_quantised",
    train_df.columns[4]:"demand_level"
}, inplace=True)

coords_df = pd.read_csv(COORDS_CSV)
coords_df.columns = [c.strip() for c in coords_df.columns]

train_df = train_df.merge(coords_df, left_on="ward_no", right_on="ward_name", how="left")
if train_df[['lat','lon']].isna().any().any():
    raise ValueError("Some wards are missing coordinates in coords.csv")

drivers_df = pd.read_csv(DRIVERS_CSV)
drivers_df.columns = [c.strip() for c in drivers_df.columns]
drivers_df["assigned"] = False

# -----------------------------
# FIX DRIVER COORDINATES
# -----------------------------
drivers_df["Latitudes"] = pd.to_numeric(drivers_df["Latitudes"], errors="coerce")
drivers_df["Longitudes"] = pd.to_numeric(drivers_df["Longitudes"], errors="coerce")
drivers_df = drivers_df.dropna(subset=["Latitudes","Longitudes"])

# -----------------------------
# PREPROCESS TIME
# -----------------------------
DAY_TO_IDX = {"sunday":0,"monday":1,"tuesday":2,"wednesday":3,"thursday":4,"friday":5,"saturday":6}
base_sunday = pd.Timestamp("2024-01-07 00:00:00")

def construct_ds(row):
    day_idx = DAY_TO_IDX[row["day"].strip().lower()]
    try:
        t = pd.to_datetime(row["time"], format="%H:%M").time()
    except:
        t = datetime.strptime("00:00","%H:%M").time()
    return base_sunday + timedelta(days=day_idx, hours=t.hour, minutes=t.minute)

train_df["ds"] = train_df.apply(construct_ds, axis=1)
train_df["y"] = train_df["demand_quantised"]

# -----------------------------
# TRAIN PROPHET MODEL PER WARD
# -----------------------------
models = {}
for ward, g in train_df.groupby("ward_no"):
    m = Prophet(weekly_seasonality=True, daily_seasonality=True, yearly_seasonality=False)
    m.add_seasonality(name='hourly', period=24, fourier_order=6)
    m.fit(g[["ds","y"]])
    models[ward] = m

# -----------------------------
# FORECAST FOR TARGET TIMESTAMP
# -----------------------------
target_time = pd.Timestamp(FORECAST_DATE)
pred_list = []

for ward, m in models.items():
    fc = m.predict(pd.DataFrame({"ds":[target_time]}))
    yhat = max(float(fc.loc[0,"yhat"]),0)
    lat = train_df.loc[train_df.ward_no==ward,"lat"].values[0]
    lon = train_df.loc[train_df.ward_no==ward,"lon"].values[0]
    pred_list.append({"ward_no":ward,"yhat":yhat,"lat":lat,"lon":lon})

pred_df = pd.DataFrame(pred_list)
total_demand = pred_df["yhat"].sum()
pred_df["ward_share"] = pred_df["yhat"]/total_demand
pred_df["drivers_to_allocate"] = np.round(pred_df["ward_share"] * TOTAL_VEHICLES).astype(int)
pred_df["demand_level"] = pd.cut(pred_df["yhat"], bins=[-1,33,66,101], labels=["Low","Medium","High"])

# -----------------------------
# ALLOCATE DRIVERS PROPORTIONAL TO DEMAND
# -----------------------------
allocations = []

for idx, row in pred_df.iterrows():
    needed = row["drivers_to_allocate"]
    if needed <= 0:
        continue
    available = drivers_df[~drivers_df.assigned].copy()
    if available.empty:
        print(f"No available drivers for ward {row.ward_no}")
        continue
    available["distance"] = np.sqrt((available["Latitudes"] - row.lat)**2 + (available["Longitudes"] - row.lon)**2)
    nearest_drivers = available.nsmallest(needed,"distance")
    
    for i, driver in nearest_drivers.iterrows():
        allocations.append({
            "Ward no": row.ward_no,
	    "Driver Name": driver["Driver Name"],
	    "Driver ID": driver["Driver ID"],
	    "Contact Number": driver["Phone Number"],
	    "Vehicle Number": driver["Vehicle Number"],
	    "Latitudes": driver["Latitudes"],
   	    "Longitudes": driver["Longitudes"]
    	     })
        drivers_df.loc[driver.name,"assigned"] = True


alloc_df = pd.DataFrame(allocations)
ALLOC_CSV_PATH = os.path.join(OUTPUT_FOLDER,"allocated_list.csv")
alloc_df.to_csv(ALLOC_CSV_PATH,index=False)
print("Saved allocated drivers CSV:", ALLOC_CSV_PATH)

# -----------------------------
# CREATE COLOR-CODED HEATMAP
# -----------------------------
m = folium.Map(location=[13.0827, 80.2707], zoom_start=11)
color_map = {"Low":"green","Medium":"yellow","High":"red"}

for idx, row in pred_df.iterrows():
    folium.CircleMarker(
        location=[row.lat,row.lon],
        radius=15,
        color=color_map.get(row.demand_level,"green"),
        fill=True,
        fill_color=color_map.get(row.demand_level,"green"),
        fill_opacity=0.6,
        popup=f"Ward: {row.ward_no}\nDemand: {row.demand_level}"
    ).add_to(m)

# -----------------------------
# CREATE COLOR-CODED HEATMAP WITH DRIVER LAYERS
# -----------------------------
m = folium.Map(location=[13.0827, 80.2707], zoom_start=11)
color_map = {"Low": "green", "Medium": "yellow", "High": "red"}

# Layer for wards
ward_layer = folium.FeatureGroup(name="Wards").add_to(m)

for idx, row in pred_df.iterrows():
    folium.CircleMarker(
        location=[row.lat, row.lon],
        radius=15,
        color=color_map.get(row.demand_level, "green"),
        fill=True,
        fill_color=color_map.get(row.demand_level, "green"),
        fill_opacity=0.6,
        popup=f"Ward: {row.ward_no}\nDemand: {row.demand_level}"
    ).add_to(ward_layer)

# Layer for drivers
driver_layer = folium.FeatureGroup(name="Drivers").add_to(m)

for _, driver in alloc_df.iterrows():
    folium.CircleMarker(
        location=[driver["Latitudes"], driver["Longitudes"]],
        radius=4,
        color="blue",
        fill=True,
        fill_opacity=0.7,
        popup=f"Driver: {driver['Driver Name']} ({driver['Vehicle Number']})"
    ).add_to(driver_layer)

# Add layer control (toggle button)
folium.LayerControl().add_to(m)

MAP_HTML_PATH = os.path.join(OUTPUT_FOLDER, "chennai_demand_heatmap_colored.html")
m.save(MAP_HTML_PATH)
print("Saved Chennai color-coded heatmap with layers:", MAP_HTML_PATH)
