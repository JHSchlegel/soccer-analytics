# ============================================================================= #
#                           Offside Analysis                                    #
# ============================================================================= #


# ----------------------------------- #
#        Packages and Presets         #
# ----------------------------------- #
import json
from tqdm import tqdm
import pandas as pd
from pathlib import Path
from skimpy import clean_columns
import seaborn as sns
import matplotlib.pyplot as plt

sns.set_style("whitegrid")

import imageio.v2 as iio

from mplsoccer import VerticalPitch
import shutil
import os


pd.set_option("display.max_columns", None)


# Neighborhood that determines which timestamps will be considered in the animation
# before and after the offside position occured
MAX_TIMESTAMP_DIFF = 2_000


# ------------------------------------------- #
#        Data Loading and Preprocessing       #
# ------------------------------------------- #

# dictionary that creates hash map for skyllcorner vs wyscout match id"s
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

# initialize dictionaries for all dataframes skillcorner provides
# each dictionary will have the match_id as key and the dataframe as value
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

# read in all skillcorner data that concerns matches in which Spain played
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


# dictionary for minutes player per player
# manually looked the minutes played up from the uefa website:
# https://www.uefa.com/euro2024/teams/122--spain//squad/
mins_played = {
    "Álvaro Morata": 461,
    "Rodri": 608,
    "Dani Carvajal": 586,
    "Fabián Ruiz": 279,
    "Nico Williams": 222,
    "José Gayá": 331,
    "Robin Le Normand": 450,
    "Ferrán Torres": 272,
    "Íñigo Martínez": 180,
    "Gavi": 488,
    "Unai Simón": 450,
    "Oihan Sancet": 98,
    "Lamine Yamal": 205,
    "Rodrigo Riquelme": 54,
    "Martín Zubimendi": 112,
    "Mikel Merino": 372,
    "Alex Grimaldo": 90,
    "Jesús Navas": 89,
    "Pau Torres": 90,
    "Mikel Oyarzabal": 207,
    "David Raya": 90,
    "Joselu": 235,
    "Aleix García": 45,
    "David García": 180,
    "Aymeric Laporte": 450,
    "Fran García": 135,
    "Ansu Fati": 45,
    "Alfonso Pedraza": 19,
    "Alejandro Balde": 164,
    "Bryan Zaragoza": 44,  # for whatever reason showed as 0 in the uefa website
    # thus I used the minutes player from transfer markt
    "Yéremy Pino": 158,
    "Álex Baena": 14,
    "Marco Asensio": 44,
    "Dani Olmo": 111,
    "Pedro Porro": 45,
    "Kepa Arrizabalaga": 180,
    "Dani Ceballos": 111,
    "Iago Aspas": 91,
    "Borja Iglesias": 24,
    "Nacho Fernández": 90,
}

# all wyscout ids of Spain matches
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

# read in all wyscout data from Spain matches
for id in wyscout_match_ids:
    json_path = path / f"{id}.json"
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    df = pd.json_normalize(data, record_path=["events"])
    df = clean_columns(df)
    df.name = f"wyscout_{id}"
    wyscout_dataframes[id] = df


# create dataframe with all offside positions of Spain
offsides = (
    pd.concat(wyscout_dataframes.values())
    .query('type_primary == "offside" & team_name == "Spain"')
    .loc[
        :,
        [
            "match_id",
            "player_name",
            "player_position",
            "player_id",
            "opponent_team_name",
            "opponent_team_formation",
            "possession_duration",
            "possession_id",
            "possession_types",
            "match_timestamp",
            "match_period",
        ],
    ]
)


# ---------------------------------------------- #
#      Number of Offsides per Team per Game      #
# ---------------------------------------------- #

# get wyscout match ids from all matches (not just the Spain matches)
all_wyscout_match_ids = [id.split(".")[0] for id in os.listdir("all_data/wyscout")]

all_data_path = Path("all_data/wyscout")
wyscout_all_dataframes = {}


