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


pd.set_option('display.max_columns', None)

%load_ext blackcellmagic
%load_ext rpy2.ipython
#%%

#%%
ROUND_ANGLE = 15
#%%



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
#%%

# =========================================================================== #
#                   Calculating Sonars for Plotting                           #
# =========================================================================== #

#%%
spain_throw_ins =  (
    wyscout_spain_matches
    .query("type_primary == 'throw_in'")
    .query("pass_accurate == True")
    .query("team_name == 'Spain'")
)

spain_throw_ins.shape
#%%

#%%
#!!! Translated from R to Python from here:
#!!! https://github.com/etmckinley/PassSonar/blob/master/StatsBomb%20PassSonars.R
sonars = (
    spain_throw_ins
    .assign(
        angle_round = lambda x: x.pass_angle.apply(lambda y: round(y/ROUND_ANGLE)*ROUND_ANGLE),
        count = lambda x: x.shape[0],
        n_angle = lambda x: x.groupby("angle_round").angle_round.transform("count") / x["count"],
        max_count =lambda x: max(x.n_angle),
        angle_normalized = lambda x: x.n_angle / x.max_count,
        avg_angle_normalized = lambda x: x.groupby(["angle_round", "count"]).angle_normalized.transform("mean"),
        avg_distance = lambda x: x.groupby(["angle_round", "count"]).pass_length.transform("mean"),
        distance = lambda x: np.where(x.avg_distance > 30, 30, x.avg_distance),
        thirds = lambda x: pd.cut(x.location_x, bins=[0, 33, 67, 100], labels=["Defensive Third", "Midfield Third", "Attacking Third"]),
    )
)
#%%


# =========================================================================== #
#                        Sonar Plot of Throw-ins                              #
# =========================================================================== #

#%%
%%R -i sonars

library(ggplot2)


sonars$thirds <- factor(
    sonars$thirds, 
    levels = c("Attacking Third",  "Midfield Third", "Defensive Third")
)
p_ti_sonar = ggplot(sonars)+
    geom_bar(aes(x=angle_round, y=angle_normalized, fill=distance), stat="identity")+
    geom_vline(xintercept=0, color="black", size=0.5, linetype="dashed")+
    geom_vline(xintercept=180, color="black", size=0.5, linetype="dashed")+
    scale_y_continuous(limits=c(0,1))+
    scale_x_continuous(breaks=seq(-180,180, by=45), limits=c(-180,180), labels= function(x) paste0(x, "°"))+
    coord_polar(start=pi, direction=1)+
    scale_fill_viridis_c("Mean Throw-in \nDistance (m)\n", limits=c(0,27), na.value="#FDE725FF")+
    labs(x="", y="")+
    theme_bw() +
    facet_wrap(~thirds, ncol = 1) + #, scales="free")+
    theme(
        axis.ticks.y = element_blank(),
        axis.text.y = element_blank(),
        # no outside grid
        panel.border = element_blank(),
        plot.title = element_text(face = "bold", size = 14),
        plot.subtitle = element_text(
            face = "italic", size = 10, colour = "grey50"
        ),
        plot.title.position = "plot"
    )
p_ti_sonar
ggsave("results/plots/throw_in_sonar.png", p_ti_sonar, width=7, height=10)
#%%