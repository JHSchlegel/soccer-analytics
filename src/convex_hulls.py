# =========================================================================== #
#                    Packages and Presets                                     #
# =========================================================================== #
# %%
import json
from tqdm import tqdm
import pandas as pd
from pathlib import Path
import numpy as np
from skimpy import clean_columns
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
from mplsoccer import VerticalPitch
from PIL import Image
from datetime import datetime
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os
from typing import Dict

pd.set_option("display.max_columns", None)


# =========================================================================== #
#                           Data Loading                                      #
# =========================================================================== #

# %%
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
# %%

# %%
# stack tracking data
tracking_dfs_conc = pd.concat(tracking_dfs.values())
off_ball_runs_dfs_conc = pd.concat(off_ball_runs_dfs.values())
lineup_dfs_conc = pd.concat(lineup_dfs.values())
play_direction_dfs_conc = pd.concat(play_direction_dfs.values())


FPS = 10


# =========================================================================== #
#                        Helper Functions                                     #
# =========================================================================== #
def get_matchinfo(match_id: int):
    metadata_game = metadata_dfs[str(match_id)]
    length = metadata_game.pitch_length.values[0]
    width = metadata_game.pitch_width.values[0]
    home = metadata_game.home_team.values[0]
    away = metadata_game.away_team.values[0]
    home_score = metadata_game.home_score.values[0]
    away_score = metadata_game.away_score.values[0]
    date = datetime.strptime(metadata_game.match_date.values[0], "%m/%d/%Y %H:%M")
    date_conv = date.strftime("%m.%d.%Y")
    return length, width, home, away, home_score, away_score, date_conv


def preprocess_skillcorner_data(
    match_ids: Dict[str, str],
    tracking_df: pd.DataFrame,
    dir_dct: Dict[int, Dict[int, int]],
):
    tracking_dfs_conc = tracking_df.copy()
    for match_id in match_ids.values():
        match_id = int(match_id)
        play_dir = dir_dct[match_id]
        _, _, home, away, _, _, _ = get_matchinfo(match_id)
        # print(home, away)
        for half, direction in play_dir.items():
            criteria = "match_id == @match_id & half == @half"
            tracking_dfs_conc.loc[
                tracking_dfs_conc.eval(criteria), ["x", "y"]
            ] *= direction
    return tracking_dfs_conc


def get_match_time(timestamp, half):
    """Return the running match time (start from the first half kick-off) from the given timestamp and half"""
    half_start = 0
    if half == 2:
        half_start = 45 * 60 * 1000
    seconds = int((timestamp + half_start) / 1000)
    minutes = int(seconds / 60)
    seconds = seconds % 60
    match_time = f"{minutes}:{seconds:02d}"
    return match_time


# Function to add the flag to picture
#!!! based on snippet nr 1015 by rufat asadli
def add_flag(fig, flag_path, zoom, position):
    img = plt.imread(flag_path)
    imagebox = OffsetImage(img, zoom=zoom)
    ab = AnnotationBbox(imagebox, position, xycoords="figure fraction", frameon=False)
    fig.add_artist(ab)


# =========================================================================== #
#                           Data Preprocessing                                     #
# =========================================================================== #
spain_in_possession = (
    pd.concat(phase_dfs.values())
    .query("team_name == 'Spain' & name == 'IN_POSSESSION'")
    .query("end-start > 10 * @FPS")  # posession at least 10 seconds; 100 frames
)


spain_out_possession = (
    pd.concat(phase_dfs.values())
    .query("team_name == 'Spain' & name == 'OUT_POSSESSION'")
    .query("end-start > 10 * @FPS")  # posession at least 10 seconds; 100 frames
)


spain_out_possession["frame_id"] = spain_out_possession["start"] + 10 * FPS
spain_in_possession["frame_id"] = spain_in_possession["start"] + 10 * FPS


play_direction_dfs_conc["play_direction"] = (
    play_direction_dfs_conc.play_direction.apply(
        lambda x: 1 if x == "BOTTOM_TO_TOP" else -1
    )
)

play_directions_spain = play_direction_dfs_conc.query("team_name == 'Spain'")

play_directions_dct = {}
for _, (match_id, _, half, play_dir) in play_directions_spain.iterrows():
    if match_id in play_directions_dct:
        play_directions_dct[match_id][half] = play_dir
    else:
        play_directions_dct[match_id] = {}
        play_directions_dct[match_id][half] = play_dir


tracking_dfs_conc_cleaned = preprocess_skillcorner_data(
    match_ids, tracking_dfs_conc, play_directions_dct
)


