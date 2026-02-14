# ======================================== #
#               Passing Sonars             #
# ======================================== #

#!!! All the code snippets apart from the data loading were first copied 
#!!! from the following source:
#!!! https://github.com/etmckinley/PassSonar/blob/master/StatsBomb%20PassSonars.R
#!!! and then adapted to our specific requirements

# ---------------------------------------- #
#         Packages and Presets             #
# ---------------------------------------- #
library(tidyverse)
library(lubridate)
library(jsonlite)
# to clean column names:
library(janitor)
# for pitch plots:
library(ggsoccer)
# devtools::install_github("FCrSTATS/SBpitch")
# library(SBpitch)
library(viridis)

# packages for image processing in R:
library(magick)
library(grid)

WYSCOUT_PATH = "data/wyscout" 
# round angles to closest x degrees
ROUND_ANGLE = 15
PITCH_COLOR = "#22312b"
LINE_COLOR = "white"

# pitch dimensions
XMAX = 100
YMAX = 70

SONAR_SIZE = 25

# player positions
BACK = 8
MID = 35
FORWARD = 60


# ---------------------------------------- #
#       Data Preparation and Cleaning      #
# ---------------------------------------- #

# hash map for wyscout ids and corresponding skillcorner ids for spain
match_ids_dct = c(
  # Spain Georgia 3-1
  # 4-3-3
  "5414314"="1381503",
  # Cyprus Spain 1-3
  # 4-3-3
  "5414290"="1381473",
  # Norway Spain 0-1
  "5414267"="1193645",
  # Spain Scotland 2-0
  # 4-3-3
  "5414241"="1368349",
  # Spain Cyprus 6-0
  # 4-3-3
  "5414229"="1381427"
)


# all wyscout ids
wyscout_match_ids = c(
  "5414314",
  "5414290",
  "5414267",
  "5414241",
  "5414229",
  "5414204",
  "5414143",
  "5414122"
)

# create dictioary for name conversion of players between skillcorner
# and wyscout
# Note that not all players are in the dictionary since for some games we
# don't have skillcorner data
player_names_dct = c(
  "Álvaro Morata"= "Morata Martín",
  "Dani Carvajal" = "Carvajal Ramos",
  "Nico Williams" = "Williams Arthuer",
  "Robin Le Normand" = "Robin Le Normand",
  "Íñigo Martínez" = "Martínez Berridi",
  "Unai Simón" = "Simón Mendibil",
  "Lamine Yamal" = "Nasroui Ebana",
  "Martín Zubimendi" = "Zubimendi Ibañez",
  "Rodri" = "Hernández Cascante",
  "Fabián Ruiz" = "Ruiz Peña",
  "José Gayá" = "Gayá Peña",
  "Ferrán Torres" = "Torres García",
  "Gavi" = "Páez Gavira",
  "Oihan Sancet" = "Sancet Tirapu",
  "Rodrigo Riquelme" = "Riquelme Reche",
  "Jesús Navas" = "Navas González",
  "Mikel Merino" = "Merino Zazón",
  "David García" = "García Zubiría",
  "Aleix García" = "García Serrano",
  "Alex Grimaldo" = "Grimaldo García",
  "Mikel Oyarzabal" = "Oyarzabal Ugarte",
  "Pau Torres" = "Torres",
  "David Raya" = "Raya Martin",
  "Joselu" = "Sanmartín Mato",
  "Alfonso Pedraza" = "Pedraza Sag",
  "Ansu Fati" = "Fati",
  "Fran García" = "García Torres",
  "Yéremy Pino" = "Pino Santos",
  "Aymeric Laporte" = "Laporte",
  "Alejandro Balde" = "Balde Martínez",
  "Bryan Zaragoza" = "Zaragoza Martínez",
  "Álex Baena" = "Baena Rodríguez"
)


wyscout_dfs = list()

