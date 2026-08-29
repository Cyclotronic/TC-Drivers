# Agilent / Keysight E364xA — instrument notes

Behaviour of the E364xA supplies worth knowing when using this driver. These are
characteristics of the instrument and the driver's design, not of TestController.
Everything below was confirmed on an **E3641A** (firmware 1.8-5.0-1.0) unless noted.

---

## There is no CV/CC mode command

The supply runs in **constant voltage** until the load draws the current limit, then
crosses into **constant current** by itself. Nothing selects the mode — the load decides.

So there is one voltage setpoint and one current limit, and `STAT:QUES:COND?` reports
which side the hardware is on:

| Value | Meaning |
| --- | --- |
| 0 | Output off, or unregulated |
| 1 | Constant current |
| 2 | Constant voltage |
| 3 | Regulation fault |

Those bits are **not latched**, so each reading is the live state. The driver exposes
this as the `Regulation` logged channel and logs it as a **digital** channel, so the
column reads `CC` or `CV` instead of `1` or `2` and the chart draws it on the shared
digital scale rather than as a numeric curve. Register 0 leaves the column blank rather
than showing `0`; a saved log file keeps the raw integer regardless.

Bench check: with the output into an electronic load, `STAT:QUES:COND?` read **2** at
5 V / 50 mA (load below the limit), **1** once the load demand exceeded the current
limit, and **0** with the output off. `MEAS:VOLT?` / `MEAS:CURR?` agreed with the load's
own readback.

The same Questionable Status register also carries overtemperature (bit 4) and OVP
tripped (bit 9). Overtemperature has its own indicator in the Setup dialog; OVP tripped
is read directly from `VOLT:PROT:TRIP?`.

---

## There is no overcurrent protection

Unlike the E363xA, the E364xA family has **no `CURR:PROT` subsystem** — `CURR:PROT?`,
`CURR:PROT:STAT?` and `CURR:PROT:TRIP?` all return `-113,"Undefined header"`. The driver
omits every OCP control so it cannot queue a header error. The current *limit* still
regulates the output into constant current; it just cannot be made to trip.

Overvoltage protection is present and normal: `VOLT:PROT` with a 1–66 V range on the
E3641A, plus `:STAT`, `:TRIP` and `:CLE`.

---

## The low range does not enforce its own ceiling

Setpoints on the **low** range are validated against the *high* range maximum, not the
low one. On an E3641A, `VOLT 40` on the 35 V range is accepted without error; only values
beyond the 60 V range maximum are rejected (`VOLT 65` → `-222,"Data out of range"`, and
the setpoint is left unchanged). Current is rejected against the active range
(`CURR 0.9` → `-222`).

The driver therefore carries per-range ceilings and shows them beside each setpoint
field, so a value the active range cannot deliver cannot be entered from the dialog by
accident.

| E3641A | Voltage | Current |
| --- | --- | --- |
| 35 V range | 0 – 36.05 V | 0 – 0.824 A |
| 60 V range | 0 – 61.80 V | 0 – 0.515 A |
| OVP | 1 – 66 V | — |

These four numbers were read from the instrument with `VOLT? MAX` / `CURR? MAX` on each
range. The figures for the other five models are from the family User's Guide and have
not been checked against hardware.

---

## Changing range switches the output off

`VOLT:RANG` turns the output off before changing. The driver does this explicitly, so a
low-range high-current setup is never carried into high-range voltage conditions.
`VOLT:RANG?` answers `P35V` / `P60V` (or `P8V` / `P20V` on the 8 V/20 V models), which the
driver maps to the `LOW` / `HIGH` labels on the range control.

---

## The finest step sits just below the sixth decimal

`VOLT:STEP DEF` and `CURR:STEP DEF` set the instrument's finest resolution. On an E3641A
that is **0.00112706 V** and **0.0000144676 A**. Shown to the six decimals the Fine
Adjust fields carry, those are `0.001127` and `0.000014`, and those exact values are the
floor each field accepts — an earlier revision floored them slightly higher and the field
lit red the moment the "Smallest Increment" button wrote the true default back.

