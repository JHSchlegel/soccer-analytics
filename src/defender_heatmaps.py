

# =========================================================================== #
#                    Packages and Presets                                     #
# =========================================================================== #
#%%
import json
from tqdm import tqdm
import pandas as pd
from pathlib import Path
import numpy as np
from skimpy import clean_columns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
from PIL import Image
from datetime import datetime
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import os
from typing import Dict
import json
import pandas as pd
import matplotlib.pyplot as plt
from collections import OrderedDict
import warnings
warnings.filterwarnings('ignore') # sanest python user

pd.set_option('display.max_columns', None)

%load_ext blackcellmagic




# =========================================================================== #
#                           Data Loading                                      #
# =========================================================================== #

#%%
# dictionary that creates hash map for skyllcorner vs wyscout match id's
match_ids = {
    # wyscout:skillcorner
    "5414314":"1381503",
    "5414290":"1381473",
    "5414267":"1193645",
    "5414241":"1368349",
    "5414229":"1381427"
}

skyllcorner_ids = [key for key in match_ids.values()]

## skillcorner data
data_dir = Path('data/skillcorner')

#match_id = "1381503"
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
    play_direction_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_play_direction.csv")
    phase_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_phase.csv")
    lineup_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_lineup.csv")
    tracking_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_tracking.csv")
    visible_area_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_visible_area.csv")
    physical_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_physical.csv")
    passes_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_passes.csv")
    on_ball_pressures_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_on_ball_pressures.csv")
    off_ball_runs_dfs[match_id] = pd.read_csv(data_dir / f"{match_id}_off_ball_runs.csv")
    max_ball_z_dfs[match_id] = int(tracking_dfs[match_id].z.max())
#%%

#%%
# stack tracking data
tracking_dfs_conc = pd.concat(tracking_dfs.values())
off_ball_runs_dfs_conc = pd.concat(off_ball_runs_dfs.values())
lineup_dfs_conc = pd.concat(lineup_dfs.values())
#%%


#%% 
wyscout_match_ids = [
    "5414314",
    "5414290",
    "5414267",
    "5414241",
    "5414229",
    "5414204",
    "5414143",
    "5414122"
]

path = Path('data/wyscout')
wyscout_dataframes = {}


for id in wyscout_match_ids:
    json_path = path / f"{id}.json"
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    df = pd.json_normalize(data, record_path=['events'])
    df = clean_columns(df)
    df.name = f"wyscout_{id}"
    wyscout_dataframes[id] = df
#%%



#%%
wyscout_spain_matches = pd.concat(wyscout_dataframes.values())





# =========================================================================== #
#                                Helper Functions                             #
# =========================================================================== #
def get_matchinfo(match_id:int):
    metadata_game = metadata_dfs[str(match_id)]
    length = metadata_game.pitch_length.values[0]
    width = metadata_game.pitch_width.values[0]
    home = metadata_game.home_team.values[0]
    away = metadata_game.away_team.values[0]
    home_score = metadata_game.home_score.values[0]
    away_score = metadata_game.away_score.values[0]
    date = datetime.strptime(metadata_game.match_date.values[0], '%m/%d/%Y %H:%M')
    date_conv = date.strftime('%m.%d.%Y')
    return length, width, home, away, home_score, away_score, date_conv

play_direction_dfs_conc = pd.concat(play_direction_dfs.values())

play_direction_dfs_conc["play_direction"] = play_direction_dfs_conc.play_direction.apply(
    lambda x: 1 if x == "BOTTOM_TO_TOP" else -1
)

play_directions_spain = play_direction_dfs_conc.query("team_name == 'Spain'")

play_directions_dct = {}
for _, (match_id, _, half, play_dir) in play_directions_spain.iterrows():
    if match_id in play_directions_dct:
        play_directions_dct[match_id][half] = play_dir
    else:
        play_directions_dct[match_id] = {}
        play_directions_dct[match_id][half] = play_dir
        
def preprocess_skillcorner_data(
    match_ids:Dict[str, str], 
    tracking_df:pd.DataFrame, 
    dir_dct:Dict[int, Dict[int, int]]
    ):
    tracking_dfs_conc = tracking_df.copy()
    for match_id in match_ids.values():
        match_id = int(match_id)
        play_dir = dir_dct[match_id]
        _, _, home, away, _, _, _ = get_matchinfo(match_id)
        # print(home, away)
        for half, direction in play_dir.items():
            criteria = ("match_id == @match_id & half == @half")
            tracking_dfs_conc.loc[
                tracking_dfs_conc.eval(criteria),
                ["x", "y"]
            ] *= direction
    return tracking_dfs_conc

def frame_to_time(frame_id:int, fps:int=10) -> int:
    return frame_id / fps * 1000


# Function to add the flag to picture
#!!! based on snippet nr 1015 by rufat asadli
def add_flag(fig, flag_path, zoom, position):
    img = plt.imread(flag_path)
    imagebox = OffsetImage(img, zoom=zoom)
    ab = AnnotationBbox(imagebox, position, xycoords='figure fraction', frameon=False)
    fig.add_artist(ab)
    


# =========================================================================== #
#                            Data Preprocessing                               #
# =========================================================================== #
tracking_dfs_conc_cleaned = preprocess_skillcorner_data(match_ids, tracking_dfs_conc, play_directions_dct)