# append all wyscout match data for Spain to a list
for (wyscout_id in wyscout_match_ids) {
  json_path = paste0(WYSCOUT_PATH, "/", wyscout_id, ".json")
  wyscout_dfs[[wyscout_id]] = fromJSON(json_path, flatten=TRUE)[["events"]] %>% 
    as.data.frame() %>% 
    clean_names() %>% 
    mutate(
      angle_round = round(pass_angle / ROUND_ANGLE) * ROUND_ANGLE
    )
}

# load all skillcorner lineups
lineups_lst = list()

for (skillcorner_id in match_ids_dct) {
  lineups_lst[[skillcorner_id]] = read_csv(paste0("data/skillcorner/", skillcorner_id, "_lineup.csv"))
}

# starting lineups of Spain for all matches
spain_lineups = bind_rows(lineups_lst, .id = "match_id") %>% 
  filter(
    start_time == 0,
    team_name == "Spain"
  ) %>% 
  select(match_id, player_first_name, player_last_name, player_position)

# load all skillcorner metadata
metadata_lst = list()
for (skillcorner_id in match_ids_dct) {
  metadata_lst[[skillcorner_id]] = read_csv(paste0("data/skillcorner/", skillcorner_id, "_metadata.csv"))
}

# extract metadata that is important for plots
metadata = bind_rows(metadata_lst) %>% 
  select(match_id, match_date, home_team, away_team, home_score, away_score)




# --------------------------------------------- #
#           Passing Sonar Spain-Georgia         #
# --------------------------------------------- #

#!!! All the code snippets in this section were first copied 
#!!! from the following source:
#!!! https://github.com/etmckinley/PassSonar/blob/master/StatsBomb%20PassSonars.R
#!!! and then adapted to our specific requirements

# Note that the ymin and ymax values are negative since the y-axis has to be 
# inverted for the plot to be shown correctly.


