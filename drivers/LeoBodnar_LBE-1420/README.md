# Leo Bodnar LBE-1420 GPS/GNSS Receiver

TestController driver for the **LBE-1420**, read over a serial port at 9600 8N1 as a
passive NMEA stream.

The receiver is **never commanded**. It emits NMEA continuously from the moment the port
opens, so the driver has no setup sequence, no mode pages and no controls — it frames the
stream, parses it, and logs ten channels.

| | |
| --- | --- |
| **Driver** | [`LeoBodnar_LBE-1420.txt`](LeoBodnar_LBE-1420.txt) |
| **Revision** | 1.2 |
| **Interface** | Serial, 9600 8N1 |
| **Instrument notes** | [`instrument-notes.md`](instrument-notes.md) |

---

## TestController already ships this driver

This definition was submitted upstream and HKJ ships it in **TestController V3.48**
(12 August 2026) as `LeoBodnarLBE-1420.txt`. The release notes read *"Added: Leo Bodnar
LBE-1420 GPS (Thanks Cyclotron)"*
([reply #7197](https://www.eevblog.com/forum/testgear/program-that-can-log-from-many-multimeters/msg6332536/#msg6332536)).

So on V3.48 or later you have it already, and the copy here is published for reference and
for anyone on an earlier release. It is revision 1.2, which differs from the shipped
definition in one line: `#name` reads `Leo Bodnar LBE-1420` rather than `LBE-1420 GPS`,
after a rename was asked for in the thread. That rename is not in any TestController release
— V3.48 still ships the old name — so it is made here and requested upstream, no further
than that. See [`instrument-notes.md`](instrument-notes.md).

**What that does and does not tell you.** No TestController distribution was available to
diff against, so below the header this is the definition *as submitted*, that one `#name`
line aside, rather than a file checked byte for byte against the one in the release. Assume
they are otherwise the same, and treat that as unchecked rather than confirmed.

Either way the shipped copy is the one users have, so changing what they run is a release
HKJ makes and not an edit made here. The edit here changes this copy only; the request for
the shipped one is open in the thread — see [`instrument-notes.md`](instrument-notes.md).

Both files claim the same `#idString`, and only one can win the match — the differing `#name`
does not let them coexist — so keep just one of the two in your `Devices` folder.

---

## Logged channels

Ten values, all read-only, taken from two of the three NMEA sentences in the receiver's
repeating group.

| Channel | Unit | From | Meaning |
| --- | --- | --- | --- |
| `Latitude` | — | `$GNGGA` 2, 3 | signed decimal degrees to 6 dp; south is negative |
| `Longitude` | — | `$GNGGA` 4, 5 | signed decimal degrees to 6 dp; west is negative |
| `Satellites` | — | `$GNGGA` 7 | satellites used in the fix |
| `Altitude` | m | `$GNGGA` 9 | altitude above mean sea level |
| `Speed` | km/h | `$GNRMC` 7 | speed over ground, converted from knots |
| `HDOP` | — | `$GNGGA` 8 | horizontal dilution of precision |
| `UTC_Time` | s | `$GNRMC` 1 | seconds past midnight UTC, displayed as a time |
| `Fix_Quality` | — | `$GNGGA` 6 | 0 none, 1 GPS, 2 DGPS/SBAS, 4 RTK |
| `Geoid_Separation` | m | `$GNGGA` 11 | geoid height relative to the WGS-84 ellipsoid |
| `Course` | Deg | `$GNRMC` 8 | course over ground, degrees true |

Nothing arrives in a form worth logging, so the driver converts everything: `DDMM.MMMMM`
plus a hemisphere letter becomes signed decimal degrees, knots become km/h, and
`hhmmss.ss` becomes seconds past midnight so that `UTC_Time` displays as a clock rather
than as a number. The arithmetic is in
[`instrument-notes.md`](instrument-notes.md).

`Course` reads **0 when the receiver is stationary** — NMEA leaves the course field empty
with no motion to report, and the driver substitutes 0 rather than failing the sample. A
genuine due-north heading also reads 0, so the two are not distinguishable from this
channel alone; `Speed` tells them apart.

`Fix_Quality` is worth charting alongside anything else being logged. The receiver keeps
streaming through a lost fix rather than going quiet, so a run does not stop — the position
channels simply stop being meaningful, and this is the channel that says when.

---

## Read this before logging with it

**One sample is three sentences.** The frame starts at `$GNRMC` and takes three lines, which
is what keeps the time and speed from `$GNRMC` and the position from `$GNGGA` in the same
logged row. Do not change the framing directives to sample faster; they are what makes a row
internally consistent. See [`instrument-notes.md`](instrument-notes.md).

**Logging reads a buffer, not the device.** `#askValues values?` hands over whatever the
background frame buffer last collected, so a sample is as fresh as the last complete frame
rather than a round trip to the receiver.

**The match is on the NMEA talker, not on the device.** `#idString $GN` is a prefix match
against the combined-constellation talker ID, because the receiver has no `*IDN?`
equivalent to interrogate. Any receiver emitting `$GN` sentences will be identified as an
LBE-1420 — intended, and useful if you have another GNSS receiver to log — but a GPS-only
receiver emitting `$GP` sentences will not match at all.

---

## Installing

Copy [`LeoBodnar_LBE-1420.txt`](LeoBodnar_LBE-1420.txt) into your TestController `Devices`
folder and restart, and remove the shipped `LeoBodnarLBE-1420.txt` if it is there — see
above. Then add the device on the serial port the receiver is on, at 9600 baud; it is
identified from the sentences it is already streaming, so nothing has to be sent to it
first.

If you are replacing the shipped definition and already have setups logging this receiver,
edit `settingsLoad.txt` as well: a saved setup finds its device by `#name`, and the name in
this revision is not the one that shipped.
