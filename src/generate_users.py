import numpy as np
import pandas as pd

# A seed makes the random numbers repeatable.
# You get the same fake users every time you run this file.
rng = np.random.default_rng(42)

NUM_USERS = 5000

# Each user signs up on a random day in a 6 month window.
start_date = pd.Timestamp("2026-01-01")
signup_offsets = rng.integers(0, 180, size=NUM_USERS)
signup_dates = start_date + pd.to_timedelta(signup_offsets, unit="D")

# Build the table. Each column is a list of 5000 values.
users = pd.DataFrame({
    "signup_date": signup_dates,
    "platform": rng.choice(["iOS", "Android"], size=NUM_USERS, p=[0.45, 0.55]),
    "country": rng.choice(
        ["US", "India", "UK", "Canada", "Germany"],
        size=NUM_USERS,
        p=[0.40, 0.25, 0.15, 0.10, 0.10],
    ),
    "acquisition_channel": rng.choice(
        ["organic", "paid_ads", "referral", "social"],
        size=NUM_USERS,
        p=[0.40, 0.25, 0.15, 0.20],
    ),
    "plan": "free",
})

# Sort by signup date, then give each user an ID number starting at 1.
users = users.sort_values("signup_date").reset_index(drop=True)
users.insert(0, "user_id", users.index + 1)

# Save the table as a file and show a preview.
users.to_csv("data/users.csv", index=False)
print(users.head())
print(f"Created {len(users)} users")