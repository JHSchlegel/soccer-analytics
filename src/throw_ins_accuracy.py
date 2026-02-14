# =========================================================================== #
#                    Packages and Presets                                     #
# =========================================================================== #
import json
from tqdm import tqdm
import pandas as pd
from pathlib import Path
import numpy as np
from skimpy import clean_columns
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt


pd.set_option("display.max_columns", None)


# =========================================================================== #
#                           Data Loading                                      #
# =========================================================================== #
# dictionary that creates hash map for skyllcorner vs wyscout match id's
match_ids = {
    # wyscout:skillcorner
    "5414314": "1381503",
    "5414290": "1381473",
    "5414267": "1193645",
    "5414241": "1368349",
    "5414229": "1381427",
}

skyllcorner_ids = [key for key in match_ids.values()]

## skillcorner data
data_dir = Path("data/skillcorner")

# match_id = "1381503"
metadata_dfs = {}
play_direction_dfs = {}
phase_dfs = {}
lineup_dfs = {}
tracking_dfs = {}
visible_area_dfs = {}
physical_dfs = {}
passes_dfs = {}
on_ball_pressures_dfs = {}
off_ball_runs_dfs = {}
max_ball_z_dfs = {}

for match_id in tqdm(skyllcorner_ids):
    metadata_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_metadata.csv")
    play_direction_dfs[match_id] = pd.read_csv(
        data_dir / f"{match_id}_play_direction.csv"
    )
    phase_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_phase.csv")
    lineup_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_lineup.csv")
    tracking_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_tracking.csv")
    visible_area_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_visible_area.csv")
    physical_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_physical.csv")
    passes_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_passes.csv")
    on_ball_pressures_dfs[match_id] = pd.read_csv(
        data_dir / f"{match_id}_on_ball_pressures.csv"
    )
    off_ball_runs_dfs[match_id] = pd.read_csv(
        data_dir / f"{match_id}_off_ball_runs.csv"
    )
    max_ball_z_dfs[match_id] = int(tracking_dfs[match_id].z.max())


# stack tracking data
tracking_dfs_conc = pd.concat(tracking_dfs.values())
off_ball_runs_dfs_conc = pd.concat(off_ball_runs_dfs.values())


wyscout_match_ids = [
    "5414314",
    "5414290",
    "5414267",
    "5414241",
    "5414229",
    "5414204",
    "5414143",
    "5414122",
]

path = Path("data/wyscout")
wyscout_dataframes = {}


for id in wyscout_match_ids:
    json_path = path / f"{id}.json"
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    df = pd.json_normalize(data, record_path=["events"])
    df = clean_columns(df)
    df.name = f"wyscout_{id}"
    wyscout_dataframes[id] = df


wyscout_spain_matches = pd.concat(wyscout_dataframes.values())

spain_throw_ins = wyscout_spain_matches.query("type_primary == 'throw_in'").query(
    "team_name == 'Spain'"
)

# %%
wyscout_match_ids = [
    "5414314",
    "5414290",
    "5414267",
    "5414241",
    "5414229",
    "5414204",
    "5414143",
    "5414122",
]

path = Path("data/wyscout")
wyscout_dataframes = {}


for id in wyscout_match_ids:
    json_path = path / f"{id}.json"
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    df = pd.json_normalize(data, record_path=["events"])
    df = clean_columns(df)
    df.name = f"wyscout_{id}"
    wyscout_dataframes[id] = df


# =========================================================================== #
#                           Plotting                                          #
# =========================================================================== #
#!!! code based on snippet 1291 by the one and only Rufat
# Pitch initialization
pitch = VerticalPitch(pitch_color="#2f8c58", line_color="white", pitch_type="wyscout")
fig, ax = pitch.draw(figsize=(12, 8))

# colors = ["#EE0000FF", "#088B45FF"]  # Colors taken from AAAS journal color palette
colors = ["red", "lightblue"]

# Prevent legend duplication
legend_labels = {}

for index, row in spain_throw_ins.iterrows():
    color = colors[row.pass_accurate]
    label = f"{['Inaccurate', 'Accurate'][row.pass_accurate]} Throw-in"

    if label not in legend_labels:
        # Legends don't overlap
        legend_labels[label] = ax.scatter([], [], color=color, label=label)

    # Draw a line to the throw-in end location
    pitch.arrows(
        row.location_x,
        row.location_y,
        row.pass_end_location_x,
        row.pass_end_location_y,
        color=color,
        width=1.5,
        headwidth=3,
        alpha=0.9,
        ax=ax,
    )

# Adding legends for clarity
ax.legend(
    handles=list(legend_labels.values()),
    title="",
    loc="upper right",
    bbox_to_anchor=(0.7, 1),
)
plt.savefig("results/plots/throw_in_accuracy.png", bbox_inches="tight")
plt.show()
