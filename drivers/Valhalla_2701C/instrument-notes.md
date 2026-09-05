# Valhalla 2701C — instrument notes

Behaviour of the 2701C command set worth knowing when using this driver. These are
characteristics of the instrument, not of TestController. Everything below was confirmed
on a **2701C with Option LNF** over GPIB through a Prologix GPIB-Ethernet gateway, with the
output measured by a Keithley 2002 8½-digit DMM.

The 2701C predates SCPI by some margin. Its command set is a handful of single-letter
opcodes with the argument run directly onto the end — `VO1.5`, `R2`, `T1`, `S` — with no
separators, no query forms, and no acknowledgements.

---

## There is no `*IDN?`, and no query form for anything

The instrument has exactly one thing it will tell you, and it tells you the same thing
however you ask: address it as a talker and it returns its **status word**. There is no
identification string, no error queue, and no query that reads back an individual setting.

`*IDN?` is not rejected — it is simply not understood, and the manual's rule for an
undecipherable command is to ignore it silently (unless SRQ reporting has been enabled with
`Q1`). So a bus scan looking for `*IDN?` sees a device that answers with something that is
not an identity string, which is why an inventory scan lists this instrument as mute.

A read needs no preceding write at all. Any command you do send first is incidental.

## The status word

```
  +1.000000E+0 V  
  +1.000000E+1 V *
```

Format is `SN.NNNNNNEsn xx o`:

| Field | Meaning |
| --- | --- |
| `S` | `+` or `-`, output polarity |
| `N.NNNNNNEsn` | mantissa and signed exponent — `+0.200000E+1` is 2 V |
| `xx` | units: `V`, or `mA` in 120 mA mode |
| `o` | **blank** in OPERATE, `*` in STANDBY |

Two details that matter when parsing it:

- **Leading whitespace is variable.** One or two leading spaces were both observed on the
  same instrument in the same session.
- **The OPERATE case ends in trailing spaces**, because the standby flag position is a
  blank. An end-anchored regex like `[*]$` therefore only works if the reply has already
  been trimmed, and it fails towards reporting OPERATE. A substring test for `*` is safer;
  the character appears nowhere else in the status word.

### The status word is a setpoint, not a measurement

It reports what the calibrator has been **programmed to**, and it is unchanged by STANDBY:
a unit sitting in standby with its output disconnected still reports the last level it was
set to. Confirmed directly — with the status word reading `+0.200000E+1 V *`, the DMM
across the terminals measured **−8.5 µV**.

Do not read a logged level column as evidence that a voltage was actually present at the
terminals. The standby flag is the only field that answers that.

## Writes are fire-and-forget

No command returns an acknowledgement, and there is no error queue to interrogate
afterwards. A malformed command is discarded silently unless `Q1` has enabled SRQ
reporting. The only confirmation that a command took effect is to read the status word back
and look at it.

A command line is limited to **20 characters**; anything longer is discarded whole and
raises an error condition. Commands are acted on when a terminator arrives — either LF or
EOI asserted with the last character.

## `VO` auto-selects OPERATE

Setting a level with `VO` puts the instrument into OPERATE as a side effect — confirmed both
on the wire and in the front-panel state. There is no way to program a level while staying
in standby. If you need the output off, set the level and then send `S`.

`S` (standby) leaves the programmed level untouched, so `S` then a later `V` (operate)
returns the same voltage.

`VO` also auto-ranges, and supersedes any range previously forced with `R`. The `R` command
cannot reach the 200 mV range at all — it exists for compatibility with earlier 2701-series
units and is not the recommended way to drive this one.

## Reply framing and timing

Replies come back as a **single line** terminated `CR,LF`, and a read that waits for EOI
terminates on it promptly. No LF-only workaround is needed.

The `E` command selects the delimiter: `E0` CR,LF · `E1` CR,LF with EOI · `E2` CR · `E3` CR
with EOI · `E4` EOI on the last character. There is no query for the current mode, so the
only way to be sure is to set it.

Settle time from write to the status word carrying the new value, measured:

| Transition | Settle |
| --- | --- |
| Range change (2 V ↔ 20 V) | 14–16 ms |
| Within-range change (10 V → 12 V) | 40 ms |
| OPERATE → STANDBY flag | 25 ms |

That is fast enough that a controller reading back immediately after a write can still lose
the race, since a GPIB-Ethernet gateway round trip is ~20 ms on its own.

## Selecting 4-wire without sense leads gives an uncontrolled output

The `T1` (4-wire) command switches the regulation loop to the SENSE terminals. If those are
not actually landed on the load, the loop runs open and the output is neither correct nor
stable.

Measured on this bench, with a 2 V setpoint:

| Terminal mode | DMM reading |
| --- | --- |
| 2-wire (`T0`) | 1.99994723 V — −26 ppm |
| 4-wire (`T1`), sense not landed | 2.3835–2.3953 V, **drifting +1.7 mV/s** |

Roughly 20 % high and climbing. Nothing about the command fails, the status word still
reports the programmed 2 V, and there is no query to tell you which mode is active — so this
presents as a calibrator that has simply gone wrong. If readings drift after a terminal-mode
change, suspect the sense connection first.

There is no remote query for 2-wire/4-wire state. The front-panel indicator is the only
ground truth.

## Nothing but the level can be read back

There is no query for terminal mode, range, delimiter mode, or SRQ enable. Any UI showing
those is showing what it last wrote, and will drift from the instrument if anyone touches
the front panel. Only the level, units, and OPERATE/STANDBY flag are actually readable.

## Option LNF caps the output at ±40 V

On an LNF (low-noise) unit the switching supply is replaced and the output is limited to
**±40 V** regardless of which range is selected, and the 1200 V range has no calibration
points — Section 8-3 skips those steps on LNF instruments. The 1200 V range therefore
cannot be exercised on such a unit at all.

## Addressing

The GPIB address is set by a 5-pole binary-weighted DIP switch on the rear panel (valid
range 1–30; avoid 0 and 31). **Changing it requires a power cycle** — the new address is
only read into memory at startup.

The instrument will not respond on the bus until its power-up message sequence has
finished, and the manual advises allowing a 3 second settle after a device clear before
any further bus activity.
