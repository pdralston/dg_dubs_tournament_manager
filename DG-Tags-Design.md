## DG-Tags Design

### Introduction

The DG-Rater ecosystem aims to be a one-stop shop for organizations to manage their Club/League events. Currently there are two apps serving production traffic, putt.dg-rater.com and dg-rater.com. Recently, I refactored dg-rater.com to add the backend skeleton for DG-Tags, which is what this design doc will describe. The initial task for this design doc will be to decribe the workings of the DG-Tags application in isolation of the other two applications or the overall DG-Rater ecosystem. Once complete further integration of the three webapps into the ecosystem can begin.

### What is a Bag Tag Tournament

When players sign up to be members of Disc Golf clubs, they typically will receive a numbered tag as part of their registration package. This tag acts as a mcguffin of sorts where players can compete with other tag holder with the goal of acheiving a lower tag number or defending their current tag. There are two types of organized tag round, Annual and Monthly.

#### Annual Tag Round

Annual Tag rounds are associated to the annual membership drive where all members received a brand new tag. A competition is held to determine who gets which initial tag, with the previous year's current tag acting as a tie breaker. The available tag pool will always be $$1 => n$$ where *n* is the number of checked-in players (not including non-player registrants).

Non-player registrants are assigned tags from the highest available inventory, separate from the competitive pool. See "Non-Player Tag Assignment" below for the exact ordering rules.

#### Monthly Tag Round

Monthly Tag Rounds, or Monthlies for short, are official rounds ran by the organization throughout the year to give club members an opportunity to earn or defend a lower tag number. A competition is held where participants "turn-in" their current tag which adds that tag number to the available tag pool. The turned-in tag number is used as the tie-braker in the event a tie occurs after results are turned in. The available tag pool will be the set of numbers turned in for that event.

Monthlies also have a same day registration mechanic for non-tag holders. The same information for same day registration of the Annual Tag Round must be collected and the tag number added to the pool will be the smallest next available tag from inventory. This newly assigned tag number becomes the player's `old_tag` for the purposes of distribution and tiebreaking.

**Monthly Registration Flow:** Monthly events do not currently have a pre-registration flow. All players register same-day. Registration is done by searching existing members (by UDisc name) or creating a new member. A duplicate detection check should be performed on new member creation to catch cases where a member lost their tag and needs a replacement — the TD/Admin should be prompted to confirm if a potential duplicate is detected.

#### DNF Handling

A player may DNF (Did Not Finish) due to:
- Not checking in for a pre-registered Annual event (automatically set at Scheduled → In Progress transition)
- Injury or voluntary withdrawal during an event (manually set by TD/Admin)

DNF players' tags remain in the available pool. DNF players are assigned the **highest** tags from the pool, in **descending order based on their previous tag number** (highest prev tag gets the highest available tag from the pool).

### Tag Inventory System

The organization maintains a tag inventory that tracks the total number of physical tags available and which tag numbers have been issued, lost, or are still available.

#### Inventory Model

- **Total Tags**: The total number of tags purchased by the organization for the current season (year). Admin-editable, with a safeguard against setting the value lower than the highest tag currently assigned.
- **Available Tags**: Derived set of tag numbers calculated as: all numbers from 1 to `total_tags`, minus tags currently assigned to active members, minus tags marked as lost/unavailable.
- **Lost/Unavailable Tags**: Individual tag numbers that have been removed from circulation via admin action (e.g., a tag was misplaced and cannot be issued). These are not assigned to any member.

#### Inventory Examples

**Example 1: Annual Event**
Club purchases 100 tags. 45 people pre-register for membership; 30 are players, 15 are non-players. 27 of the 30 players check in, and 15 additional players register same-day (42 total checked-in players). At the conclusion of the event: tags 1-42 are assigned to players via the distribution algorithm, tags 86-100 are assigned to the 15 non-players. Available pool after the event: tags 43-85 inclusive.

