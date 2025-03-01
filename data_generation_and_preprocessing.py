# -*- coding: utf-8 -*-
"""data_generation_and_preprocessing.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1SSavgByCADBWuFMFWrIi40VIiJuDfQAR
"""

import random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# Set random seed for reproducibility
random.seed(42)
np.random.seed(42)

# Simulation parameters
num_days = 30
interval_minutes = 5  # Data collection interval
num_transactions_per_interval = 20  # Transactions per 5-minute interval

# Generate datetime range with 5-minute intervals
date_range = [datetime.now() - timedelta(minutes=x) for x in range(0, num_days * 24 * 60, interval_minutes)]

# Simulate Business KPI Data with 5-minute granularity
def generate_business_kpi_data():
    data = []
    for date in date_range:
        for _ in range(num_transactions_per_interval):
            transaction_id = f"TX{random.randint(100000, 999999)}"
            amount = random.choice([round(random.uniform(10, 500), 2), None])  # Some missing values
            payment_status = random.choices(['Success', 'Failure', None], weights=[0.88, 0.1, 0.02])[0]  # Some missing statuses
            kpi = {
                'timestamp': random.choice([date, None]),  # Some missing timestamps
                'transaction_id': transaction_id,
                'amount': amount,
                'payment_status': payment_status,
            }
            # Introduce duplicates occasionally
            if random.random() < 0.01:
                data.append(kpi)
            data.append(kpi)
    df = pd.DataFrame(data)

    # Calculate transaction success rate for each 5-minute interval
    df['interval'] = df['timestamp'].dt.floor('5T')
    interval_kpi = df.groupby('interval').apply(lambda x: pd.Series({
        'transaction_success_rate': x['payment_status'].value_counts(normalize=True).get('Success', 0) * 100,
        'total_transactions': len(x),
    })).reset_index()
    return df, interval_kpi

# Simulate IT Metrics Data with 5-minute granularity
def generate_it_metrics_data():
    data = []
    for date in date_range:
        cpu_usage = random.choice([round(random.uniform(10, 90), 2), None])  # Some missing values
        memory_usage = random.choice([round(random.uniform(100, 1000), 2), None])  # Some missing values
        response_time = round(random.uniform(0.1, 5.0), 2)
        error_rate = round(random.uniform(0, 0.2), 2)
        metrics = {
            'timestamp': random.choice([date, None]),  # Some missing timestamps
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'response_time': response_time,
            'error_rate': error_rate,
        }

        # Introduce duplicates occasionally
        if random.random() < 0.01:
            data.append(metrics)
        data.append(metrics)
    df = pd.DataFrame(data)
    df['interval'] = df['timestamp'].dt.floor('5min')
    return df

business_kpi_df, interval_kpi_df = generate_business_kpi_data()
it_metrics_df = generate_it_metrics_data()

business_kpi_df.to_csv('raw_business_kpi_data.csv', index=False)
interval_kpi_df.to_csv('raw_interval_business_kpi_data.csv', index=False)
it_metrics_df.to_csv('raw_it_metrics_data.csv', index=False)

# Handling missing values
business_kpi_df['timestamp'].ffill(inplace=True)
business_kpi_df['amount'] = business_kpi_df['amount'].fillna(business_kpi_df['amount'].median())
business_kpi_df['payment_status'] = business_kpi_df['payment_status'].fillna('Unknown')

# Removing duplicates
business_kpi_df.drop_duplicates(inplace=True)

# Handling missing values
it_metrics_df['timestamp'].ffill(inplace=True)
it_metrics_df['cpu_usage'] = it_metrics_df['cpu_usage'].fillna(it_metrics_df['cpu_usage'].mean())
it_metrics_df['memory_usage'] = it_metrics_df['memory_usage'].fillna(it_metrics_df['memory_usage'].mean())


# Removing duplicates
it_metrics_df.drop_duplicates(inplace=True)

# Handling outliers (using interquartile range method)
q1 = it_metrics_df[['cpu_usage', 'memory_usage', 'response_time', 'error_rate']].quantile(0.25)
q3 = it_metrics_df[['cpu_usage', 'memory_usage', 'response_time', 'error_rate']].quantile(0.75)
iqr = q3 - q1
lower_bound = q1 - 1.5 * iqr
upper_bound = q3 + 1.5 * iqr

for column in ['cpu_usage', 'memory_usage', 'response_time', 'error_rate']:
    it_metrics_df[column] = np.where(
        (it_metrics_df[column] < lower_bound[column]) | (it_metrics_df[column] > upper_bound[column]),
        np.nan, it_metrics_df[column]
    )

# Fill outliers with mean values
it_metrics_df['cpu_usage'].fillna(it_metrics_df['cpu_usage'].mean(), inplace=True)
it_metrics_df['memory_usage'].fillna(it_metrics_df['memory_usage'].mean(), inplace=True)
it_metrics_df['response_time'].fillna(it_metrics_df['response_time'].mean(), inplace=True)
it_metrics_df['error_rate'].fillna(it_metrics_df['error_rate'].mean(), inplace=True)

# Align datasets by timestamps (5-minute granularity)
def align_datasets(interval_kpi_df, it_metrics_df):
    interval_metrics = it_metrics_df.groupby('interval').mean().reset_index()
    aligned_df = pd.merge(interval_kpi_df, interval_metrics, on='interval', how='outer')
    return aligned_df

