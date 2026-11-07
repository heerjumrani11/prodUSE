import numpy as np
import pandas as pd

# A different seed from the users file, so the two stay independent.
rng = np.random.default_rng(7)

# Load the users we created in the last step.
users = pd.read_csv("data/users.csv", parse_dates=["signup_date"])
n = len(users)

# How many users continue from one step to the next.
P_CHOOSE_CATEGORY = 0.90
P_SET_GOAL = 0.55  # PLANTED ISSUE 1: a normal app would be near 0.85
P_ENABLE_REMINDER = 0.60
P_FIRST_CHECKIN = 0.80

# Decide who does each step.
# "&" means both must be true, so you can't set a goal without a category.
has_category = rng.random(n) < P_CHOOSE_CATEGORY
has_goal = has_category & (rng.random(n) < P_SET_GOAL)
has_reminder = has_goal & (rng.random(n) < P_ENABLE_REMINDER)
has_checkin = has_goal & (rng.random(n) < P_FIRST_CHECKIN)

# Decide when each step happens. Each one is a few seconds or minutes
# after the step before it.
signup_seconds = rng.integers(8 * 3600, 22 * 3600, size=n)
signup_time = users["signup_date"] + pd.to_timedelta(signup_seconds, unit="s")
category_time = signup_time + pd.to_timedelta(rng.integers(20, 180, size=n), unit="s")
goal_time = category_time + pd.to_timedelta(rng.integers(30, 600, size=n), unit="s")
reminder_time = goal_time + pd.to_timedelta(rng.integers(30, 300, size=n), unit="s")
checkin_time = goal_time + pd.to_timedelta(rng.integers(300, 86400, size=n), unit="s")


def make_events(mask, name, times):
    """Make one row for every user where mask is True."""
    return pd.DataFrame({
        "user_id": users.loc[mask, "user_id"],
        "event_name": name,
        "event_time": times[mask],
    })


everyone = np.ones(n, dtype=bool)

events = pd.concat([
    make_events(everyone, "signed_up", signup_time),
    make_events(has_category, "category_chosen", category_time),
    make_events(has_goal, "goal_created", goal_time),
    make_events(has_reminder, "reminder_enabled", reminder_time),
    make_events(has_checkin, "checkin_completed", checkin_time),
], ignore_index=True)

# Sort by time, number each event and save the table.
events = events.sort_values(["event_time", "user_id"]).reset_index(drop=True)
events.insert(0, "event_id", events.index + 1)
events["app_version"] = "1.0"

events.to_csv("data/events.csv", index=False)
print(events["event_name"].value_counts())
print(f"Created {len(events)} events")