**Example 2: Mid-year membership**
5 new members purchase membership. They receive tags 43-47 (lowest available). But tag 51 has been reported lost and marked unavailable by admin. Available pool after: 48-50, 52-85.

#### Tag Issuance Rules

| Context | Tag Assigned |
|---------|-------------|
| Annual event — player (via distribution algorithm) | From pool 1..n |
| Annual event — non-player | Highest available from inventory (see ordering below) |
| Monthly event — same-day new member | Lowest available from inventory (becomes their `old_tag`) |
| Outside events — new membership purchase | Lowest available from inventory |
| Override (admin action) | Any available inventory tag specified by admin |

Organizations should have the option to override the tag number issued, in case a tag is lost from inventory or some other unforeseen issue. Only tags available in inventory should be allowed to be issued.

### Non-Player Tag Assignment (Annual Events)

Non-player registrants are assigned tags from the highest available inventory, following this ordering:

1. **Non-players without a previous year's tag** are assigned first. They receive the highest available tag numbers with no particular ordering among themselves.
2. **Non-players with a previous year's tag** are assigned next. They receive the remaining highest available tags, ordered by their previous year's tag number descending (highest prev tag → highest remaining available tag).

Non-player tag numbers are **not** included in the competitive distribution pool.

### Event Management

#### Event Types

Events store their type explicitly as `annual` or `monthly`. This determines:
- Tag pool logic (1..n vs. turned-in tags)
- Whether pre-registration is expected
- Non-player assignment behavior

#### Event Lifecycle (Status Machine)

```
Pending → Scheduled → In Progress → Complete
```

| Status | Visibility | Description |
|--------|-----------|-------------|
| **Pending** | Admin/TD only | Event is being created. Registration (bulk CSV or manual) is in progress. |
| **Scheduled** | All users | Pre-registration complete. Check-in is open. |
| **In Progress** | All users | Event is running. Awaiting results entry. |
| **Complete** | All users | Results finalized. View-only. |

#### Status Transition Workflows

##### Pending → Scheduled
All pre-registrations are complete. The event becomes visible to unauthenticated viewers.

##### Scheduled → In Progress
This transition triggers automated actions:
1. **Non-player tag assignment (Annual only)**: Non-players are assigned tags per the Non-Player Tag Assignment rules above.
2. **DNF assignment**: Any pre-registered player who has not checked in is marked as DNF.
3. **Card creation (P0.5 — deferred)**: Cards would be generated here based on selected method. For P0, this step is skipped.

##### In Progress → Complete
This transition triggers:
1. **Ambiguity resolution**: If results were imported and player name matches are ambiguous, TD/Admin resolves them.
2. **Tag distribution**: The distribution algorithm runs, assigning new tags to all players (including DNF players per DNF rules).
3. **Inventory update**: Tag assignments are reflected in the org's inventory/member records.

#### Pre-Registration

Registration for the annual tag round is mostly known prior, through a third party site (DGScene.com), and DG-Tags should be able to handle ingesting the registration list from a .csv exported from that site. Registration import is part of the event creation flow — an Admin/TD creates the event, registers players (manually or via CSV import), then advances the event to Scheduled.

The DGScene CSV includes fields: Division, Name, First Name, Last Name, PDGA#, Email, Phone, Entry Fee, Last Year's Tag, Address, City, State, ZIP, Country, Registration Date, Notes. The Division field is used to distinguish players from non-players (it is not related to tag distribution pools).

An example DGScene registration CSV is available at:
`/home/pdralsto/projects/repo/2024-bag-tag-challenge-and-membership-drive-registrations-2026-08-16-csv.csv`

#### Same Day Registration

There may also be same day registrations where a tournament director must collect the member's name, UDisc name, shipping address, email, and previous year's tag number (if they had one). Same-day registrants are automatically checked in.

For Monthly events, same-day registration is done by searching existing members (by UDisc name or name) or creating a new member. A duplicate detection check should be performed on new member creation. A potential duplicate may indicate a member who lost their tag and needs a replacement — the TD/Admin should be prompted to confirm their intention.