# loop through all maches for which we have skillcorner and wyscout data
for (id in names(match_ids_dct)) {
  wyscout_id = id
  skillcorner_id = match_ids_dct[[id]]

  players = unique(wyscout_dfs[[wyscout_id]] %>% filter(team_name == "Spain") %>% 
                     pull(player_name)) %>% 
    na.omit() # omit interruptions encoded as NA observations
  
  # get starting eleven of the game:
  starting_lineup = bind_rows(lineups_lst, .id = "match_id") %>% 
    filter(
      start_time == 0,
      team_name == "Spain",
      match_id == skillcorner_id
    ) %>%   
    # convert skillcorner name to wyscout player_name
    mutate(player_name = sapply(player_last_name, function(x) names(player_names_dct)[player_names_dct==x])) %>% 
    select(player_name, player_position)
  
  
  # get pass angles and mean pass distance for all players
  sonars = wyscout_dfs[[wyscout_id]] %>% 
    filter(
      type_primary == "pass",
      team_name == "Spain",
      pass_accurate == TRUE
    ) %>%
    group_by(player_name) %>%
    mutate(count = n()) %>%
    ungroup() %>%
    group_by(player_name, angle_round) %>% 
    mutate(n_angle = n() / count) %>%
    ungroup() %>% 
    group_by(player_name) %>% 
    mutate(
      max_count = max(n_angle),
      angle_normalized = n_angle / max_count
    ) %>% 
    ungroup() %>% 
    group_by(angle_round, player_name, team_name, count) %>% 
    summarize(
      angle_normalized = mean(angle_normalized),
      distance = mean(pass_length),
      # prevent outliers from distorting the plot
      distance = ifelse(distance > 27, 27, distance)
    )
   
  
  # where each position should be plotted in the map
  # 4-3-3 formation
  plot_positions_df = data.frame(
    player_position = c(
      "Goalkeeper", "Left Wing Back", "Right Wing Back", "Left Center Back", "Right Center Back",  
       "Left Midfield", "Right Midfield","Defensive Midfield", 
      "Left Forward","Right Forward", "Center Forward"
    ),
    xmin = c(
      -10, BACK+5, BACK+5, BACK, BACK,  MID, MID, MID - 10, FORWARD, FORWARD, FORWARD + 5
    ),
    ymax = c(
      # GK
      50 + SONAR_SIZE / 2, 
      # Defenders
      10 + SONAR_SIZE / 2,
      90 + SONAR_SIZE / 2,
      35 + SONAR_SIZE / 2,
      65 + SONAR_SIZE / 2,
      # Midfielders
      15 + SONAR_SIZE / 2,
      85 + SONAR_SIZE / 2,
      50 + SONAR_SIZE / 2,
      
      # Forwards
      15 + SONAR_SIZE / 2,
      85 + SONAR_SIZE / 2,
      50 + SONAR_SIZE / 2
    )
    
  ) %>% 
    mutate(
      xmax = xmin + SONAR_SIZE,
      ymin = ymax - SONAR_SIZE
    )
  
  
  # Sonar plots of all players; additional plot for the legend:
  sonar_plots = list()
  for (row_idx in 1:nrow(starting_lineup)) {
    player = starting_lineup[row_idx, "player_name"] %>% as.character()
    position = starting_lineup[row_idx, "player_position"] %>% as.character()
    
    sonar = sonars %>% 
      filter(player_name == player)
    
    p = ggplot(sonar)+
      geom_bar(aes(x=angle_round, y=angle_normalized, fill=distance), stat="identity")+
      scale_y_continuous(limits=c(0,1))+
      scale_x_continuous(breaks=seq(-180,180, by=45), limits=c(-180,180))+
      coord_polar(start=pi, direction=1)+
      scale_fill_viridis_c("Distance", limits=c(0,27), na.value="#FDE725FF")+
      labs(x="", y="",title= player)+
      theme_void()+
      theme(plot.title = element_text(hjust=0.5, vjust=-3, face="bold",  color = LINE_COLOR, size = 13),
            legend.position = "none", 
            plot.margin = margin(0,0,0,0, "cm"))
    
    if (row_idx == nrow(starting_lineup)) {
      p_legend = ggplot(sonar)+
        geom_bar(aes(x=angle_round, y=angle_normalized, fill=distance), stat="identity")+
        scale_y_continuous(limits=c(0,0))+
        scale_x_continuous(breaks=seq(-180,180, by=45), limits=c(-180,180))+
        coord_polar(start=pi, direction=1)+
        scale_fill_viridis_c("Mean Pass \nDistance (m)\n", limits=c(0,27), na.value="#FDE725FF")+
        labs(x="", y="")+
        theme_void()+
        theme(legend.position = "bottom", 
              legend.spacing.x = unit(1.5, "cm"),
              legend.title = element_text(color = LINE_COLOR, size = 13),
              legend.text = element_text(color = LINE_COLOR, size = 12),
              plot.margin = margin(0,0,0,0, "cm"))
      sonar_plots[[as.character(row_idx)]] = ggplotGrob(p_legend)
    }
    sonar_plots[[position]] = ggplotGrob(p)
  }
  
  
  # match date as character
  match_date = metadata %>% 
    filter(match_id == skillcorner_id) %>% 
    mutate(match_date = format(mdy_hm(match_date), "%d.%m.%Y")) %>% 
    pull(match_date) %>% 
    as.character()
  
  ## name of home and away team
  home = metadata %>% 
    filter(match_id == skillcorner_id) %>% 
    pull(home_team) %>% 
    as.character()
  
  away = metadata %>%
    filter(match_id == skillcorner_id) %>% 
    pull(away_team) %>% 
    as.character()
  
  ## Score of home and away team
  home_score = metadata %>% 
    filter(match_id == skillcorner_id) %>% 
    pull(home_score) %>% 
    as.character()
  
  away_score = metadata %>%
    filter(match_id == skillcorner_id) %>% 
    pull(away_score) %>% 
    as.character()
  
  # read in home flag and scale to standard size
  home_flag = magick::image_read(paste0("flags/",home,".png")) %>% 
    magick::image_scale(., "600x400") %>% 
    as.raster() %>% 
    rasterGrob()
  
  
  # read in away flag and scale to standard size
  away_flag = magick::image_read(paste0("flags/",away,".png")) %>% 
    magick::image_scale(., "600x400") %>% 
    as.raster() %>% 
    rasterGrob()
  
  # initiate pitch and annotate pitch with flags and score
  p_pitch_sonar = ggplot() +
    annotate_pitch(
      fill = PITCH_COLOR, colour = LINE_COLOR, 
      linewidth = 0.7
    ) +
    theme_pitch() +
    coord_flip() +
    scale_y_reverse() +
    theme(
      aspect.ratio = 100/70, 
      plot.title = element_text(hjust=0.5, color = LINE_COLOR),
      plot.background = element_rect(fill = PITCH_COLOR, color = NA),
      plot.margin = margin(t = 2, b = 20)
    ) +
    ggtitle("") + 
    annotation_custom(grob = home_flag, xmin = 100, xmax = 110, ymin = -60, ymax = -70) +
    annotation_custom(grob = away_flag, xmin = 100, xmax = 110, ymin = -30, ymax = -40) +
    annotation_custom(grob = textGrob(label=paste0(home_score, " - ", away_score), 
             gp=gpar(col = LINE_COLOR, fontsize = 15, fontface="bold")), 
             xmin = 102, xmax = 108, ymin = -43, ymax = -57
    ) +
    annotation_custom(
      textGrob(label=match_date, 
               gp=gpar(col = LINE_COLOR, fontsize = 12, fontface = "bold")), 
      xmin = 105, xmax = 110, ymin = -90, ymax = -100
    )
    
  
  # annotate the pitch with the sonar plots
  for (row_idx in 1:nrow(plot_positions_df)){
    p = sonar_plots[[plot_positions_df[row_idx, "player_position"]]]
    p_pitch_sonar = p_pitch_sonar + annotation_custom(
      grob=p, xmin = plot_positions_df[row_idx, "xmin"], 
      xmax = plot_positions_df[row_idx, "xmax"],
      # multiply by -1 to flip the y-axis; I first forgot to reverse y axis
      # of the pitch and did not want to type everything again
      ymin = plot_positions_df[row_idx, "ymin"] - 100,
      ymax = plot_positions_df[row_idx, "ymax"] - 100
    )
  }
  
  # add legend
  p_pitch_sonar = p_pitch_sonar + annotation_custom(
    grob = sonar_plots[[as.character(11)]], xmin = -12, xmax = -7, ymax = -75, ymin = -25
  ) +
    annotation_custom(
      grob = textGrob(label="Bar length = normalized passing angle frequency", 
                      gp=gpar(col = LINE_COLOR, fontsize = 13)), 
      xmin = -6, xmax = -2, ymax = -70, ymin = -30
    ) 

  
  # save sonar plot
  ggsave(
    p_pitch_sonar, 
    file=paste0("results/plots/sonar_plots/", home, "_", away, "_",home_score, "_", away_score, "_pass_sonar.png"), 
    width=9.5, height=12, dpi=300, bg=PITCH_COLOR
  )
}






















































