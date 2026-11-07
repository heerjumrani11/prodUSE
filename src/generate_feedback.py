from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(314)

users = pd.read_csv("data/users.csv", parse_dates=["signup_date"])
events = pd.read_csv("data/events.csv", parse_dates=["event_time"])
subs = pd.read_csv("data/subscriptions.csv", parse_dates=["start_date", "end_date"])

DATA_END = pd.Timestamp("2026-06-30")
ANDROID_UPDATE = pd.Timestamp("2026-04-15")
n = len(users)

# Short messages for each theme. We pick one at random for each piece of feedback.
TEXTS = {
    "pricing": [
        "Pro is too expensive for what it offers.",
        "I can't justify paying every month for a habit tracker.",
        "Too pricey compared to free habit apps.",
        "Love the app but the subscription cost is too high for me.",
        "Thinking of cancelling because the price is not worth it.",
    ],
    "onboarding_confusing": [
        "Setting up my first goal was confusing and I gave up.",
        "Too many steps before I could start. I almost deleted the app.",
        "I didn't understand what to enter when creating a goal.",
        "The goal setup screen is overwhelming.",
    ],
    "app_crashes": [
        "The app keeps crashing since the last update.",
        "Crashes every time I open my streak screen.",
        "Latest update broke the app. My check-ins won't save.",
        "Freezes and closes randomly on my phone.",
    ],
    "love_reminders": [
        "The daily reminders keep me on track. Love them.",
        "Reminders are the best feature. I haven't missed a day.",
        "Streak reminders actually work for me.",
    ],
    "feature_request": [
        "Please add a widget for my home screen.",
        "Would love to share streaks with friends.",
        "Can you add dark mode and weekly reports?",
        "Needs a way to track habits I do many times a day.",
    ],
    "general_positive": [
        "Simple and nice to use.",
        "Great little app. Does exactly what I need.",
        "Clean design and easy to log check-ins.",
    ],
    "other": [
        "It's okay. Nothing special yet.",
        "Not sure this is for me.",
        "Decent app but I keep forgetting to open it.",
    ],
}

# Star ratings for each theme as (lowest, highest + 1).
RATING_RANGE = {
    "pricing": (1, 4),
    "onboarding_confusing": (1, 4),
    "app_crashes": (1, 3),
    "love_reminders": (4, 6),
    "feature_request": (3, 5),
    "general_positive": (4, 6),
    "other": (2, 5),
}

# Which users set a goal and which turned on reminders.
did_goal = users["user_id"].isin(
    events.loc[events["event_name"] == "goal_created", "user_id"]
).to_numpy()
did_reminder = users["user_id"].isin(
    events.loc[events["event_name"] == "reminder_enabled", "user_id"]
).to_numpy()

# PART 1: everyday feedback. About 8% of all users write something once.
writes = rng.random(n) < 0.08
base = users[writes].copy()
base["did_goal"] = did_goal[writes]
base["did_reminder"] = did_reminder[writes]

days_left = (DATA_END - base["signup_date"]).dt.days.to_numpy()
offset = rng.integers(1, np.minimum(days_left, 120) + 1)
base["created_at"] = base["signup_date"] + pd.to_timedelta(offset, unit="D")


def pick_baseline_theme(goal, reminder, platform, created_at):
    """Choose what a user writes about, based on what they experienced."""
    if platform == "Android" and created_at >= ANDROID_UPDATE:
        names = ["app_crashes", "pricing", "feature_request", "general_positive", "other"]
        odds = [0.40, 0.05, 0.15, 0.20, 0.20]
    elif not goal:
        names = ["onboarding_confusing", "pricing", "feature_request", "general_positive", "other"]
        odds = [0.45, 0.04, 0.11, 0.10, 0.30]
    elif reminder:
        names = ["love_reminders", "pricing", "feature_request", "general_positive", "other"]
        odds = [0.25, 0.05, 0.20, 0.35, 0.15]
    else:
        names = ["pricing", "feature_request", "general_positive", "other"]
        odds = [0.05, 0.25, 0.40, 0.30]
    return str(rng.choice(names, p=odds))


base_themes = [
    pick_baseline_theme(g, r, p, t)
    for g, r, p, t in zip(
        base["did_goal"], base["did_reminder"], base["platform"], base["created_at"]
    )
]
base_fb = base[["user_id", "created_at"]].assign(theme=base_themes).reset_index(drop=True)

# PART 2: feedback right before cancelling.
# PLANTED ISSUE 4: most users who say they cancelled because of price
# write a pricing complaint in the 14 days before they leave.
rows = []
cancelled = subs[subs["status"] == "cancelled"]
for sub in cancelled.itertuples():
    reason = sub.cancel_reason
    p_price = 0.85 if reason == "too_expensive" else 0.20
    if rng.random() < p_price:
        theme = "pricing"
    elif rng.random() < 0.35:
        theme = {
            "not_using_it": "other",
            "found_alternative": "feature_request",
            "app_problems": "app_crashes",
        }.get(reason, "other")
    else:
        continue  # this user cancels without writing anything
    days_before = int(rng.integers(1, 15))
    created_at = max(sub.end_date - pd.Timedelta(days=days_before), sub.start_date)
    rows.append((sub.user_id, created_at, theme))

cancel_fb = pd.DataFrame(rows, columns=["user_id", "created_at", "theme"])

# Put both parts together and fill in the remaining columns.
all_fb = pd.concat([base_fb, cancel_fb], ignore_index=True)
seconds = rng.integers(8 * 3600, 22 * 3600, size=len(all_fb))
all_fb["created_at"] = all_fb["created_at"] + pd.to_timedelta(seconds, unit="s")
all_fb["channel"] = rng.choice(["app_review", "survey"], size=len(all_fb), p=[0.6, 0.4])
all_fb["text"] = [str(rng.choice(TEXTS[t])) for t in all_fb["theme"]]
all_fb["rating"] = [int(rng.integers(*RATING_RANGE[t])) for t in all_fb["theme"]]

all_fb = all_fb.sort_values(["created_at", "user_id"]).reset_index(drop=True)
all_fb.insert(0, "feedback_id", all_fb.index + 1)

# Save the feedback table without the theme. Save the theme labels
# separately as the answer key.
all_fb[["feedback_id", "user_id", "created_at", "channel", "rating", "text"]].to_csv(
    "data/feedback.csv", index=False
)
Path("answer_key").mkdir(exist_ok=True)
all_fb[["feedback_id", "theme"]].to_csv("answer_key/feedback_themes.csv", index=False)

print(all_fb["theme"].value_counts())
print(f"\nCreated {len(all_fb)} feedback messages")

# Sanity check: did the planted issue show up?
fb = all_fb.merge(subs[["user_id", "end_date"]], on="user_id", how="left")
days_to_cancel = (fb["end_date"] - fb["created_at"].dt.normalize()).dt.days
near_cancel = days_to_cancel.between(0, 14)

print("\nShare of feedback about pricing:")
share_near = (fb.loc[near_cancel, "theme"] == "pricing").mean()
share_other = (fb.loc[~near_cancel, "theme"] == "pricing").mean()
print(f"  In the 14 days before cancelling: {share_near:.2f} ({near_cancel.sum()} messages)")
print(f"  At all other times: {share_other:.2f} ({(~near_cancel).sum()} messages)")