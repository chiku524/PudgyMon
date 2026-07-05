# ShipHappens — Game Design Document (v0.2)

## Summary

| Field | Value |
|-------|--------|
| **Title** | ShipHappens |
| **Genre** | Online multiplayer / social deduction / physics comedy |
| **Players** | 6–8 (friends, lobby code) |
| **Session** | 22–28 minutes |
| **Camera** | Third-person orbit |
| **Tone** | Full cartoon — ragdoll, slapstick, no gore |
| **Platform** | Windows PC (Steam first) |
| **Roles** | Crew vs Stowaway (1 at 6 players, 2 at 7–8) |
| **Stowaway** | Knows role from round start |

**Elevator pitch:** You and your friends are the worst freight crew in the galaxy. Complete absurd jobs, survive cartoon physics, and catch the Stowaway smuggling space junk before ShipHappens fires you all.

## Design pillars

1. **Friends cause the comedy** — physics, smack talk, bad plans
2. **Readable chaos** — bright colors, big silhouettes, clear UI at 8 players
3. **Short, loud sessions** — 20–30 min, instant “one more round”
4. **Evil but silly** — Stowaway is a gremlin, not a killer
5. **Clip-friendly** — third-person, emotes, post-round blame stats

## Fantasy

**You are:** Crew of ShipHappens Logistics, the galaxy’s worst-rated freight co-op.

**You deliver:** Space goods — bulk slime, inflatable moons, sentient toasters, premium air in cans.

**Stowaway fantasy:** Smuggle hot contraband while the crew does real work.

**Tone:** Full cartoon. “Death” = bonked out → respawn in HR Timeout with a dunce prop.

## Player count & roles

| Players | Crew | Stowaway |
|---------|------|----------|
| 6 | 5 | 1 |
| 7 | 5 | 2 |
| 8 | 6 | 2 |

Stowaway knows from lobby. At 7–8 players, Stowaways do not know each other.

## Session structure

```
Lobby → Loadout → Station drop
    → Jobs + smuggle + sabotage (15–20 min)
    → Emergency Stand-Up Meeting™ (max 3)
    → Final shuttle scramble (3–5 min)
    → Corporate Review (stats, rematch)
```

**Corporate Satisfaction:** Shared team bar; jobs fill it, sabotage/smuggle drain it.

## MVP map: MegaBargain Orbit #12

```
                [ SHUTTLE BAY ]
                      |
           ┌──────────┴──────────┐
           |     CARGO RING      |
           └──────────┬──────────┘
                      |
           [ BREAK ROOM ] ← meetings
                      |
           ┌──────────┴──────────┐
           |     MAIN HUB        |
           └──────────┬──────────┘
                      |
           ┌──────────┴──────────┐
           |     OPS DECK        |
           └──────────┬──────────┘
                      |
           [ JANITOR VENT / CACHE ]
                      |
           [ DOCKING ARM ]
```

## Win / lose

**Crew wins:** ≥7 jobs done, shuttle escape, all Stowaways Written Up or smuggle failed.

**Stowaway wins:** Full smuggle quota + shuttle still leaves, OR Satisfaction hits 0.

**Mutual fail:** Nobody at shuttle in final 60s → Everyone Fired.

## Emergency Stand-Up Meeting™

- 90 seconds in Break Room
- Accuse + vote to Write Up, or Skip (−5% Satisfaction)
- Written Up: dunce hat, one hand for jobs 2 min
- Correct Stowaway Write-Up: revealed, smuggle tools disabled
- Max 3 meetings per round

## Post-round stats

- Falls into slime
- Friends yeeted
- Crates dropped on heads
- Jobs faked / spotted
- Wrong Write-Ups
- **MVP: Most Replaceable**
- **Stowaway Award: Best Straight Face**

## Scope locks (solo dev)

- One map until Steam Early Access
- Eight characters = palette + hat swaps
- Jobs 5, 6, 10 first; Crane last
- No proximity voice v1
- No dedicated servers v1

See also: [CHARACTERS.md](CHARACTERS.md), [JOBS.md](JOBS.md), [STOWAWAY.md](STOWAWAY.md), [ROADMAP.md](ROADMAP.md), [STEAM.md](STEAM.md).