bind_rows(wyscout_dfs) %>% 
  filter(opponent_team_name == "Scotland") %>% 
  pull(match_id) %>% 
  unique











#### Scottland 2-0 Spain

wyscout_id = "5414143" #id
#skillcorner_id = match_ids_dct[[id]]

players = unique(wyscout_dfs[[wyscout_id]] %>% filter(team_name == "Spain") %>% 
                   pull(player_name)) %>% 
  na.omit() # omit interruptions encoded as NA observations

# get starting eleven of the game:
starting_lineup = bind_rows(lineups_lst, .id = "match_id") %>% 
  filter(
    start_time == 0,
    team_name == "Spain",
    match_id == skillcorner_id
  ) %>%   
  # convert skillcorner name to wyscout player_name
  mutate(player_name = sapply(player_last_name, function(x) names(player_names_dct)[player_names_dct==x])) %>% 
  select(player_name, player_position)


starting_lineup = data.frame(
  player_name = c(
    "Kepa Arrizabalaga", 
    "José Gayá", "Íñigo Martínez", "David García", "Pedro Porro",
    "Mikel Merino", "Rodri",
    "Mikel Oyarzabal", "Dani Ceballos", "Yéremy Pino",
    "Joselu"
    ),
  player_position =c(
    "Goalkeeper", 
    "Left Wing Back",  "Left Center Back", "Right Center Back",  "Right Wing Back",
    "Left CM", "Right CM", 
    "Left Forward", "CAM", "Right Forward", 
    "SS"
  )
)

