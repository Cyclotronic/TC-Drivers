# HP / Agilent 6060B — instrument notes

Behaviour of the 6060B command set worth knowing when using this driver. These are
characteristics of the instrument and the driver's design, not of TestController.
Everything below was confirmed on a **6060B** (firmware `A.02.01`) over GPIB.

The 6060B is a 1993-era instrument. Its command set is SCPI-shaped but predates the
`CONFigure` / `STATus`-heavy model of later loads, and several keywords the manual
implies do not exist on this firmware.

---

## Modes

### The mode is a keyword suffix, not a parameter

`MODE:CURR`, `MODE:VOLT`, `MODE:RES` select constant current, voltage and resistance.
The space form `MODE CURR` is **accepted and then silently ignored** — no error is
queued and `MODE?` still reports the previous mode. The driver only ever sends the
colon form.

`MODE?` answers `CURR` / `VOLT` / `RES`. `FUNCtion`, documented as an alias for `MODE`,
returns `-113,"Undefined header"` on this firmware and is not used.

### Changing mode briefly opens the input

Selecting a new mode takes the input through a non-conducting state for a few
milliseconds so the transition does not overshoot. Settings not associated with the new
mode are left alone.

---

## Ranges

### Constant current: two ranges, picked by the value written

There is no range keyword. `CURR:RANG` takes a current: any value up to 6 selects the
**6 A** range, anything above selects the **60 A** range. The Current, Transient Level
and Triggered Level ceilings follow the selected range, and the driver's Range radio
re-reads those fields when it changes.

| CC range | Setpoint | Resolution |
| --- | --- | --- |
| Low  | 0–6 A  | 1.6 mA |
| High | 0–60 A | 16 mA  |

### Constant resistance: three ranges, and the limits move with them

`RES:RANG` takes a resistance: `1` / `1000` / `10000` select the low / middle / high
range. `RES?` `MIN` and `MAX` then report that range's own span, and a value outside it
is accepted by the interface and quietly clamped by the load.

| CR range | Nominal (manual) | Instrument (`RES? MIN` / `MAX`) |
| --- | --- | --- |
| Low    | 0.033–1 Ω  | ~0–1.17 Ω    |
| Middle | 1–1000 Ω   | 1.17–1170 Ω  |
| High   | 10–10000 Ω | 11.7–11700 Ω |

The instrument's per-range ceiling sits about 17 % above the nominal figure. The driver
uses the instrument's ceiling as each range's maximum and the nominal figure as its
minimum, so a value the load snaps to on a range change never lands outside the
declared span.

**Changing the CR range re-scales the present settings.** If the current setpoint does
not fit the new range, the load moves it to the nearest edge — switch from middle to
low and a 1111 Ω setting becomes 1.170 Ω (the low-range maximum).

### Constant voltage has one range

0–60 V is the operating span; the instrument accepts up to 70 V without error. Setpoint
resolution is 16 mV.

---

## Slew rate

`CURR:SLEW` (A/s) and `VOLT:SLEW` (V/s) each snap the programmed value to **one of 12
discrete hardware steps**. A value outside the programmable span is clamped with no
error — the manual notes there are no upper or lower limits that raise one. Read the
value back to see where it landed.

    CURR:SLEW  1e3 – 5e6   A/s   (0.001 – 5 A/µs)
    VOLT:SLEW  1.2e3 – 5.8e6 V/s

### Constant resistance has no slew command of its own

`RES:SLEW` returns `-113,"Undefined header"`. In the **low** resistance range the load
uses the CV slew rate (`VOLT:SLEW`); in the **middle and high** ranges it uses the CC
slew rate (`CURR:SLEW`). The driver has no CR slew field for this reason — set it on
the CV or CC slew field according to the range, as the field tips say.

---

## Setpoint resolution degrades with magnitude

In the middle and high CR ranges the main and transient levels quantise more coarsely
as the value rises: `RES 600` on the middle range reads back as `588.240`. The
displayed value is the closest step the load can produce. The same applies to the
increment keys. This is expected; it is not the driver rounding.

---

## Transient operation

`TRAN ON` / `OFF` switches transient operation, which alternates the input between the
active mode's main level and its transient level at that mode's slew rate.

`TRAN:MODE` is `CONT` (continuous pulse train), `PULS` (one pulse per trigger) or `TOGG`
(flip on each trigger). Only continuous can be set from the front panel; all three are
available over GPIB.

| Parameter | Command | Range |
| --- | --- | --- |
| Frequency (continuous) | `TRAN:FREQ` | 0.25 – 10 000 Hz |
| Duty cycle (continuous) | `TRAN:DCYC` | 3–97 % below 1 kHz, 6–94 % above |
| Pulse width (pulsed) | `TRAN:TWID` | 50 µs – 4 s |

---

## Input and short

`INPut ON` / `OFF` is the load's Input key; `INP?` answers `0` / `1`. `OUTPut`,
documented as an alias, returns `-113` here and is not used.

`INPut:SHORt ON` / `OFF` simulates a short across the input using the active mode and
range slew rate. `INPUT OFF` takes precedence over `SHORT ON`. The manual warns this
can damage the device under test.

---

## Software over-current protection

`CURR:PROT` sets a current limit (0 to about 61.2 A — `CURR:PROT? MAX` on this unit),
`CURR:PROT:DEL` a delay (0–60 s), and `CURR:PROT:STAT ON` / `OFF` arms it. When armed,
input current above the limit for longer than the delay shuts the input off. It applies
in every mode, not just CC.

**A trip is cleared with `INPut:PROTection:CLEar`.** `CURR:PROT:CLE`, which the manual's
structure implies, returns `-113,"Undefined header"`.

---

## Status and error reporting

### An unimplemented keyword answers with silence

A keyword this firmware does not implement produces **no response at all** and leaves
the read pending. Over a gateway that reads after every command, the timeout then
shifts later replies onto the wrong command and the session looks flaky rather than
wrong. Query `SYST:ERR?` to tell a rejected command from a slow one — on this family
the `-113` or `-420` surfaces on the *next* error read, one command late.

### Protection status decode is not established

`STAT:QUES:COND?` reports a bitmask of questionable conditions — over-current,
over-voltage, over-temperature, reverse voltage. The per-bit meaning has **not been
confirmed on this instrument**, so the driver's Protection Status indicator only
distinguishes `0` (healthy) from non-zero (fault) and shows the raw code. Forcing each
trip and reading the value back is the way to name the bits.

### Compound measurement queries must be fully qualified

TestController splits `#askValues` on `;` and sends each part as its own command, so a
continuation like `MEAS:VOLT?;CURR?;POW?` returns nothing for the second and third.
Write `MEAS:VOLT?;MEAS:CURR?;MEAS:POW?`.

---

## `*RST` does not switch the input off

On this instrument `*RST` resets the setpoints but **leaves the input in whatever state
it was in**. The driver's Output Off action and its disconnect command both send
`INPut OFF` explicitly rather than relying on a reset.

Reset defaults, for reference: `MODE CURR`, `CURR:RANG` 60 A, `CURR:SLEW` at maximum,
`VOLT` 70, `RES` 1111.1 on the middle range, transient off in `CONT` mode at 1 kHz /
50 %, `CURR:PROT` 61.2 A disabled with a 15 s delay.

---

## `*IDN?` model field

This unit answers `HEWLETT-PACKARD,6060j,0,A.02.01` — the model field really does read
`6060j`, on every read, across firmware and adapter. It looks like a firmware quirk in
the ID string rather than anything wrong with the transfer. The driver matches on the
`HEWLETT-PACKARD,6060` prefix so it identifies both that string and a plain `6060B`.
