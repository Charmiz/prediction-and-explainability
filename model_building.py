# -*- coding: utf-8 -*-
"""model_building.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1-DytHSOjUrdbj5qIlR6QXUHXieoW2rO3
"""

!pip install pmdarima prophet

import warnings
from statsmodels.tools.sm_exceptions import ConvergenceWarning

warnings.simplefilter("ignore", category=FutureWarning)  # Ignore FutureWarnings
warnings.simplefilter("ignore", category=ConvergenceWarning)  # Ignore ConvergenceWarnings

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, classification_report, accuracy_score
from statsmodels.tsa.arima.model import ARIMA
import statsmodels.api as sm
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.stattools import adfuller
from sklearn.ensemble import RandomForestClassifier
from pmdarima import auto_arima
from statsmodels.tsa.statespace.sarimax import SARIMAX
from prophet import Prophet
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier

# Load forecasting data
daily_data = pd.read_csv("daily_aggregated_features.csv", parse_dates=["date"], index_col="date")

# Ensure the index has a proper frequency
daily_data = daily_data.asfreq('D')

# Fill missing values if any (optional)
daily_data = daily_data.ffill()

"""**KPI FORECASTING**

***ARIMA***
"""

# Display data
daily_data.head()

plt.figure(figsize=(12, 6))
plt.plot(daily_data['transaction_success_rate'], label='Transaction Success Rate')
plt.title('Transaction Success Rate Over Time')
plt.xlabel('Date')
plt.ylabel('Success Rate')
plt.legend()
plt.show()

# Perform ADF Test

kpi_column = 'transaction_success_rate'
data = daily_data[kpi_column].dropna()

result = adfuller(data)

print(f'ADF Statistic: {result[0]}')
print(f'p-value: {result[1]}')
print('Critical Values:')
for key, value in result[4].items():
    print(f'   {key}: {value}')

if result[1] <= 0.05:
    print("Data is stationary (p ≤ 0.05)")
else:
    print("Data is NOT stationary (p > 0.05)")

# Select KPI column for forecasting
kpi_series = daily_data['transaction_success_rate'].dropna()
kpi_series = kpi_series.squeeze()