spain_in_possession = (
    pd.concat(phase_dfs.values())
    .query("team_name == 'Spain' & name == 'IN_POSSESSION'")
)


spain_out_possession = (
    pd.concat(phase_dfs.values())
    .query("team_name == 'Spain' & name == 'OUT_POSSESSION'")
)



# =========================================================================== #
#                            Plotting Functions                               #
# =========================================================================== #

def get_coordinates(match_id: int):
    # get out of possession phases for the match that
    match_out_poss = spain_out_possession.loc[
        spain_out_possession.match_id == match_id, :
    ]

    match_in_poss = spain_in_possession.loc[spain_in_possession.match_id == match_id, :]

    match_in_poss["frames"] = match_in_poss.apply(
        lambda row: list(range(row.start, row.end + 1)), axis=1
    )
    match_out_poss["frames"] = match_out_poss.apply(
        lambda row: list(range(row.start, row.end + 1)), axis=1
    )

    in_poss_timestamps = (
        match_in_poss.explode("frames")
        .frames.apply(lambda x: frame_to_time(x))
        .tolist()
    )
    out_poss_timestamps = (
        match_out_poss.explode("frames")
        .frames.apply(lambda x: frame_to_time(x))
        .tolist()
    )

    # player ids of spain players (apart from goalkeepers)
    defenders_object_ids = lineup_dfs_conc.query(
        "match_id == @match_id & team_name=='Spain'"
    ).query("player_position.str.contains('Back')")[["player_id", "player_position"]]

    # order dataframe by player position on the field
    # see: https://stackoverflow.com/questions/23482668/sorting-by-a-custom-list-in-pandas
    defenders_object_ids.player_position = defenders_object_ids.player_position.astype(
        "category"
    )
    order = [
        "Left Wing Back",
        "Left Center Back",
        "Center Back",
        "Right Center Back",
        "Right Wing Back",
    ]
    defenders_object_ids.player_position = (
        defenders_object_ids.player_position.cat.set_categories(order)
    )
    defenders_object_ids = defenders_object_ids.sort_values("player_position")

    coords_list = []
    for timestamps in [in_poss_timestamps, out_poss_timestamps]:
        # need ordered dict to preserve order of defenders
        coords = OrderedDict()
        for _, (id, position) in defenders_object_ids.iterrows():
            # print(id, position)
            coords[str(position)] = tracking_dfs_conc_cleaned.query(
                "match_id == @match_id & object_id == @id & timestamp in @timestamps"
            )[["x", "y"]].values
        coords_list.append(coords)

    return coords_list


def plot_defender_heatmaps(
    pos_data: OrderedDict[str, np.ndarray],
    match_id:int,
    posession:str,
    length: int,
    width: int,
    home: str,
    away:str,
    home_score:int,
    away_score:int,
    date:datetime.date,
    zoom_home:float,
    zoom_away:float,
    save_fig:bool=False,
):
    
    fig, axes = plt.subplots(1, len(pos_data.values()), figsize=(20, 10))
    fig.patch.set_facecolor("gainsboro")

    pitch = VerticalPitch(
        pitch_type="skillcorner",
        line_color="black",
        pitch_color="gainsboro",
        pitch_length=length,
        pitch_width=width,
    )

    plt.suptitle(
        f"{home_score}   -   {away_score}\n\n\n{date} - Spain {posession}",
        fontsize=18,
        fontweight="bold",
        y=0.95,
    )
    add_flag(fig, f"flags/{home}.png", zoom_home, (0.46, 0.94))
    add_flag(fig, f"flags/{away}.png", zoom_away, (0.54, 0.94))
    for ax, (position, coords) in zip(
        axes, pos_data.items()
    ):
        pitch.draw(ax=ax)
        # see: https://stackoverflow.com/questions/62376042/calculating-and-displaying-a-convexhull
        pitch.kdeplot(
            x=coords[:, 0],
            y=coords[:, 1],
            fill=True,
            shade_lowest=False,
            alpha=.5,
            n_levels=10,
            cmap='viridis',
            ax=ax,
        )


        ax.set_title(f"{position}", fontsize=16)

    plt.tight_layout()
    if save_fig:
        save_path = f"results/plots/defenders/{match_id}_{posession}.jpg"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300)
    plt.show()




def plot_all_heatmaps(match_ids:Dict[str, str], zoom_home:float, zoom_away:float, save_fig:bool):
    for match_id in tqdm(match_ids.values()):
        match_id = int(match_id)
        in_pos, out_pos = get_coordinates(match_id)
        pos_dct = {"In Possession": in_pos, "Out of Possession": out_pos}
        length, width, home, away, home_score, away_score, date = get_matchinfo(match_id)
        for posession, pos_data in pos_dct.items():
            plot_defender_heatmaps(
                pos_data,
                match_id,
                posession,
                length,
                width,
                home,
                away,
                home_score,
                away_score,
                date,
                zoom_home,
                zoom_away,
                save_fig,
            )
            
# =========================================================================== #
#                            Plotting Heatmaps                                #
# =========================================================================== #
plot_all_heatmaps(match_ids, 0.05, 0.05, True)