#### Member Management and Non-Participant Registration

The registration list ingested from DiscGolfScene will act as the basis for the organization's active member list for that year. This list will inform the number of tags the organization has issued and the next tags that would be available for issue. Some of the registrants may be registered as non-players. Their issued tag numbers should be decided by issuing from the highest tag number the organization has available for that year (see Non-Player Tag Assignment above). These non-player tag numbers are not considered for the available tag pool.

Since the DG-Tags database will serve as the active member list, DG-Tags will also need a mechanism to add a new member for tags purchased outside of the Annual or Monthly events. The tag number issued to a registered member in this way should be the lowest available tag from the inventory.

Personally identifiable information, PII, should not be accessible to Non-Admin users. Tournament directors should be able to enter this information at time of event registration, but cannot view it after the fact. Any updates to a member's personally identifiable information must be affected by an admin.

#### Check-in

Members that have pre-registered for the event may not actually show up for one reason or another. Therefore, there must be a check-in system that will allow TD's to confirm attendance prior to triggering event start. Check-in is tracked as a boolean per registration record (`is_checked_in`). Same-day registrants should be auto-checked in. Any registrants not checked in at the Scheduled → In Progress transition should be assigned a DNF result and allocated a tag number according to DNF rules.

#### Card Creation and Hole Assignment (P0.5 — Deferred)

Card creation is deferred to a fast-follow release. The full design is documented here for reference.

Organizations will be opinionated on how they want to setup cards for the tournament and the app should be able to handle the most common options:
- Player Selected: Players will make up their own cards and select their own starting holes. This does not need to be tracked in app and if tournament directors/admins select this option, no card management features should be shown for the event.
- TD Managed: Tournament Directors or Admins should have the option to organize cards manually, lowest first or serpentine. The pieces of information needed for the automated allocations will be:
  -  Minimum Card Size
  -  Number of holes on the course
  -  Desired gap between cards (default 0)
  -  Serpentine or Lowest first pattern
  -  Shotgun or Tee Time style (Shotgun limits number of cards to number of holes. Tee Time style will require additional inputs of time gap between cards, first card start time, and desired end time)  

##### Card Creation Methods

- Manual
  -  TD's will drag and drop players into cards or assign a card number to a player via the UI.
  -  TD's can select how many empty cards to create initially or add/remove cards individually
  -  TD's can manually assign either a starting hole or a starting time
- Lowest First
  -  Players are added to cards starting from the lowest tag number to the highest, filling each card before adding players to the next.
  -  Maximum number of cards is limited based on Shotgun or Tee Time Style
  -  Cards must have a minimum number of players to be considered valid, smaller cards should be broken up and redistributed to existing cards, ignoring card capacity (known as 'super groups') as needed and filling evenly from earliest card/starting hole to latest
  - Default Initial capacity on cards is 4 (configurable by TD/Admin)
- Serpentine
  -  Similar to lowest first but cards are filled out in the pattern lowest seed to first card, second lowest to second card, wrapping back to the first card when the nth seed is added to the nth card where n is the maximum card. 
  - Repeat until all players are assigned to a card.
  - Verify all cards are valid by ensuring that every card has the minimum required players, shifting as necessary and removing empty cards, to make sure all cards are valid. 

#### Payouts (P1 — Deferred)

Some organizations may want to offer a payout structure for their events. This is not a P0 feature and will be designed at a later time.

#### Results

Results can be manually entered or parsed from a CSV or XLSX file exported from UDisc. Files from other event score keeping applications can be used, but the expected headers will be consistent with what UDisc provides. Both CSV and XLSX formats are supported.

An example UDisc results file is available at:
`/home/pdralsto/projects/repo/svdgc-monthly-bag-tag-svdgc-tags-september-2025-2025-09-06.xlsx`