for id in wyscout_match_ids:
    json_path = all_data_path / f"{id}.json"
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    df = pd.json_normalize(data, record_path=["events"]).pipe(clean_columns)
    df.name = f"wyscout_{id}"
    wyscout_all_dataframes[id] = df


all_offsides = (
    pd.concat(wyscout_all_dataframes.values())
    .query("type_primary == 'offside'")
    .loc[
        :,
        [
            "match_id",
            "player_name",
            "player_position",
            "player_id",
            "team_name",
            "opponent_team_name",
            "opponent_team_formation",
            "possession_duration",
            "possession_id",
            "possession_types",
            "match_timestamp",
            "match_period",
        ],
    ]
)

# calculate number of games played per team
games_per_team = (
    pd.concat(wyscout_all_dataframes.values())
    .groupby("team_name")["match_id"]
    .nunique()
)


total_offsides_per_team = all_offsides.groupby("team_name").size()


offsides_per_game_sorted = (total_offsides_per_team / games_per_team).sort_values(
    ascending=False
)


# remove non-European teams at the top; convert to markdown
print(offsides_per_game_sorted[6:16].round(2).to_markdown())


# ------------------------------------------- #
#       Plot Offside Counts per Player        #
# ------------------------------------------- #

plot_dir = Path("results/plots")
plot_dir.mkdir(parents=True, exist_ok=True)

num_offsides = (
    offsides.groupby("player_name").size().reset_index().rename(columns={0: "offsides"})
)
num_offsides["mins_played"] = num_offsides["player_name"].apply(
    lambda x: mins_played[x]
)


num_offsides["offsides_per_min"] = num_offsides.offsides / num_offsides.mins_played

offsides_per_min_ordered = num_offsides.sort_values(
    by=["offsides_per_min"], ascending=False
)

print(offsides_per_min_ordered)

ax = sns.barplot(
    data=offsides_per_min_ordered,
    x="player_name",
    y="offsides_per_min",
    palette="viridis",
)

ax.set_xlabel("Player")
ax.set_ylabel("Offside Count per Minute")
ax.set_title("Offside Calls per Player in Euro 2024 Qualifiers")

plt.xticks(rotation=90)

plt.tight_layout()
plt.savefig(plot_dir / "offside_count_by_player.png", dpi=300)


# ------------------------------------------- #
#              Offside Animations             #
# ------------------------------------------- #


def get_timestamp(wyscout_timestamp: str, match_period: str) -> int:
    """Parses a timestamp string formatted as "HH:MM:SS:mm" where HH are hours,
        MM are minutes, SS are seconds and mm are milliseconds and calculates
        the corresponding timestamp in milliseconds

    Args:
        wyscout_timestamp (str): wyscout timestamp in "HH:MM:SS:mm" format
        match_period (str): first half ("1H") or second half ("2H")

    Returns:
        int: timestamp in milliseconds
    """
    # Split the string into hours, minutes, and seconds.milliseconds
    parts = wyscout_timestamp.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds, milliseconds = map(int, parts[2].split("."))

    if match_period == "1H":
        return minutes * 60 * 1000 + seconds * 1000 + milliseconds
    else:
        return (
            # subtract first half milliseconds
            hours * 60 * 60 * 1000
            - 45 * 60 * 1000
            + minutes * 60 * 1000
            + seconds * 1000
            + milliseconds
        )


# This function was copied from the skillcorner.ipynb file that wasw provided
# to us in the beginning of the course
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


# This function was copied from the skillcorner.ipynb file that wasw provided
# to us in the beginning of the course
def truncate(float_number, decimal_places):
    """This function truncates a float number to the given decimal places"""
    multiplier = 10**decimal_places
    return int(float_number * multiplier) / multiplier