# get pass angles and mean pass distance for all players
sonars = wyscout_dfs[[wyscout_id]] %>% 
  filter(
    type_primary == "pass",
    team_name == "Spain",
    pass_accurate == TRUE
  ) %>%
  group_by(player_name) %>%
  mutate(count = n()) %>%
  ungroup() %>%
  group_by(player_name, angle_round) %>% 
  mutate(n_angle = n() / count) %>%
  ungroup() %>% 
  group_by(player_name) %>% 
  mutate(
    max_count = max(n_angle),
    angle_normalized = n_angle / max_count
  ) %>% 
  ungroup() %>% 
  group_by(angle_round, player_name, team_name, count) %>% 
  summarize(
    angle_normalized = mean(angle_normalized),
    distance = mean(pass_length),
    # prevent outliers from distorting the plot
    distance = ifelse(distance > 27, 27, distance)
  )


# where each position should be plotted in the map
# 4-3-3 formation
plot_positions_df = data.frame(
  player_position = c(
    "Goalkeeper", "Left Wing Back", "Right Wing Back", "Left Center Back", "Right Center Back",  
    "Left CM", "Right CM", 
    "Left Forward","CAM", "Right Forward", 
    "SS"
  ),
  xmin = c(
    -10, 
    BACK+5, BACK+5, BACK, BACK,  
    MID -10, MID -10, 
    MID + 10, MID + 10, MID + 10, 
    FORWARD + 6
  ),
  ymax = c(
    # GK
    50 + SONAR_SIZE / 2, 
    # Defenders
    10 + SONAR_SIZE / 2,
    90 + SONAR_SIZE / 2,
    35 + SONAR_SIZE / 2,
    65 + SONAR_SIZE / 2,
    # Midfielders
    35 + SONAR_SIZE / 2,
    65 + SONAR_SIZE / 2,
    
    # AM
    15 + SONAR_SIZE / 2,
    50 + SONAR_SIZE / 2,
    85 + SONAR_SIZE / 2,
    
    
    # Forwards
    50 + SONAR_SIZE / 2
  )
  
) %>% 
  mutate(
    xmax = xmin + SONAR_SIZE,
    ymin = ymax - SONAR_SIZE
  )


# Sonar plots of all players; additional plot for the legend:
sonar_plots = list()
for (row_idx in 1:nrow(starting_lineup)) {
  player = starting_lineup[row_idx, "player_name"] %>% as.character()
  position = starting_lineup[row_idx, "player_position"] %>% as.character()
  
  sonar = sonars %>% 
    filter(player_name == player)
  
  p = ggplot(sonar)+
    geom_bar(aes(x=angle_round, y=angle_normalized, fill=distance), stat="identity")+
    scale_y_continuous(limits=c(0,1))+
    scale_x_continuous(breaks=seq(-180,180, by=45), limits=c(-180,180))+
    coord_polar(start=pi, direction=1)+
    scale_fill_viridis_c("Distance", limits=c(0,27), na.value="#FDE725FF")+
    labs(x="", y="",title= player)+
    theme_void()+
    theme(plot.title = element_text(hjust=0.5, vjust=-3, face="bold",  color = LINE_COLOR, size = 13),
          legend.position = "none", 
          plot.margin = margin(0,0,0,0, "cm"))
  
  if (row_idx == nrow(starting_lineup)) {
    p_legend = ggplot(sonar)+
      geom_bar(aes(x=angle_round, y=angle_normalized, fill=distance), stat="identity")+
      scale_y_continuous(limits=c(0,0))+
      scale_x_continuous(breaks=seq(-180,180, by=45), limits=c(-180,180))+
      coord_polar(start=pi, direction=1)+
      scale_fill_viridis_c("Mean Pass \nDistance (m)\n", limits=c(0,27), na.value="#FDE725FF")+
      labs(x="", y="")+
      theme_void()+
      theme(legend.position = "bottom", 
            legend.spacing.x = unit(1.5, "cm"),
            legend.title = element_text(color = LINE_COLOR, size = 13),
            legend.text = element_text(color = LINE_COLOR, size = 12),
            plot.margin = margin(0,0,0,0, "cm"))
    sonar_plots[[as.character(row_idx)]] = ggplotGrob(p_legend)
  }
  sonar_plots[[position]] = ggplotGrob(p)
}


