# ========================================== #
#               Passing Accuracy             #
# ========================================== #

# ---------------------------------------- #
#         Packages and Presets             #
# ---------------------------------------- #
library(tidyverse)
library(lubridate)
library(jsonlite)
library(janitor)

# for percent format in plots
library(scales)
# for annotating plots with potentially overlapping text
library(ggrepel)


WYSCOUT_PATH = "data/wyscout" 

# some ggplot2 theme I a year ago for a paper I was working on
paper_theme <- function() {
  theme(
    # plot
    plot.title = element_text(
      face = "bold",
      size = rel(.9),
      hjust = .5,
      vjust = 2.5,
      color = "#130f09"
    ),
    plot.subtitle = element_text(size = rel(.7), hjust = .5, margin = margin(b = 10, unit = "pt")),
    plot.caption = element_text(size = rel(.7), hjust = 1),
    plot.background = element_rect(fill = "#FFFFFF", color = NA),
    # panel
    panel.background = element_rect(fill = "#FFFFFF", color = NA),
    panel.border = element_rect("#a5a5a5", fill = "transparent", linewidth = rel(2)),
    panel.grid.major = element_line(colour = "#eeeeee", linewidth = rel(1.2)),
    panel.grid.minor = element_blank(),
    # axis
    axis.ticks = element_line(color = "#a5a5a5"),
    axis.text = element_text(size = rel(.8)),
    axis.title.x = element_text(vjust = -.2),
    axis.title.y = element_text(angle = 90, vjust = 2),
    axis.text.y = element_text(
      size = rel(.8),
      vjust = 0.2,
      hjust = 1,
      margin = margin(r = 3)
    ),
    axis.text.x = element_text(size = rel(.8), margin = margin(2, 0, 0, 0)),
    axis.title = element_text(face = "bold", size = rel(.8)),
    # legend
    legend.position = "bottom",
    legend.background = element_rect(fill = "transparent", color = NA),
    legend.title = element_text(
      face = "italic",
      size = rel(.8),
      hjust = .5
    ),
    legend.direction = "horizontal",
    legend.text = element_text(size = rel(.8), vjust = 1),
    legend.box.spacing = unit(.2, "cm"),
    legend.key = element_rect(fill = "transparent", color = "transparent"),
    legend.key.size = unit(.3, "cm"),
    # facets
    strip.background = element_rect(fill = "#a5a5a5", color = NA),
    strip.text = element_text(
      face = "bold",
      size = rel(.7),
      margin = margin(t = 2.5, b = 2.5)
    )
  )
}

# set this theme globally:
theme_set(paper_theme())



# ---------------------------------------- #
#       Data Preparation and Cleaning      #
# ---------------------------------------- #
# all wyscout ids of the Spain matches
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


wyscout_dfs = list()

# append all wyscout match data for Spain to a list
for (wyscout_id in wyscout_match_ids) {
  json_path = paste0(WYSCOUT_PATH, "/", wyscout_id, ".json")
  wyscout_dfs[[wyscout_id]] = fromJSON(json_path, flatten=TRUE)[["events"]] %>% 
    as.data.frame() %>% 
    clean_names() 
}

# get position player played the most
# otherwise players would appear multiple times in plots below
most_often_pos = bind_rows(wyscout_dfs) %>% 
  filter(team_name == "Spain") %>%
  group_by(player_name, match_id) %>%
  distinct(player_position) %>% 
  ungroup() %>% 
  group_by(player_name) %>% 
  count(player_position) %>%
  top_n(1, n) %>% 
  mutate(player_position_most = player_position) %>%
  select(player_name, player_position_most)


# used wyscout player positions from here:
# https://support.wyscout.com/players-wyid-advancedstats
wyscout = bind_rows(wyscout_dfs) %>% 
  filter(team_name == "Spain", !is.na(player_name)) %>% 
  group_by(player_name) %>% 
  arrange(player_position) %>% 
  left_join(most_often_pos, by = "player_name", relationship =
              "many-to-many") %>%
  mutate(
    player_position_enc = case_when(
      player_position_most == "GK" ~ "Goalkeeper",
      player_position_most %in% c("LCB", "RCB", "CB", "LCB3", "RCB3") ~ "Center Back",
      player_position_most %in% c("LWB", "RWB", "LB", "RB", "RB5", "LB5") ~ "Full Back",
      player_position_most %in% c("DMF", "LDMF", "RDMF") ~ "Defensive Midfield",
      player_position_most %in% c("CMF", "LCMF", "RCMF", "LCMF3", "RCMF3") ~ "Central Midfield",
      player_position_most %in% c("AMF", "LAMF", "RAMF") ~ "Attacking Midfield",
      player_position_most %in% c("LW" , "RW","CF", "LWF", "RWF", "SS") ~ "Forward",
      )
  )