# This function was copied from the skillcorner.ipynb file that wasw provided
# to us in the beginning of the course. I made some minor changes to it
def plot(
    store_path,
    frame_id,
    timestamp,
    half,
    metadata_df,
    ball_df,
    home_df,
    away_df,
    home_lineup_df,
    away_lineup_df,
    home,
    away,
    visible_area,
    max_ball_z,
):
    match_time = get_match_time(timestamp, half)

    pitch_size = (
        metadata_df["pitch_width"].iloc[0],
        metadata_df["pitch_length"].iloc[0],
    )
    match_date = metadata_df["match_date"].iloc[0].split(" ")[0]
    pitch = VerticalPitch(
        pitch_type="secondspectrum",
        pitch_width=pitch_size[0],
        pitch_length=pitch_size[1],
        line_color="#E2E2E2",
    )

    # we make use of team shirt and number colors provided in the metadata file
    team_shirt_colors = [
        metadata_df["home_team_jersey_color"].iloc[0],
        metadata_df["away_team_jersey_color"].iloc[0],
    ]
    team_number_colors = [
        metadata_df["home_team_number_color"].iloc[0],
        metadata_df["away_team_number_color"].iloc[0],
    ]
    lineups = [home_lineup_df, away_lineup_df]

    fig, ax = pitch.draw(figsize=(pitch_size[0] / 10, pitch_size[1] / 10))

    # The TV broadcast camera view of the pitch (if available) is depicted as a light green polygon.
    corner_coords = []
    for corner in ["top_left", "bottom_left", "bottom_right", "top_right", "top_left"]:
        corner_coords.append((visible_area[f"x_{corner}"], visible_area[f"y_{corner}"]))

    if corner_coords != []:
        pitch.polygon([corner_coords], color="#4c8527", alpha=0.05, ax=ax)

    # Per team, draw the players
    for index, team in enumerate([home_df, away_df]):
        shirt_color = team_shirt_colors[index]
        number_color = team_number_colors[index]
        lineup = lineups[index]
        id2shirt = dict(zip(lineup["player_id"], lineup["player_shirt_number"]))
        for _, player in team.iterrows():
            pnum = id2shirt[player["object_id"]]
            pitch.plot(
                truncate(player["x"], 1),
                truncate(player["y"], 1),
                ax=ax,
                linewidth=0,
                marker="o",
                markersize=20,
                markeredgecolor="black",
                color=shirt_color,
            )

            pitch.annotate(
                pnum,
                xy=(truncate(player["x"], 1), truncate(player["y"], 1)),
                c=number_color,
                va="center",
                ha="center",
                size=11,
                weight="bold",
                ax=ax,
            )

    # Plot the ball
    relative_ball_height = 1 - (
        (max_ball_z - truncate(ball_df["z"].iloc[0], 1)) / max_ball_z
    )
    pitch.plot(
        truncate(ball_df["x"].iloc[0], 1),
        truncate(ball_df["y"].iloc[0], 1),
        ax=ax,
        linewidth=0,
        marker="o",
        markersize=10,
        markeredgecolor="black",
        markerfacecolor=str(max(relative_ball_height, 0)),
    )

    ax.set_title(f"{home} vs. {away} on {match_date}, Half: {half}, Time: {match_time}")

    # Save the figure
    fig.savefig(store_path / f"{frame_id}.png", dpi=160)
    plt.close(fig)


# This function was copied from the skillcorner.ipynb file that wasw provided
# to us in the beginning of the course. I made some minor changes to it
def animate(match_dir, img_dir, f_start, f_end, animate_fps, home, away):
    """Animate the match from the given start frame to the given end frame by concatinating the already drawn images of each team per frame."""
    image_ids = [i for i in range(f_start, f_end)]

    images = []
    for i in image_ids:
        file = img_dir / f"{i}.png"
        if file.is_file():
            images.append(file)
    with iio.get_writer(
        match_dir / f"{home}_{away}_{f_start}_to_{f_end}_animation.mp4",
        format="FFMPEG",
        mode="I",
        fps=animate_fps,
    ) as writer:
        # Loop over the images and write them to the video after concatination of the left and right images
        for index in tqdm(range(len(images))):
            im = iio.imread(images[index])
            writer.append_data(im)