# match date as character
match_date = "28.03.2023"

## name of home and away team
home = "Scotland"

away = "Spain"
## Score of home and away team
home_score = "2"

away_score = "0"

# read in home flag and scale to standard size
home_flag = magick::image_read(paste0("flags/",home,".png")) %>% 
  magick::image_scale(., "600x400") %>% 
  as.raster() %>% 
  rasterGrob()


# read in away flag and scale to standard size
away_flag = magick::image_read(paste0("flags/",away,".png")) %>% 
  magick::image_scale(., "600x400") %>% 
  as.raster() %>% 
  rasterGrob()

p_pitch_sonar = ggplot() +
  annotate_pitch(
    fill = PITCH_COLOR, colour = LINE_COLOR, 
    linewidth = 0.7
  ) +
  theme_pitch() +
  coord_flip() +
  scale_y_reverse() +
  theme(
    aspect.ratio = 100/70, 
    plot.title = element_text(hjust=0.5, color = LINE_COLOR),
    plot.background = element_rect(fill = PITCH_COLOR, color = NA),
    plot.margin = margin(t = 2, b = 20)
  ) +
  ggtitle("") + 
  annotation_custom(grob = home_flag, xmin = 100, xmax = 110, ymin = -60, ymax = -70) +
  annotation_custom(grob = away_flag, xmin = 100, xmax = 110, ymin = -30, ymax = -40) +
  annotation_custom(grob = textGrob(label=paste0(home_score, " - ", away_score), 
                                    gp=gpar(col = LINE_COLOR, fontsize = 15, fontface="bold")), 
                    xmin = 102, xmax = 108, ymin = -43, ymax = -57
  ) +
  annotation_custom(
    textGrob(label=match_date, 
             gp=gpar(col = LINE_COLOR, fontsize = 12, fontface = "bold")), 
    xmin = 105, xmax = 110, ymin = -90, ymax = -100
  )


# annotate the pitch with the sonar plots
for (row_idx in 1:nrow(plot_positions_df)){
  p = sonar_plots[[plot_positions_df[row_idx, "player_position"]]]
  p_pitch_sonar = p_pitch_sonar + annotation_custom(
    grob=p, xmin = plot_positions_df[row_idx, "xmin"], 
    xmax = plot_positions_df[row_idx, "xmax"],
    # multiply by -1 to flip the y-axis; I first forgot to reverse y axis
    # of the pitch and did not want to type everything again
    ymin = plot_positions_df[row_idx, "ymin"] - 100,
    ymax = plot_positions_df[row_idx, "ymax"] - 100
  )
}

# add legend
p_pitch_sonar = p_pitch_sonar + annotation_custom(
  grob = sonar_plots[[as.character(11)]], xmin = -12, xmax = -7, ymax = -75, ymin = -25
) +
  annotation_custom(
    grob = textGrob(label="Bar length = normalized passing angle frequency", 
                    gp=gpar(col = LINE_COLOR, fontsize = 13)), 
    xmin = -6, xmax = -2, ymax = -70, ymin = -30
  ) 


# save sonar plot
ggsave(
  p_pitch_sonar, 
  file=paste0("results/plots/sonar_plots/", home, "_", away, "_",home_score, "_", away_score, "_pass_sonar.png"), 
  width=9.5, height=12, dpi=300, bg=PITCH_COLOR
)


  