# Plot ACF & PACF
fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# Dynamically determine lags (max 50% of sample size)
max_lag = min(len(kpi_series) // 2, 20)
print(max_lag)

# ACF plot
plot_acf(kpi_series, lags=max_lag, ax=axes[0])
axes[0].set_title("Autocorrelation Function (ACF)")

# PACF plot
plot_pacf(kpi_series, lags=max_lag, ax=axes[1])
axes[1].set_title("Partial Autocorrelation Function (PACF)")

plt.show()

# Define the ARIMA model
arima_model = ARIMA(daily_data['transaction_success_rate'], order=(1, 0, 0))

# Fit the model
model_fit = arima_model.fit()

forecast = model_fit.forecast(steps=30)

# Split the data into train and test
train_size = int(len(daily_data) * 0.8)
train, test = daily_data[:train_size], daily_data[train_size:]

# Fit the ARIMA model on the training dataset
arima_model_train = ARIMA(train['transaction_success_rate'], order=(0, 0, 0))
arima_model_train_fit = arima_model_train.fit()

# Forecast on the test dataset
arima_test_forecast = arima_model_train_fit.get_forecast(steps=len(test))
arima_test_forecast_series = pd.Series(arima_test_forecast.predicted_mean, index=test.index)


# Calculate the mean squared error
mse = mean_squared_error(test['transaction_success_rate'], arima_test_forecast_series)
rmse = mse**0.5
mae = mean_absolute_error(test['transaction_success_rate'], arima_test_forecast_series)
r2 = r2_score(test['transaction_success_rate'], arima_test_forecast_series)


print(f"ARIMA Model Performance:")
print(f"RMSE: {rmse:.4f}")
print(f"MSE: {mse:.4f}")
print(f"MAE: {mae:.4f}")
print(f"R2: {r2:.4f}")

# Plot Actual vs Forecasted
plt.figure(figsize=(14,7))
plt.plot(train['transaction_success_rate'], label='Training Data')
plt.plot(test['transaction_success_rate'], label='Actual Data', color='orange')
plt.plot(arima_test_forecast_series, label='Forecasted Data', color='green')
plt.fill_between(test.index,
                 arima_test_forecast.conf_int().iloc[:, 0],
                 arima_test_forecast.conf_int().iloc[:, 1],
                 color='k', alpha=.15)
plt.title('ARIMA Model Evaluation')
plt.xlabel('Date')
plt.ylabel('Transaction Success Rate')
plt.legend()
plt.show()

"""***SARIMA***"""

# Decompose the Time Series to check seasonality
decomposition = sm.tsa.seasonal_decompose(daily_data["transaction_success_rate"], model="additive", period=7)
decomposition.plot()
plt.show()

# Auto-ARIMA to find optimal (p, d, q) and (P, D, Q, s)
auto_model = auto_arima(daily_data["transaction_success_rate"], seasonal=True, m=7, trace=True, stepwise=True)
print(auto_model.summary())

# Extract best parameters
best_order = auto_model.order
best_seasonal_order = auto_model.seasonal_order
print(f"Best Order: {best_order}")
print(f"Best Seasonal Order: {best_seasonal_order}")

# Split Data (Train: 80%, Test: 20%)
train_size = int(len(daily_data) * 0.8)
train, test = daily_data[:train_size], daily_data[train_size:]

# Train SARIMA Model
sarima_model = SARIMAX(train["transaction_success_rate"], order=best_order, seasonal_order=best_seasonal_order)
sarima_fit = sarima_model.fit()

# Forecast
forecast_steps = len(test)
sarima_forecast = sarima_fit.forecast(steps=forecast_steps)

# Calculate MSE & RMSE
mse = mean_squared_error(test["transaction_success_rate"], sarima_forecast)
rmse = np.sqrt(mse)
mae = mean_absolute_error(test['transaction_success_rate'], sarima_forecast)
r2 = r2_score(test['transaction_success_rate'], sarima_forecast)

print(f"SARIMA RMSE: {rmse:.4f}")
print(f"SARIMA MSE: {mse:.4f}")
print(f"SARIMA MAE: {mae:.4f}")
print(f"SARIMA R2: {r2:.4f}")

# Plot Actual vs. Forecasted
plt.figure(figsize=(12,6))
plt.plot(train.index, train["transaction_success_rate"], label="Training Data", color="blue")
plt.plot(test.index, test["transaction_success_rate"], label="Actual Data", color="orange")
plt.plot(test.index, sarima_forecast, label="SARIMA Forecast", color="green")
plt.fill_between(test.index, sarima_forecast - rmse, sarima_forecast + rmse, color="gray", alpha=0.2)
plt.legend()
plt.title("SARIMA Model Forecasting")
plt.show()

"""***Prophet***"""

# Prepare data for Prophet
prophet_df = daily_data.reset_index().rename(columns={"date": "ds", "transaction_success_rate": "y"})

# Initialize and fit the Prophet model
prophet_model = Prophet(seasonality_mode='multiplicative')
prophet_model.fit(prophet_df)

# Create a dataframe for future predictions (next 30 days)
future = prophet_model.make_future_dataframe(periods=30)

# Generate forecast
forecast = prophet_model.predict(future)

# Evaluate performance
actual = prophet_df['y'].iloc[-30:].values
predicted = forecast['yhat'].iloc[-30:].values

mse = mean_squared_error(actual, predicted)
mae = mean_absolute_error(actual, predicted)
rmse = mse ** 0.5
r2 = r2_score(actual, predicted)

print(f"Prophet RMSE: {rmse:.4f}")
print(f"Prophet MAE: {mae:.4f}")
print(f"Prophet mse: {mse:.4f}")
print(f"Prophet r2: {r2:.4f}")

# Plot results
fig, ax = plt.subplots(figsize=(12, 6))
prophet_model.plot(forecast, ax=ax)
plt.title("Prophet Model Forecasting")
plt.show()

# Initialize Prophet model with custom seasonality
from prophet.make_holidays import make_holidays_df
holidays = pd.DataFrame({
    'holiday': 'big_sale_day',
    'ds': pd.to_datetime(['2025-02-14', '2025-12-25']),
    'lower_window': 0,
    'upper_window': 1
})
#prophet_model = Prophet(seasonality_mode='multiplicative',holidays=holidays,daily_seasonality=True)
prophet_model = Prophet(seasonality_mode='multiplicative',daily_seasonality=True)

prophet_model.fit(prophet_df)

future = prophet_model.make_future_dataframe(periods=30)
forecast = prophet_model.predict(future)

# Evaluate performance
actual = prophet_df['y'].iloc[-30:].values
predicted = forecast['yhat'].iloc[-30:].values

mse = mean_squared_error(actual, predicted)
mae = mean_absolute_error(actual, predicted)
rmse = mse ** 0.5
r2 = r2_score(actual, predicted)

print(f"Prophet RMSE: {rmse:.4f}")
print(f"Prophet MAE: {mae:.4f}")
print(f"Prophet MSE: {mse:.4f}")
print(f"Prophet R2: {mse:.4f}")

# Plot results
fig, ax = plt.subplots(figsize=(12, 6))
prophet_model.plot(forecast, ax=ax)
plt.title("Prophet Model Forecasting")
plt.show()

"""***Random Forest***"""

# Load supervised learning data
supervised_data = pd.read_csv("final_feature_engineered_data.csv")

supervised_data.dropna(subset=["timestamp", "cpu_usage", "memory_usage"], inplace=True)

# Create a degradation flag (label)
threshold = supervised_data['transaction_success_rate'].mean() - supervised_data['transaction_success_rate'].std()
supervised_data['degradation_flag'] = supervised_data['transaction_success_rate'].apply(lambda x: 1 if x < threshold else 0)

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(supervised_data[features], supervised_data[target], test_size=0.2, random_state=42, stratify=supervised_data[target])

# Train Random Forest model
rf_model = RandomForestClassifier( n_estimators=100, random_state=42, class_weight="balanced")
rf_model.fit(X_train, y_train)

# Predictions
y_pred = rf_model.predict(X_test)

# Evaluation
print("Classification Report:\n", classification_report(y_test, y_pred))
print("Accuracy:", accuracy_score(y_test, y_pred))
print("R2 Score:", r2_score(y_test,y_pred))


mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, y_pred)

