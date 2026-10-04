# Field Rotation

**Deutsch:** [Bildfeldrotation](Bildfeldrotation)

An alt-az mount moves up-down and left-right. It keeps the camera level with
the horizon, but the sky turns around the celestial pole. So during a
session the stars slowly rotate in your frame. Smart telescopes like the
Seestar stack such frames by aligning the stars and crop the edges that no
longer overlap.

How fast the frame turns depends on where the target is. Far from the zenith
it's slow, about 0.2 to 0.5° per minute. Near the zenith it gets fast: more
than 1.5° per minute within about 5° of the zenith, and over 20° per minute
within 1°.

## What Nachtlotse does with it

On an alt-az rig, Nachtlotse skips moments when the frame would turn faster
than 1.5° per minute. A target that passes close to the zenith gets a best
time before or after that, or drops out if there is none.

On an EQ mount the frame doesn't turn, so this check doesn't apply.

## Seeing it

The [Framing Preview](Framing-Preview) shows the frame at the best time and a
ring of ticks with its direction at every full hour. For M81 and M82 seen
from the Taunus in early October, the frame turns by more than 110° between
21:00 and 07:00. A one-hour session at the best time turns it by about 13°.

The rotation rate is also printed: "rotating 0.22°/min".
