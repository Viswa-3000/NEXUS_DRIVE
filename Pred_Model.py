import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
import joblib

# Load dataset
df = pd.read_csv("TrafficVolumeData.csv")

# Select features and target
rain = df.iloc[:, 9].values.reshape(-1, 1)   # independent variable (2D)
traffic = df.iloc[:, 14].values              # dependent variable (1D)

# Avoid division by zero
base = traffic.min() if traffic.min() != 0 else 1
factor = traffic / base

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    rain, factor, test_size=0.2, random_state=42
)

# Train model
model = LinearRegression()
model.fit(X_train, y_train)

# Print results
print("Model Coefficients:", model.coef_)
print("Intercept:", model.intercept_)
print("R² Score:", model.score(X_test, y_test))

# Save model
joblib.dump(model, "rain_traffic_model.pkl")