print(f"RF RMSE: {rmse:.4f}")
print(f"RF MAE: {mae:.4f}")
print(f"RF MSE: {mse:.4f}")
print(f"RF R2: {r2:.4f}")

"""***XGBoost***"""

# Select Features and Target
features = ['cpu_usage', 'memory_usage', 'response_time', 'error_rate']
target = 'degradation_flag'

# Train-test split (80-20)
X_train, X_test, y_train, y_test = train_test_split(supervised_data[features], supervised_data[target], test_size=0.2, random_state=42)

# Initialize XGBoost Model (Choose Regression or Classification)
if supervised_data[target].nunique() > 2:
    model = xgb.XGBRegressor(objective="reg:squarederror", n_estimators=100, learning_rate=0.1, random_state=42)
    classification = False
else:
    model = xgb.XGBClassifier(objective="binary:logistic", n_estimators=100, learning_rate=0.1, random_state=42)
    classification = True

# Train the Model
model.fit(X_train, y_train)

# Make Predictions
y_pred = model.predict(X_test)

# Evaluate Model
if classification:
    print("\nClassification Report:\n", classification_report(y_test, y_pred))
else:
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    print(f"\nXGBoost Regression RMSE: {rmse:.4f}")


# Apply SMOTE to balance the dataset
smote = SMOTE(sampling_strategy='auto', random_state=42)
X_resampled, y_resampled = smote.fit_resample(supervised_data[features], supervised_data[target])

# Check class distribution after balancing
print("Class distribution after SMOTE:")
print(y_resampled.value_counts())

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X_resampled, y_resampled, test_size=0.2, random_state=42)

# Train XGBoost model
xgb_model = XGBClassifier(use_label_encoder=False, eval_metric='logloss')
xgb_model.fit(X_train, y_train)

# Predict and evaluate
y_pred = xgb_model.predict(X_test)
print("Classification Report:")
print(classification_report(y_test, y_pred))

mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, y_pred)

print(f"XGBoost RMSE: {rmse:.4f}")
print(f"XGBoost MAE: {mae:.4f}")
print(f"XGBoost MSE: {mse:.4f}")
print(f"XGBoost R2: {r2:.4f}")

# Feature Importance using SHAP
explainer = shap.Explainer(model)
shap_values = explainer(X_test)

# Plot Feature Importance
shap.summary_plot(shap_values, X_test)

# Bar Plot: Shows mean absolute SHAP values per feature
shap.summary_plot(shap_values, X_test, plot_type="bar")

# Force Plot: Shows local impact on a single prediction
shap.initjs()
shap.force_plot(explainer.expected_value, shap_values.values[0], X_test.iloc[0])

import pickle
import joblib
from google.colab import drive

# Mount Google Drive
drive.mount('/content/drive')

# Save trained model to Google Drive
joblib.dump(xgb_model, '/content/drive/MyDrive/kpi_degradation_rf_model.pkl')

# Save the best model
with open('kpi_degradation_rf_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)

print("Model saved to Google Drive successfully!")