When importing results from a csv/xlsx file, players are matched on the UDisc name field. If there are ambiguities between the results data and the checked-in players then TD's/Admins should be able to manually map the results that could not be automatically resolved.

#### Tag Distribution Algorithm

The distribution algorithm assigns new tags based on event type:

**Monthly Events:**
1. Collect `available_tags` = set of `old_tag` values from all registered players (including DNF players)
2. Sort `available_tags` ascending
3. Separate players into two groups: finished players (have scores) and DNF players
4. Sort finished players by: `round_score` ASC, then `old_tag` ASC (tiebreaker)
5. DNF players get the **highest** tags from the sorted pool, ordered by `old_tag` descending (highest prev tag → highest available)
6. Remaining tags (after removing DNF assignments) are zipped with sorted finished players: lowest tag → best score

**Annual Events:**
1. `available_tags` = 1..n where n = number of checked-in players
2. Sort `available_tags` ascending
3. Separate players into finished and DNF groups
4. Sort finished players by: `round_score` ASC, then previous year's tag ASC (tiebreaker)
5. DNF players get highest tags from pool, ordered by previous year's tag descending
6. Remaining tags zipped with sorted finished players

### Permissions

#### Admins

Admins are allowed all CRUD operations and access to PII and Member/Event Management functions. Admin-only actions include:
- Viewing/updating member PII
- Managing tag inventory (set total, mark tags lost/unavailable)
- All TD capabilities

#### Tournament Directors

TD's are allowed to:

-  Create new events
-  Register new players (same-day or pre-registration)
-  Import registration list from CSV file
-  Check in players
-  Advance event status (Pending → Scheduled → In Progress → Complete)
-  Enter results manually or via CSV/XLSX import
-  Modify player ↔ non-player status during Scheduled state

#### Viewers (Unauthenticated Users)

Unauthenticated users may view:
- Events in Scheduled, In Progress, or Complete status
- Current tag standings
- Event results and tag history

Events in Pending status are not visible to unauthenticated users.

### Member Management and Messaging

Member management and messaging will be a P1 feature.

### Data Model Summary

#### TagEvent
| Field | Type | Notes |
|-------|------|-------|
| event_id | int, PK | |
| event_type | enum: annual, monthly | Determines pool logic |
| date | date | |
| course | string | |
| status | enum: pending, scheduled, in_progress, complete | |
| notes | text | |
| created_at | datetime | |

#### TagRegistration
| Field | Type | Notes |
|-------|------|-------|
| reg_id | int, PK | |
| event_id | int, FK | |
| member_id | int, FK | |
| is_player | boolean | True = competing, False = non-player |
| is_checked_in | boolean | Auto-true for same-day registrants |
| is_dnf | boolean | Set at Scheduled → In Progress for no-shows, or manually |
| old_tag | int | Tag brought to event (or newly assigned for same-day) |
| round_score | int, nullable | Filled after scoring |
| new_tag | int, nullable | Computed after distribution |
| position | int, nullable | Finishing position |

#### TagInventory
| Field | Type | Notes |
|-------|------|-------|
| inventory_id | int, PK | |
| season_year | int | Calendar year |
| total_tags | int | Total physical tags purchased |

#### TagUnavailable (lost/retired tags)
| Field | Type | Notes |
|-------|------|-------|
| id | int, PK | |
| season_year | int | |
| tag_number | int | The specific tag marked unavailable |
| reason | string | Optional: "lost", "damaged", etc. |
| created_at | datetime | |

#### TagMember (updated)
| Field | Type | Notes |
|-------|------|-------|
| member_id | int, PK | |
| name | string | Full display name |
| udisc_name | string, nullable | For CSV matching |
| current_tag | int, nullable | Currently held tag number |
| is_active | boolean | |
| joined_at | datetime | |

#### MemberContactInfo (PII — separate table)
| Field | Type | Notes |
|-------|------|-------|
| member_id | int, PK/FK | |
| email | string | |
| shipping_address | text | |
| payment_method | string | |
| updated_at | datetime | |
