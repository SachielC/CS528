import os
import pandas as pd
import pymysql
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from google.cloud import storage
import re
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, confusion_matrix
import lightgbm as lgb
from google.cloud import storage
from sklearn.ensemble import RandomForestClassifier
import re
# =========================
# CONFIG (FROM ENV)
# =========================
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
BUCKET_NAME = os.getenv("BUCKET_NAME")

# =========================
# UPLOAD TO GCS
# =========================
def upload_to_gcs(local_file, dest_file=None):
    if dest_file is None:
        dest_file = local_file
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(dest_file)
    blob.upload_from_filename(local_file)
    print(f"Uploaded {local_file} to gs://{BUCKET_NAME}/{dest_file}")

# =========================
# LOAD CLIENT DATA
# =========================
def get_clients_data(conn):
    query = """
    SELECT 
        c.client_id,
        c.gender,
        c.age,
        c.income_range_id,
        ip.client_ip,
        ip.country
    FROM clients c
    LEFT JOIN ips ip ON c.ip_id = ip.ip_id
    """
    df = pd.read_sql(query, conn)
    print(f"Clients data shape: {df.shape}")
    return df

# =========================
# LOAD TOTAL REQUESTS PER CLIENT
# =========================
def get_total_requests(conn):
    query = """
    SELECT client_id, COUNT(*) AS total_requests
    FROM requests
    GROUP BY client_id
    """
    df = pd.read_sql(query, conn)
    return df
def model_ip_to_country(df):
    df_ip = df[['client_ip', 'country']].dropna()
    if df_ip.empty:
        print("No data for IP -> Country model. Skipping...")
        return None

    le_ip = LabelEncoder()
    le_country = LabelEncoder()
    X = le_ip.fit_transform(df_ip['client_ip']).reshape(-1, 1)
    y = le_country.fit_transform(df_ip['country'])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model 1 Accuracy (IP -> Country): {acc:.4f}")

    df_pred = pd.DataFrame({
        'client_ip': le_ip.inverse_transform(X_test.flatten()),
        'true_country': le_country.inverse_transform(y_test),
        'pred_country': le_country.inverse_transform(y_pred)
    })
    filename = "ip_to_country_results.csv"
    df_pred.to_csv(filename, index=False)
    upload_to_gcs(filename)
    return model
# =========================
# SUPERVISED MODEL: Predict Income
# =========================
def knn_income_prediction(df_clients, conn, n_neighbors=5, bucket_name=None):
    # Merge total requests
    query = "SELECT client_id, COUNT(*) AS total_requests FROM requests GROUP BY client_id"
    df_requests = pd.read_sql(query, conn)
    df = df_clients.merge(df_requests, on='client_id', how='left')
    df['total_requests'] = df['total_requests'].fillna(0)

    # Drop unknown income
    df = df[df['income_range_id'].notna()]
    df['income_range_id'] = df['income_range_id'].astype(int)

    # Features: one-hot encode categorical variables
    X = pd.get_dummies(df[['country','gender']], drop_first=True)
    X['total_requests'] = df['total_requests']
    X.columns = [re.sub(r'\W+', '_', c) for c in X.columns]

    y = df['income_range_id']

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )

    # KNN classifier
    knn = KNeighborsClassifier(n_neighbors=n_neighbors, n_jobs=-1)
    knn.fit(X_train, y_train)
    y_pred = knn.predict(X_test)

    # Accuracy
    acc = accuracy_score(y_test, y_pred)
    print(f"KNN classifier accuracy: {acc:.4f}")

    # Confusion matrix
    cm = pd.DataFrame(
        confusion_matrix(y_test, y_pred, labels=sorted(y.unique())),
        index=sorted(y.unique()),
        columns=sorted(y.unique())
    )
    print("Confusion Matrix:\n", cm)

    # Save predictions
    results = pd.DataFrame(X_test, columns=X.columns)
    results['true_income_range_id'] = y_test.reset_index(drop=True)
    results['pred_income_range_id'] = y_pred
    results_file = "knn_income_predictions.csv"
    results.to_csv(results_file, index=False)

    # Upload to GCS if bucket provided
    if bucket_name:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(results_file)
        blob.upload_from_filename(results_file)
        print(f"Uploaded {results_file} to gs://{bucket_name}/{results_file}")

    return knn, acc, cm

# =========================
# MAIN
# =========================
def main():
    # Connect to DB
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

    df_clients = get_clients_data(conn)
    
    knn_model, knn_acc, knn_cm = knn_income_prediction(df_clients, conn, n_neighbors=7, bucket_name=BUCKET_NAME)   

    conn.close()

if __name__ == "__main__":
    main()
