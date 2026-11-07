import numpy as np
import pandas as pd

rng = np.random.default_rng(99)

users = pd.read_csv("data/users.csv", parse_dates=["signup_date"])
events = pd.read_csv("data/events.csv", parse_dates=["event_time"])

DATA_END = pd.Timestamp("2026-06-30")
ANDROID_UPDATE = pd.Timestamp("2026-04-15")
n = len(users)

# Which users set a goal and which turned on reminders.
did_goal = users["user_id"].isin(
    events.loc[events["event_name"] == "goal_created", "user_id"]
).to_numpy()
did_reminder = users["user_id"].isin(
    events.loc[events["event_name"] == "reminder_enabled", "user_id"]
).to_numpy()

# The last day each user opened the app. Users who never opened it stay empty.
opens = events[events["event_name"] == "app_opened"]
users["last_open"] = users["user_id"].map(opens.groupby("user_id")["event_time"].max())

# Decide who upgrades. Reminder users upgrade more often.
p_upgrade = np.where(did_reminder, 0.30, np.where(did_goal, 0.18, 0.0))
upgrades = (rng.random(n) < p_upgrade) & users["last_open"].notna().to_numpy()
pro = users[upgrades].reset_index(drop=True)
m = len(pro)

# Pick an upgrade day between day 1 after signup and the user's last visit.
span = (pro["last_open"] - pro["signup_date"]).dt.days.to_numpy()
upgrade_day = rng.integers(1, np.maximum(span, 2) + 1)
start = pro["signup_date"] + pd.to_timedelta(upgrade_day, unit="D")

# Normal cancellation: Pro users stay about 90 days on average.
cancel = start + pd.to_timedelta(rng.exponential(90, size=m), unit="D")

# PLANTED ISSUE 3: after the update, Android users get a second, extra chance
# to cancel. Whichever cancel date comes first wins.
extra_start = start.clip(lower=ANDROID_UPDATE)
extra_cancel = extra_start + pd.to_timedelta(rng.exponential(90, size=m), unit="D")
is_hit = (pro["platform"] == "Android") & (cancel > ANDROID_UPDATE)
earlier = cancel.where(cancel < extra_cancel, extra_cancel)
cancel = cancel.where(~is_hit, earlier).dt.normalize()

# A cancel date after the data ends means the user is still subscribed.
end_date = cancel.where(cancel <= DATA_END)
reasons = pd.Series(
    rng.choice(
        ["too_expensive", "not_using_it", "found_alternative", "app_problems", "other"],
        size=m,
        p=[0.25, 0.30, 0.15, 0.15, 0.15],
    )
)

subs = pd.DataFrame({
    "user_id": pro["user_id"],
    "platform": pro["platform"],
    "plan": "pro",
    "start_date": start,
    "end_date": end_date,
    "status": np.where(end_date.notna(), "cancelled", "active"),
    "cancel_reason": reasons.where(end_date.notna()),
})
subs = subs.sort_values("start_date").reset_index(drop=True)
subs.insert(0, "subscription_id", subs.index + 1)

subs.drop(columns=["platform"]).to_csv("data/subscriptions.csv", index=False)
print(subs["status"].value_counts())
print(f"Created {len(subs)} Pro subscriptions")

# Sanity check: of the Pro users subscribed on April 15,
# how many cancelled within the next 30 days, by platform?
on_update = subs[
    (subs["start_date"] < ANDROID_UPDATE)
    & (subs["end_date"].isna() | (subs["end_date"] >= ANDROID_UPDATE))
].copy()
on_update["cancelled_in_30_days"] = on_update["end_date"].notna() & (
    on_update["end_date"] <= ANDROID_UPDATE + pd.Timedelta(days=30)
)
print("\nShare cancelling within 30 days of the update:")
print(on_update.groupby("platform")["cancelled_in_30_days"].agg(["mean", "count"]).round(2))