import csv
import random
from faker import Faker
from uuid import uuid4
import pandas as pd

# Initialize Faker for realistic names
fake = Faker()

path1 = "data/conferences.csv"
path2 = "data/journals.csv"
df1 = pd.read_csv(path1, sep=",")
df2 = pd.read_csv(path2, sep=",")
NUM_RECORDS = len(df1)+len(df2)

# Generate random data
data = []
for _ in range(NUM_RECORDS):
    record = {
        'id': str(uuid4()),  # Generate unique UUID
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
        'age': random.randint(18, 80),
        'email': fake.email(),
        'phone': fake.phone_number()
    }
    data.append(record)

# CSV file path
csv_file = '../data/coordinators.csv'

# Write to CSV
with open(csv_file, mode='w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

print(f"Generated {NUM_RECORDS} records in {csv_file}")