# create dataframe with offside timestamps
offside_timestamps = offsides[["match_id", "match_timestamp", "match_period"]]
offside_timestamps["sc_match_id"] = (
    offside_timestamps["match_id"].astype(str).map(match_ids)
)
# drop rows with missing values as all of the columns need to be complete for
# calculating the timestamp in milliseconds and storing the result in a dictionary
offside_timestamps = offside_timestamps.dropna()

# for each offside position for which we have skillcorner tracking data, save
# the tracking data in a dataframe and insert into offside_plot_dfs dictionary
offside_plot_dfs = {}
for idx, row in offside_timestamps.iterrows():
    df = tracking_dfs[row["sc_match_id"]]
    timestamp = get_timestamp(row["match_timestamp"], row["match_period"])
    df["offside_timestamp"] = timestamp  # add offside timestamp to tracking data
    df["diff_timestamp"] = df.timestamp - timestamp
    df["match_period"] = 1 if row["match_period"] == "1H" else 2
    # get the closest timestamp after the offside event
    offside_plot_dfs[(row["sc_match_id"], timestamp)] = df.query(
        "abs(diff_timestamp) < @MAX_TIMESTAMP_DIFF & half == @df.match_period"
    )


# animate the offside positions
for id, tstamp in offside_plot_dfs.keys():
    offside_plot_df = offside_plot_dfs[(id, tstamp)]

    home = metadata_dfs[id]["home_team"].iloc[0]
    away = metadata_dfs[id]["away_team"].iloc[0]
    date = metadata_dfs[id]["match_date"].iloc[0]
    date = "-".join(date.split(" ")[0].split("/"))
    match_name = f"{home} - {away} - {date}"

    results_dir = Path("results/offsides")
    match_dir = results_dir / match_name / f"{tstamp}"
    img_dir = match_dir / "img"
    # Remove the match directory if it exists
    if match_dir.exists():
        shutil.rmtree(match_dir, ignore_errors=True)

    # Create the match directory to store the results
    match_dir.mkdir(parents=True)
    img_dir.mkdir(parents=True)

    animate_fps = int(metadata_dfs[id]["fps"].iloc[0])
    # in the SkillCorner class in the skillcorner.ipynb notebook,
    # the object id of the ball was assigned to be -1
    ball_df = offside_plot_df.query("object_id == -1")
    frames_df = offside_plot_df.query("object_id != -1")

    f_start = offside_plot_df.frame_id.min()
    f_end = offside_plot_df.frame_id.max()

    home_lineup_df = lineup_dfs[id].query("team_name == @home")
    home_frames_df = offside_plot_df.query(
        "object_id in @home_lineup_df.player_id.unique()"
    )

    away_lineup_df = lineup_dfs[id].query("team_name == @away")
    away_frames_df = offside_plot_df.query(
        "object_id in @away_lineup_df.player_id.unique()"
    )

    for frame_id in tqdm(ball_df.frame_id.unique()):
        home_df = home_frames_df[home_frames_df.frame_id == frame_id]
        away_df = away_frames_df[away_frames_df.frame_id == frame_id]
        ball = ball_df[ball_df.frame_id == frame_id]
        timestamp = list(ball.timestamp)[0]
        half = list(ball.half)[0]
        visible_area = (
            visible_area_dfs[id][visible_area_dfs[id].frame_id == frame_id]
            .drop(columns=["match_id", "frame_id"])
            .iloc[0]
        )
        plot(
            img_dir,
            frame_id,
            timestamp,
            half,
            metadata_dfs[id],
            ball,
            home_df,
            away_df,
            home_lineup_df,
            away_lineup_df,
            home,
            away,
            visible_area,
            max_ball_z_dfs[id],
        )
        animate(match_dir, img_dir, f_start, f_end, animate_fps, home, away)