def get_example_positions(match_id: int, poss_df: pd.DataFrame, n: int = 2):
    positions = {}

    for half in [1, 2]:
        # unique frame ids in tracking data to avoid sampling frames that don't exist
        # in the tracking data
        tracking_frames = (
            tracking_dfs_conc_cleaned.query("match_id == @match_id")
            .query("half == @half")
            .frame_id.unique()
            .tolist()
        )

        # get out of possession phases for the match
        match_poss = (
            poss_df.loc[poss_df.match_id == match_id, :]
            .query("half == @half")
            .query("frame_id in @tracking_frames")
        )

        # randomly sample n examples from each half
        sampled_indices = np.random.choice(len(match_poss), size=n // 2, replace=False)
        poss_examples = match_poss.iloc[sampled_indices, :].sort_values("frame_id")
        frame_ids = poss_examples.frame_id.values.tolist()

        # player ids of spain players (apart from goalkeepers)
        spain_object_ids = (
            lineup_dfs_conc.query("match_id == @match_id & team_name == 'Spain'")
            .query("player_position != 'Goalkeeper'")
            .player_id.unique()
        )

        for idx, frame_id in enumerate(frame_ids):
            timestamp = tracking_dfs_conc_cleaned.query(
                "frame_id == @frame_id"
            ).timestamp.values[0]
            match_time = get_match_time(timestamp, half)
            positions[f"Half {half} - {match_time}"] = tracking_dfs_conc_cleaned.query(
                "match_id == @match_id & object_id in @spain_object_ids & frame_id == @frame_id"
            )[["x", "y"]].values
    return positions


# =========================================================================== #
#                             Plotting                                        #
# =========================================================================== #
def plot_convex_hulls(
    pos_data: Dict[str, np.ndarray],
    match_id: int,
    length: int,
    width: int,
    home: str,
    away: str,
    home_score: int,
    away_score: int,
    date: datetime.date,
    possession_str: int,
    zoom_home: float,
    zoom_away: float,
    save_fig: bool = False,
):
    fill_colors = ["green", "green", "blue", "blue"]
    marker_colors = ["green", "green", "blue", "blue"]
    markers = ["o", "o", "s", "s"]
    alpha = 0.3

    fig, axes = plt.subplots(1, 4, figsize=(20, 10))
    fig.patch.set_facecolor("gainsboro")

    pitch = VerticalPitch(
        pitch_type="skillcorner",
        line_color="black",
        pitch_color="gainsboro",
        pitch_length=length,
        pitch_width=width,
    )

    plt.suptitle(
        f"{home_score}   -   {away_score}\n\n\n{date} - {possession_str}",
        fontsize=18,
        fontweight="bold",
        y=0.95,
    )
    add_flag(fig, f"flags/{home}.png", zoom_home, (0.46, 0.94))
    add_flag(fig, f"flags/{away}.png", zoom_away, (0.54, 0.94))
    for ax, (time, coords), fill_color, marker_color, marker in zip(
        axes, pos_data.items(), fill_colors, marker_colors, markers
    ):
        pitch.draw(ax=ax)
        hull = ConvexHull(coords)
        center_of_mass = np.mean(coords, axis=0)
        # see: https://stackoverflow.com/questions/62376042/calculating-and-displaying-a-convexhull
        pitch.plot(
            x=coords[:, 0],
            y=coords[:, 1],
            color=marker_color,
            linestyle="",
            ax=ax,
            marker=marker,
            markersize=8,
        )
        # light blue arrow from center of mass to middle of the pitch
        ax.arrow(
            0,
            0,
            center_of_mass[1],
            center_of_mass[0],
            color="#191970",
            head_width=1.5,
            head_length=1.5,
        )
        # fill convex hull
        ax.fill(
            coords[hull.vertices, 1], coords[hull.vertices, 0], fill_color, alpha=alpha
        )
        ax.set_title(f"Time: {time}", fontsize=16)

    plt.tight_layout()
    if save_fig:
        save_path = f"results/plots/convex_hull/{match_id}_{possession_str}.jpg"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300)
    plt.show()


def plot_all_convex_hulls(
    match_ids: Dict[str, str],
    n: int,
    zoom_home: float,
    zoom_away: float,
    save_fig: bool,
):
    for match_id in match_ids.values():
        match_id = int(match_id)
        poss_dct = {
            "Spain in Possession": spain_in_possession,
            "Spain out of Possession": spain_out_possession,
        }
        for possession_str, possession_data in poss_dct.items():
            pos_data = get_example_positions(match_id, possession_data, n)
            length, width, home, away, home_score, away_score, date = get_matchinfo(
                match_id
            )
            plot_convex_hulls(
                pos_data,
                match_id,
                length,
                width,
                home,
                away,
                home_score,
                away_score,
                date,
                possession_str,
                zoom_home,
                zoom_away,
                save_fig,
            )


np.random.seed(42)
plot_all_convex_hulls(match_ids, 4, 0.05, 0.05, True)
