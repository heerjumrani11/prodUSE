import numpy as np
import pandas as pd

rng = np.random.default_rng(21)

users = pd.read_csv("data/users.csv", parse_dates=["signup_date"])
events = pd.read_csv("data/events.csv", parse_dates=["event_time"])

# Remove old app_opened rows so running this file twice does not double them.
events = events[events["event_name"] != "app_opened"].drop(columns=["event_id"])

n = len(users)
DATA_END = pd.Timestamp("2026-06-30")
MAX_DAYS = 180
OPEN_CHANCE = 0.45  # chance a still-active user opens the app on a given day

# Work out which users completed which onboarding steps.
did_goal = users["user_id"].isin(
    events.loc[events["event_name"] == "goal_created", "user_id"]
).to_numpy()
did_reminder = users["user_id"].isin(
    events.loc[events["event_name"] == "reminder_enabled", "user_id"]
).to_numpy()

# PLANTED ISSUE 2: reminder users stay around longer.
# This is the average number of days a user stays active.
mean_lifetime = np.where(did_reminder, 30, np.where(did_goal, 22, 6))
lifetime = rng.exponential(mean_lifetime)

# Build a grid with one row per user and one column per day after signup.
days = np.arange(1, MAX_DAYS + 1)
alive = days[None, :] <= lifetime[:, None]
opens_today = rng.random((n, MAX_DAYS)) < OPEN_CHANCE

# Nobody can open the app after the data ends.
days_left = (DATA_END - users["signup_date"]).dt.days.to_numpy()
in_window = days[None, :] <= days_left[:, None]

# A cell is True when the user is still active, opens the app and the day is in range.
active = alive & opens_today & in_window
user_idx, day_idx = np.nonzero(active)

# Turn each True cell into one app_opened row.
base = users["signup_date"].iloc[user_idx].reset_index(drop=True)
seconds = rng.integers(7 * 3600, 23 * 3600, size=len(user_idx))
opened = pd.DataFrame({
    "user_id": users["user_id"].iloc[user_idx].reset_index(drop=True),
    "event_name": "app_opened",
    "event_time": base
    + pd.to_timedelta(days[day_idx], unit="D")
    + pd.to_timedelta(seconds, unit="s"),
})

# Add the new rows to the events table.
events = pd.concat([events, opened], ignore_index=True)

# The app updated to version 1.1 in mid April.
events["app_version"] = np.where(
    events["event_time"] < pd.Timestamp("2026-04-15"), "1.0", "1.1"
)

events = events.sort_values(["event_time", "user_id"]).reset_index(drop=True)
events.insert(0, "event_id", events.index + 1)
events.to_csv("data/events.csv", index=False)

print(events["event_name"].value_counts())
print(f"Total events: {len(events)}")

# Sanity check: did the planted issue show up?
# Look at users who signed up early enough to have 60 days of history.
users["group"] = np.where(
    did_reminder, "reminder", np.where(did_goal, "goal_no_reminder", "no_goal")
)
opens = events[events["event_name"] == "app_opened"].merge(
    users[["user_id", "signup_date"]], on="user_id"
)
opens["day"] = (opens["event_time"] - opens["signup_date"]).dt.days
returned = opens.loc[opens["day"] >= 14, "user_id"].unique()

early = users[users["signup_date"] < "2026-05-01"].copy()
early["returned_after_14_days"] = early["user_id"].isin(returned)
print("\nShare of users who came back 14+ days after signup:")
print(early.groupby("group")["returned_after_14_days"].mean().round(2))