aligned_df = align_datasets(interval_kpi_df, it_metrics_df)

# Find total rows and columns
rows,columns = aligned_df.shape
print("Total Rows:", rows)
print("Total Columns:", columns)

# Perform Exploratory Data Analysis (EDA)

# Basic statistics
print("Business KPI Data Statistics:")
print(business_kpi_df.describe(include='all'))

print("IT Metrics Data Statistics:")
print(it_metrics_df.describe(include='all'))

print("Aligned Data Statistics:")
print(aligned_df.describe(include='all'))

# Plot transaction success rate over time
plt.figure(figsize=(10, 6))
sns.lineplot(data=aligned_df, x='interval', y='transaction_success_rate', label='Transaction Success Rate')
plt.title('Transaction Success Rate Over Time')
plt.xlabel('Time Interval')
plt.ylabel('Transaction Success Rate (%)')
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.show()

# Correlation heatmap for IT metrics
plt.figure(figsize=(8, 6))
sns.heatmap(it_metrics_df[['cpu_usage', 'memory_usage', 'response_time', 'error_rate']].corr(), annot=True, cmap='coolwarm', fmt='.2f')
plt.title('Correlation Heatmap for IT Metrics')
plt.tight_layout()
plt.show()

# Pairplot for IT metrics
sns.pairplot(it_metrics_df[['cpu_usage', 'memory_usage', 'response_time', 'error_rate']])
plt.suptitle('Pairplot for IT Metrics', y=1.02)
plt.show()

# Transaction amount distribution
plt.figure(figsize=(8, 6))
sns.histplot(business_kpi_df['amount'], bins=30, kde=True, color='blue')
plt.title('Transaction Amount Distribution')
plt.xlabel('Amount')
plt.ylabel('Frequency')
plt.tight_layout()
plt.show()

# Boxplot for IT metrics
plt.figure(figsize=(10, 6))
sns.boxplot(data=it_metrics_df[['cpu_usage', 'memory_usage', 'response_time', 'error_rate']])
plt.title('Boxplot for IT Metrics')
plt.tight_layout()
plt.show()

# Lag Features
def add_lag_features(df, lag_features, lag=1):
    for feature in lag_features:
        df[f'{feature}_lag{lag}'] = df[feature].shift(lag)
    return df

lag_features = ['transaction_success_rate', 'cpu_usage', 'memory_usage', 'response_time', 'error_rate']
aligned_df = add_lag_features(aligned_df, lag_features, lag=1)

# Rolling Window Features
def add_rolling_features(df, rolling_features, window=12):
    for feature in rolling_features:
        df[f'{feature}_rolling_mean'] = df[feature].rolling(window=window).mean()
        df[f'{feature}_rolling_std'] = df[feature].rolling(window=window).std()
    return df

rolling_features = ['transaction_success_rate', 'cpu_usage', 'memory_usage', 'response_time', 'error_rate']
aligned_df = add_rolling_features(aligned_df, rolling_features, window=12)  # 12 intervals = 1 hour

# Interaction Features
aligned_df['cpu_memory_interaction'] = aligned_df['cpu_usage'] * aligned_df['memory_usage']

# Time-Based Features
aligned_df['hour'] = aligned_df['interval'].dt.hour
aligned_df['day_of_week'] = aligned_df['interval'].dt.dayofweek
aligned_df['is_weekend'] = aligned_df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)

# Categorical Encoding
aligned_df['payment_status_encoded'] = aligned_df['transaction_success_rate'].apply(
    lambda x: 1 if x > 90 else 0  # Encode high success rates as 1, others as 0
)

# Anomaly Flags
aligned_df['high_error_rate_flag'] = aligned_df['error_rate'].apply(lambda x: 1 if x > 0.15 else 0)
aligned_df['response_time_spike_flag'] = aligned_df['response_time'].apply(lambda x: 1 if x > 3 else 0)

# Aggregated Features
daily_aggregates = aligned_df.groupby(aligned_df['interval'].dt.date).agg({
    'transaction_success_rate': 'mean',
    'cpu_usage': 'mean',
    'memory_usage': 'mean',
    'response_time': 'mean',
    'error_rate': 'mean'
}).reset_index().rename(columns={'interval': 'date'})

# Save Aggregates
daily_aggregates.to_csv('daily_aggregated_features.csv', index=False)

# Save Final Dataset
aligned_df.to_csv('final_feature_engineered_data.csv', index=False)

print("Feature engineering completed. Final dataset saved.")



# Plot transaction success rate over time
plt.figure(figsize=(10, 6))
sns.lineplot(data=daily_aggregates, x='date', y='transaction_success_rate', label='Transaction Success Rate')
plt.title('Transaction Success Rate Over Time')
plt.xlabel('Time Interval')
plt.ylabel('Transaction Success Rate (%)')
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.show()

df = pd.read_csv("final_feature_engineered_data.csv", index_col="interval", parse_dates=True)

# Display the first few rows of the dataframe to understand its structure
df.head()

# Correlation heatmap for IT metrics
plt.figure(figsize=(8, 6))
sns.heatmap(df[['cpu_usage', 'memory_usage', 'response_time', 'error_rate','transaction_success_rate']].corr(), annot=True, cmap='coolwarm', fmt='.2f')
plt.title('Correlation Heatmap for IT Metrics')
plt.tight_layout()
plt.show()