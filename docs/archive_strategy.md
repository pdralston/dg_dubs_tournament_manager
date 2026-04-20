## Introduction
We setup a new Tab on the admin page for managing season information including the addition of a pending action, "Archive". This document will define the Archive action design. 

## Archive Action

When the user clicks on the Archive button a new modal workflow will be presented. The first page of the modal will be a warning that the "Archive" action is destructive in nature and cannot be reversed if the user decides to continue. The user will then be presented with a "Continue" and "Cancel" option. If the user clicks "Continue" they will be presented with a form requesting a name for the concluded season and presented with some quick stats, such as, date span of the season, number of events conducted, number of unique participants in the season and number of total participants in the season. There are two buttons on the bottom of this page, "Perform Archive" and "Cancel". Once they name the Season and click "Perform Archive" a number of operations will occur as detailed below. The following sections will describe the actions taken and the desired state of the various elements assuming the "Perform Archive" action has been clicked.

## Players

Firstly, any players that do not have any tournament participation listed in their history, should be removed from the database. 

Ratings should be normalized (between the values 900 and 1400) across the remaining players.

The tournament history section will now be a dropdown selection controlled display with the current season always the initial focus. The tournament history for previous seasons should be viewable by selecting the name the admin provided. Teammate history should persist across seasons as it is meant to be a lifetime record of performance based on team pairing. When a user clicks on a tournament in their history page, they should be presented with the tournament details page for that tournament. When a tournament detail page is accessed in this way, the back action should go back to the player detail page. Maybe simply show the tournament detail page as a popup modal on the player detail page instead of going to the tournament tab at all.

We need to introduce some new season and lifetime stats to track per player: Seasonal Cash: amount earned in the current season, Lifetime Cash: amount earned across all historical seasons (adjusted at time of archive) plus the current season earnings, Average Place: current season average tournament placement. This will require updating the database as well. 

## Tournaments
The tournaments list page should only show current season tournaments. This means at the start of the season, only an empty list should be present on this page with the following text: "The season hasn't started yet, but when it does check back here to see all of the completed tournaments!"

## Ace Pot
The ace pot tracker history can be trimmed down to a single entry reflecting the carry over balance from a previous season.