`VOLT:STEP?` and `CURR:STEP?` are the only valid step queries — `? MIN`, `? MAX` and
`? DEF` are rejected (`-224,"Illegal parameter value"`). `VOLT? MAX` / `CURR? MAX` do
work and follow the selected range.

---

## Remote and local

`SYST:REM` and `SYST:LOC` are **RS-232 only**. The driver keeps them off the GPIB path
automatically — over GPIB the supply is already in remote once addressed. Connecting does
not reset the supply; disconnecting, and TestController's Output Off, disable the output
but leave protection state and the programmed setpoints alone.

`OUTP:REL` drives the optional TTL relay-control signal on the RS-232 connector and is
exposed on the Basic Setup page as **External Relay**. On a unit without the relay option
it simply reads back `0`.

---

## A rejected query reports its error one command late

A query the supply rejects leaves a pending unread response, and its
`-420,"Query UNTERMINATED"` then surfaces on the **next** error read rather than its own.
When reading `SYST:ERR?` by hand, a failure reported against a healthy command is usually
a stale queue entry from the command before it. The Utility page's Read Error button and
the driver's own error handling account for this.

---

## Display text: the embedded-quote trap

`DISP:TEXT "..."` takes up to 12 characters. A plain string and a string with spaces are
accepted. A string containing a double quote is **not**: it closes the quoted argument
early, the supply rejects the result with `-103,"Invalid separator"`, discards it, and
leaves the previous text in place. That fails safe, but silently — the driver builds the
quoting by concatenation, so an embedded `"` is the one input that breaks the command.

---

## Clearing the display message does not clear the text buffer

`DISP:TEXT:CLE` returns the panel to its normal readout, but the instrument keeps the
string it was showing, so `DISP:TEXT?` goes on answering with the text that was just
cleared — and anything that re-reads the field, including the driver's own refresh after
the button is pressed, puts the old message straight back on screen.

Writing an empty string **before** the clear empties the buffer for real:

    DISP:TEXT ""
    DISP:TEXT:CLE

`DISP:TEXT?` then returns an actually empty `""`. The driver's **Clear Display Message**
button sends both, in that order.

---

## The five settings pages and the selector

The driver's five pages (Basic Setup, Fine Adjust, Protection, Trigger, Utility) sit
behind a `Settings View` selector. In TestController, a selector must name **every** page
the file defines — a page the selector does not name paints *over* the selector-driven
content instead of beside it. The controls that stay visible above the selector (the
output, the range, the two setpoints and the temperature indicator) belong to no page at
all, which is a different thing from belonging to an unnamed one.

---

## Logged channels and the two logging modes

Logging scope is selected from the **mode menu**:

- **Log All** — Voltage, Current, VoltageSet, CurrentSet, Regulation (five channels)
- **Log V and I only** — Voltage and Current (two channels)

| Channel | Source | Meaning |
| --- | --- | --- |
| `Voltage`, `Current` | `MEAS:VOLT?`, `MEAS:CURR?` | what the terminals are doing |
| `VoltageSet`, `CurrentSet` | `VOLT?`, `CURR?` | what the supply was asked for |
| `Regulation` | `STAT:QUES:COND?` | which side it is regulating on |

A `MEAS:` query costs about twice a setpoint readback because it triggers a fresh
conversion, so **Log V and I only** is the way to log faster when several instruments
share one interval. Logging scope is a mode rather than a checkbox on purpose:
TestController locks the mode while a log is running, so the set of columns cannot change
partway through a log.

---

## Revision history

**1.2** — first release. Family driver for the single-output E3640A–E3645A, patterned on
the E363xA selector-layout driver. Hardware-verified against an E3641A: both range
ceilings and both step-DEF values read from the instrument, CV/CC confirmed under load,
every command path exercised. The Fine Adjust step floors were set to the instrument's
own `STEP DEF` values (0.001127 V / 0.000014 A) so the "Smallest Increment" buttons no
longer drive the field out of range.
