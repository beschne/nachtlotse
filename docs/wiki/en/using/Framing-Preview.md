# Framing Preview

**Deutsch:** [Bildausschnitt](Bildausschnitt)

The framing preview shows how a target sits in your camera frame at its best
time that night.

```bash
uv run lotse frame M31
uv run lotse frame M81 M82 --rig S30P --date 2026-11-14
uv run lotse frame "NGC 7000" --no-survey     # without the sky image
```

In the app, double-click a row in Shortlist, All ranked or Events, or select
it and press Framing preview….

![The framing preview window](https://raw.githubusercontent.com/wiki/beschne/nachtlotse/images/gui-framing.png)

## What you see

The yellow rectangle is your camera frame, calculated from focal length and
sensor. Around the target, the dashed circle shows its size from the
catalog. The catalog has no orientation for elongated objects, so the circle
shows how far the object reaches, not its shape. Other catalog objects
inside the frame are drawn as well.

Behind it is a real sky image (DSS2 color from the CDS image service) when
you're online. North is up and east is left.

## On an alt-az mount

An alt-az mount keeps the camera level with the horizon. The top edge of the
frame points toward the zenith, so the frame sits at an angle to north and
keeps turning through the night. The small arrow marks the direction of the
zenith at the time shown in the title.

The ring of ticks around the frame shows where the top edge points at each
full hour of the dark window while the target is higher than 20°. Hours that
lie close together share one label, like "23–02". This shows at a glance how
much the frame will turn during your session. See [Field Rotation](Field-Rotation).

On an EQ mount the frame doesn't turn. It is drawn with its long side
east-west.

## Several targets

Name several targets to frame them together, for example `lotse frame M81 M82`.
They have to fit into one frame.

## Output files

`lotse frame` prints the numbers and writes a PNG named
`nachtlotse-frame-<target>.png` into the current folder, for example
`nachtlotse-frame-M81+M82.png`. An existing file with that name is
overwritten. `--out` picks a different path. PNG output needs the `charts`
extra. In the app, Export PNG… writes the same image.

Sky images are cached in `.cache/sky_survey/` and never expire. Without
internet and without a cached image, the preview is drawn without one.
