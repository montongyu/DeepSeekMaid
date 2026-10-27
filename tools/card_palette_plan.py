"""Original art-direction map for the 0.8 card recolor prompts; no pixel editing."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
groups={
 'lightning':'ball_lightning barrage capacitor charge_battery energy_surge lightning_mastery lightning_rod storm tesla_coil thunder thunder_strike voltaic zap',
 'frost':'chill cold_snap coolant coolheaded hailstorm hibernate ice_lance glacier',
 'dark':'darkness consuming_shadow null shadow_shield',
 'plasma':'fusion hyperbeam ignition meteor_strike overclock supercritical turbo sweeping_beam flak_cannon',
 'guard':'buffer bulk_up defend_defect defragment compact genetic_algorithm self_repair reboot',
 'glass':'glasswork refract shatter',
 'impact':'adaptive_strike claw feral fight_through focused_strike go_for_the_eyes helix_drill momentum_strike rocket_punch scrape strike_defect sunder',
 'rose':'all_for_one chaos echo_form hologram imitation_learning iteration one_for_all rainbow synthesis uproar',
 'teal':'beam_cell biased_cognition boost_away boot_sequence compile_driver consume creative_ai double_energy dualcast fission ftl gunk_up hotfix leap lock_on loop machine_learning modded multi_cast quadcast scavenge seek signal_boost skim smokestack spinner subroutine synchronize tempest trash_to_treasure white_noise',
}
directions={
 'lightning':'bright lemon yellow and rich gold lightning, deep charcoal background, ivory highlights',
 'frost':'glacial turquoise, jade-cyan ice, frosted silver and white, pale mint backdrop',
 'dark':'amethyst violet, wine-purple shadows and magenta accents, near-black background',
 'plasma':'fiery orange, amber and crimson plasma, warm burgundy backdrop',
 'guard':'emerald green, jade and lime-gold shields/healing, cream and forest backdrop',
 'glass':'iridescent mint green and rose-pink glass with pearl highlights, soft sage backdrop',
 'impact':'coral red, vermilion and warm copper impact arcs, warm peach or red-brown backdrop',
 'rose':'rose-pink, lilac and peach magic, warm ivory backgrounds, rainbow accents only for rainbow',
 'teal':'teal, sea-green and turquoise data glyphs, warm gold details, dark evergreen or pale cream background',
}
index=json.loads((ROOT/'assets/cards/index.json').read_text())
palette={}
for name in index:
    matches=[g for g,ids in groups.items() if name in ids.split()]
    assert len(matches)==1,(name,matches)
    palette[name]={'palette':matches[0],'direction':directions[matches[0]]}
(ROOT/'assets/cards/palette-v0.8.json').write_text(json.dumps(palette,indent=2),encoding='utf-8')
print(json.dumps([[(k,palette[k]['direction']) for k,v in index.items() if v['sheet']==s] for s in range(5)]))
