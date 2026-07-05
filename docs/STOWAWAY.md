# Stowaway Playbook

## Win conditions

- [ ] 3/3 contraband in **Hidden Cache** (janitor vent)
- [ ] Shuttle leaves OR Corporate Satisfaction hits 0
- [ ] Avoid correct Write-Up (or win anyway if quota met)

## Contraband

| ID | Item | Best window | Route | Risk |
|----|------|-------------|-------|------|
| S1 | Galactic Hot Dog crate | Crane chaos | Cargo → vent | Medium |
| S2 | Bootleg Chirp-O-Matic | Vending Restock panel | Break Room → vent | High (squeak) |
| S3 | Unlicensed Mini-Bot | Power Hour blackout | Ops locker → vent | Medium |
| S4 | Holo-Autograph | Wrong crate during Crane | Cargo → vent | High (glitter) |
| S5 | Mislabeled Air-in-a-Can | Manifest terminal alone | Hub → vent | Low |

## Zone routes

```
CARGO RING ──high traffic──► MAIN HUB ──leg cams──► BREAK ROOM
     │                            │
     ▼                            └── meeting trap
JANITOR VENT ◄── Hidden Cache ──► OPS DECK
     │
     ▼
DOCKING ARM (tether section)
```

## Tools (MVP)

| Tool | Effect | Cooldown |
|------|--------|----------|
| Fake Badge | Job terminal shows “working” 10s | 60s |
| Rubber Duck Deploy | Blocks hallway + squeak | 90s |
| Label Swappinator | Wrong door sign | 120s |

## Sabotage

| Sabotage | Effect | Cooldown |
|----------|--------|----------|
| Jazz Protocol | PA loud jazz | 90s |
| Gravity Hiccup | Low-G bounce 30s in one zone | 120s |
| Door Whoopsie | Lock random door 20s | 60s |
| Slime Spill | Trail in Cargo Ring | 90s |
| Shuttle Delay | +30s final ramp timer | Once |

Max **2 active sabotages** at once. No killing.

## Play styles

**Safe gremlin:** Fake paperwork → S5 label swap → vent cache → rubber duck in meeting.

**Chaos agent:** Jazz during Trust Fall → steal S1 on crane fail → slime spill → blame Grom.

**Double Stowaway (7–8p):** Alternate sabotage cooldowns; one fakes, one smuggles; never stack meetings.

## Evidence trail (crew can cite)

- Printer duplicate logs
- Scanner hot-dog ping
- Glitter trail (S4)
- Squeak audio (S2)
- Mop “done” but puddles remain
- Leg-cam: near vent 3× without mop

## Meeting outcomes

- **Wrong crew Write-Up:** Stowaway gets +1 smuggle progress equivalent
- **Correct Stowaway Write-Up:** Revealed; smuggle tools disabled
- **Skip vote:** −5% Satisfaction