# dictionary for minutes player per player
# manually looked the minutes played up from the uefa website:
# https://www.uefa.com/euro2024/teams/122--spain//squad/
mins_played = c(
  "Álvaro Morata" = 461,
  "Rodri" = 608,
  "Dani Carvajal" = 586,
  "Fabián Ruiz" = 279,
  "Nico Williams" = 222,
  "José Gayá" = 331,
  "Robin Le Normand" = 450,
  "Ferrán Torres"= 272,
  "Íñigo Martínez" = 180,
  "Gavi" = 488,
  "Unai Simón" = 450,
  "Oihan Sancet" = 98,
  "Lamine Yamal" = 205,
  "Rodrigo Riquelme" = 54,
  "Martín Zubimendi" = 112,
  "Mikel Merino" = 372,
  "Alex Grimaldo" = 90,
  "Jesús Navas" = 89, 
  "Pau Torres" = 90,
  "Mikel Oyarzabal" = 207,
  "David Raya" = 90,
  "Joselu" = 235,
  "Aleix García" = 45, 
  "David García" = 180,
  "Aymeric Laporte" = 450,
  "Fran García" = 135,
  "Ansu Fati" = 45,
  "Alfonso Pedraza" = 19,
  "Alejandro Balde" = 164,
  "Bryan Zaragoza" = 44, # for whatever reason showed as 0 in the uefa website
  # thus I used the minutes player from transfermarkt
  "Yéremy Pino" = 158,
  "Álex Baena" = 14,
  "Marco Asensio" = 44,
  "Dani Olmo" = 111,
  "Pedro Porro" = 45,
  "Kepa Arrizabalaga" = 180,
  "Dani Ceballos" = 111,
  "Iago Aspas" = 91,
  "Borja Iglesias" = 24,
  "Nacho Fernández" = 90
)


# ---------------------------------------- #
#       Accuracy vs Mins Played            #
# ---------------------------------------- #
p_accuracy = wyscout %>%
  filter(
    type_primary == "pass",
       team_name == "Spain",
       !is.na(player_name)
  ) %>%
  mutate(mins_played = mins_played[player_name]) %>%
  group_by(player_name, player_position_enc) %>%
  summarize(
    num_passes = n(),
    num_passes_per_min = num_passes / mins_played,
    pass_accuracy = mean(pass_accurate, na.rm = T)
  ) %>%
  # discard duplicates since only interested in num_passes_per_min and pass_accuracy
  slice(1) %>%
  ggplot(aes(x = num_passes_per_min, y = pass_accuracy, color = player_position_enc)) +
  scale_y_continuous(labels = percent_format(accuracy = 1)) +
  geom_point() +
  scale_x_continuous(limits = c(0, 1.5), breaks = seq(0, 1.5, by = 0.25)) +
  # used ChatGPT to find a way to annotate points in a better way than geom_text.
  # Prompt used: "How to avoid overlaps when annotating plots in ggplot in R?"
  geom_text_repel(aes(label = player_name), size = 3, show.legend = F) +
  labs(
    title = "Passing Completion in Euro 2024 Qualifiers",
    x = "Passes per Minute",
    y = "Pass Completion %",
    caption = "Data: Wyscout",
    color = "Position"
  ) +
  # using color palette from aaas from the ggsci package
  # see here for more info about the palette:
  # https://nanx.me/ggsci/reference/pal_aaas.html
  scale_color_manual(
    values = c(
      "Goalkeeper" = "#1B1919FF",
      "Full Back" = "#3B4992FF",
      "Center Back" = "#631879FF",
      "Defensive Midfield" = "#A20056FF",
      "Central Midfield" = "#008280FF",
      "Attacking Midfield" = "#008B45FF",
      "Forward" = "#EE0000FF"
    )
  )

ggsave(
  "results/plots/pass_accuracy.png",
  p_accuracy,
  width = 8,
  height = 6,
  dpi = 300
)


# ---------------------------------------- #
#       Accuracy Under Pressure            #
# ---------------------------------------- #
p_pressure = wyscout %>%
  mutate(
    under_pressure = map_lgl(type_secondary, ~ "under_pressure" %in% .x)
  ) %>%
  filter(
    type_primary == "pass",
    team_name == "Spain",
    !is.na(player_name),
    !is.na(under_pressure),
    !is.na(player_position)
  ) %>%
  mutate(mins_played = mins_played[player_name]) %>%
  group_by(player_name, player_position_enc) %>%
  filter(mins_played >= 135) %>% 
  summarize(
    num_passes = n(),
    num_passes_per_min = num_passes / mins_played,
    pass_accuracy_no_pressure = mean(pass_accurate[under_pressure==F], na.rm = T),
    pass_accuracy_pressure = mean(pass_accurate[under_pressure==T], na.rm = T)
  ) %>%
  # discard duplicates since only interested in num_passes_per_min and pass_accuracy
  slice(1) %>%
  ggplot(aes(x = pass_accuracy_no_pressure, y = pass_accuracy_pressure, color = player_position_enc)) +
  scale_y_continuous(labels = percent_format(pass_accuracy_no_pressure = 1)) +
  geom_point() +
  scale_x_continuous(labels = percent_format(pass_accuracy_pressure = 1)) +
  # used ChatGPT to find a way to annotate points in a better way than geom_text.
  # Prompt used: "How to avoid overlaps when annotating plots in ggplot in R?"
  geom_text_repel(aes(label = player_name), size = 3, show.legend = F) +
  labs(
    title = "Passing Completion Under Pressure in Euro 2024 Qualifiers",
    subtitle = "Spanish players with at least 135 minutes played",
    x = "Pass Completion % (No Pressure)",
    y = "Pass Completion % (Pressure)",
    caption = "Data: Wyscout",
    color = "Position"
  ) +
  # using color palette from aaas from the ggsci package
  # see here for more info about the palette:
  # https://nanx.me/ggsci/reference/pal_aaas.html
  scale_color_manual(
    values = c(
      "Goalkeeper" = "#1B1919FF",
      "Full Back" = "#3B4992FF",
      "Center Back" = "#631879FF",
      "Defensive Midfield" = "#A20056FF",
      "Central Midfield" = "#008280FF",
      "Attacking Midfield" = "#008B45FF",
      "Forward" = "#EE0000FF"
    )
  )

ggsave(
  "results/plots/pass_accuracy_pressure.png",
  p_pressure,
  width = 8,
  height = 6,
  dpi = 300
)

