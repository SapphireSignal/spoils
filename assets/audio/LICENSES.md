# audio licenses & credits

everything in this folder is licensed third-party audio. everything else the
game plays (ui blips, door thunks, sniper crack, flashlight click, splash
ping, rain bed, car alarm) is synthesized at runtime and needs no license.

## menu music

- `music/menu_theme.ogg` — "guitar 01 (loopeable)", and
  `music/raid_0..2.ogg` — "guitar 02" / "harp 01" / "piano 01"
  (loopeable, user-auditioned picks), all from **"the last"
  post-apocalyptic/ambient music asset pack by davidkbd**
  https://davidkbd.itch.io/the-last-post-apocalypticambient-music-asset-pack
  license: **cc-by 4.0** — credit: *music by davidkbd*.
  the rest of the pack is a good fit for later milestones (raid ambience,
  hideout); re-download from the page above if needed.

## footsteps

- `steps/*.ogg` — from **"footsteps on different surfaces" by congusbongus**
  https://opengameart.org/content/footsteps-on-different-surfaces
  license: **cc-by 3.0**, itself mastered from freesound.org recordings:
  - concrete (pack folder "boots") + asphalt ("tile"): derived from
    footstep-concrete.wav by **swuing** (freesound #38873); tile also uses
    squeaky footstep.wav by **ceberation** (freesound #235524)
  - wood: derived from footstep-wood.wav by **swuing** (freesound #38876)
  - grass: derived from footstep-grass.wav by **swuing** (freesound #38874)
  - dirt (pack folder "gravel"): derived from the gravel footsteps pack by
    **ali_6868** (freesound pack 21608, cc0)
  files were renamed per game surface and peak-normalized to a uniform quiet
  level; no other edits.

## thunder

- `thunder_0..2.ogg` — three short cuts (8 s, faded, normalized) from
  **"thunder / lightning ambience — field recording" by gregor quendel**
  https://opengameart.org/content/thunder-lightning-ambience-field-recording
  license: **cc-by 4.0** — credit: *thunder recording by gregor quendel*.

## car sounds

- `car/car_door_open.ogg`, `car/car_door_close.ogg`,
  `car/car_engine_start.ogg`, `car/car_engine_loop.ogg`,
  `car/car_engine_off.ogg` — from **"car sound effects pack (low quality)"
  by ggbotnet** https://opengameart.org/content/car-sound-effects-pack-low-quality
  license: **cc0** (public domain, no credit required — credited anyway).
  files renamed from the pack's TitleCase. **`car_engine_loop.ogg` was edited
  in v0.6.78** to make it a seamless loop: its tail is crossfaded onto its head
  over 300 ms and dropped, taking it from 2.966 s to 2.666 s. The original
  looped with a step 5.6x larger than anything in the body of the waveform, so
  it clicked once per loop — audible at idle every 2-3 seconds. cc0 permits
  modification; recorded here because a licence file should say when a shipped
  file is no longer the source file.

## credit line (readme + any published build)

> music by davidkbd (cc-by 4.0) - footsteps by congusbongus and freesound
> contributors swuing, ceberation, ali_6868 (cc-by 3.0) - thunder by gregor
> quendel (cc-by 4.0) - car sounds by ggbotnet (cc0)
