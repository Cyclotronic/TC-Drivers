# Leo Bodnar LBE-1420 — instrument notes

Behaviour of the receiver worth knowing when using this driver, and the reasoning behind the
parts of the driver that are not obvious from reading it. These are characteristics of the
receiver's NMEA output and of the driver's design.

---

## The receiver is never commanded

It streams NMEA at 9600 8N1 from the moment the port opens. Nothing is sent to it: no
identify, no configuration, no polling. That makes this a read-only driver with no setup
sequence, and it is why there is no page of controls — there is nothing to control.

`#askValues values?` is therefore **not a query to the device**. It hands over whatever the
background frame buffer last collected, so a logged sample is as fresh as the most recent
complete frame rather than the result of a round trip. Two things follow: the first sample
cannot appear until one full frame has arrived, and losing the fix does not interrupt
logging — the receiver keeps streaming, `Fix_Quality` drops, and the position channels stop
meaning anything while the rows keep coming.

---

## Three sentences make one sample, and the starting sentence matters

    #rxStart $GNRMC,
    #rxEnd   \r\n
    #rxCount 3

The receiver's repeating group is `$GNRMC`, `$GNVTG`, `$GNGGA`. Anchoring the frame at
`$GNRMC` locks it to the start of that group, and **that is the load-bearing part of the
framing**: the time and the speed come out of `$GNRMC` while the position comes out of
`$GNGGA`, and only a frame aligned to the group guarantees the two describe the same fix.

Take any three consecutive lines instead and the frame straddles two groups sooner or later,
putting a position from one fix and a time from the next into a single logged row. Nothing
about such a row looks wrong.

`$GNVTG` is inside the frame only because it sits between the two sentences that are used.
Nothing is taken from it.

---

## One regex spans the whole block

`#rxFormat` is a single `(?s)` expression — dot matches newline, so it runs across all three
framed sentences — and it lifts twelve groups in one pass:

| Group | Sentence | Field | Raw form |
| --- | --- | --- | --- |
| 1 | `$GNRMC` | 1 | UTC time, `hhmmss.ss` |
| 2 | `$GNRMC` | 7 | speed over ground, knots |
| 3 | `$GNRMC` | 8 | course over ground, degrees true |
| 4, 5 | `$GNGGA` | 2, 3 | latitude `DDMM.MMMMM`, and `N` or `S` |
| 6, 7 | `$GNGGA` | 4, 5 | longitude `DDDMM.MMMMM`, and `E` or `W` |
| 8 | `$GNGGA` | 6 | fix quality |
| 9 | `$GNGGA` | 7 | satellites used |
| 10 | `$GNGGA` | 8 | HDOP |
| 11 | `$GNGGA` | 9 | altitude above mean sea level, m |
| 12 | `$GNGGA` | 11 | geoid separation, m |

Position is taken from `$GNGGA` rather than from the latitude and longitude that `$GNRMC`
also carries, because `$GNGGA` is the sentence that brings the fix quality, the satellite
count, the HDOP and the two altitudes with it. The `$GNRMC` copies are skipped by the lazy
`.*?` runs between the captures.

The one literal in the middle of the `$GNGGA` captures — `,M,` between altitude and geoid
separation — is the altitude units field. It is matched rather than captured, and it keeps
the two height captures from sliding onto each other's fields.

---

## The conversions are all in `#askValuesMathFormat`

NMEA reports almost nothing in a form worth logging, so every channel except the counts is
converted:

| Raw | Logged as |
| --- | --- |
| `DDMM.MMMMM` with `N`/`S`, `DDDMM.MMMMM` with `E`/`W` | signed decimal degrees, 6 dp |
| speed in knots | km/h, `× 1.852` |
| `hhmmss.ss` | seconds past midnight, so `UTC_Time` displays as a clock |
| empty course field | `0` |

**Degrees and minutes are split by character position, not by arithmetic.** Latitude takes
the first two characters as whole degrees and everything after them as minutes; longitude
takes the first three, because a longitude runs to 180. Minutes are divided by 60 and added,
then the hemisphere letter multiplies the result by `-1` for `S` or `W`. This is why the two
coordinates are not symmetrical expressions in the driver, and why the split cannot be
shared between them.

**An empty course field becomes 0 by prefixing a zero digit.** A stationary receiver leaves
the course field empty, and an empty string is not a number. Prefixing `"0"` before the
conversion turns an empty field into `0` and leaves any real reading alone — `"0" + "123.4"`
parses as `123.4`. So a stationary fix logs a course of 0 rather than failing the sample.
The consequence for a reader is that a course of 0 means either due north or not moving;
`Speed` distinguishes them.

**`UTC_Time` is a count of seconds, displayed as a time.** The channel is declared with the
unit `s` and the `TIME` format, and the conversion is `hh × 3600 + mm × 60 + ss.ss`. It
carries no date — `$GNRMC` has one, in field 9, and the driver does not read it. A log
crossing midnight UTC shows the count restarting from 0.

---

## `#idString $GN` matches the talker ID, not the device

There is no `*IDN?` equivalent on a receiver that is never written to, so there is nothing
device-specific to match on. `#idString $GN` is a prefix match against the NMEA **talker
ID** — `GN` being the combined-constellation talker, as opposed to `GP` for GPS-only or
`GL` for GLONASS-only.

That is intended rather than a shortcut, and it has two consequences worth knowing:

- **Any receiver emitting `$GN` sentences will be identified as an LBE-1420.** Often useful:
  another GNSS receiver with the same repeating group will log through this driver
  unmodified.
- **A receiver that emits `$GP` sentences will not match at all**, and one that emits `$GN`
  in a different repeating group will match and then produce no usable sample: either the
  three framed lines are not the three the regex expects, or the frame never fills. The
  device appears; the rows do not.

---

## Shipped upstream, so unchanged here

TestController has shipped this definition since **V3.48**, 12 August 2026, credited *"Added:
Leo Bodnar LBE-1420 GPS (Thanks Cyclotron)"*
([reply #7197](https://www.eevblog.com/forum/testgear/program-that-can-log-from-many-multimeters/msg6332536/#msg6332536)).
From that point the copy users have is HKJ's, so a change to this driver is a request made
in the thread and not an edit made to the file — which is why revision 1.1 stands here
unchanged, including the request below.

### A rename has been asked for and has not been made

flash2b asks for `#name LBE-1420 GPS` to become `#name Leo Bodnar LBE-1420 GPS`, for
consistency with how the release notes and the device list name it
([reply #7278](https://www.eevblog.com/forum/testgear/program-that-can-log-from-many-multimeters/msg6339466/#msg6339466),
21 August 2026).

It is a reasonable request, and it is not free. `#name` is the key a saved setup uses to find
its device, so anyone already logging this receiver has to reload the definition **and** edit
`settingsLoad.txt` to match — a caveat flash2b raised himself in making the request. That
cost is the reason the change has to go through a release rather than be applied to a local
copy: a renamed local file silently stops matching the setups already on disk.

Until it is made upstream, `#name` in this file is exactly what shipped.
