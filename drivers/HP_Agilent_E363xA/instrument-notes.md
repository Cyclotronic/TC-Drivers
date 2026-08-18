# HP / Agilent / Keysight E363xA — instrument notes

Behaviour of the E363xA command set that is not obvious from the manual, found while
building the driver and verifying it against an E3633A (firmware 1.6-5.0-1.0) over GPIB.

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
this both as the `Regulation` value channel and as a readout.

Any driver offering CV and CC as selectable *modes* is writing the same `VOLT`/`CURR`
registers under two names.

---

## The supply does not enforce its own range

Setpoints are validated against the **model** maximum, not the selected range. On an
E3633A this is accepted without error:

- in the **8 V** range: `VOLT 15` — above the 8.24 V ceiling
- in the **20 V** range: `CURR 15` — above the 10.3 A ceiling

Only values beyond the model maximum are rejected (`-222,"Data out of range"`).

This is why the driver carries per-range ceilings. Offering the model's full span lets a
value be set that the active range cannot deliver, silently.

| E3633A | Voltage | Current |
| --- | --- | --- |
| P8V range | 0 – 8.24 V | 0 – 20.6 A |
| P20V range | 0 – 20.60 V | 0 – 10.3 A |
| OVP / OCP | 1 – 22 V | 0 – 22 A |

---

## A rejected query reports its error one command late

A query the supply rejects leaves a pending unread response. Its
`-420,"Query UNTERMINATED"` then surfaces on the **next** error read, not its own.

When probing this family, read `SYST:ERR?` after every single query — otherwise the
blame lands on the following command and a healthy command looks broken. A failure on
the first query of a run is usually a stale queue entry rather than a real fault.

---

## Step queries reject MIN, MAX and DEF

`VOLT:STEP DEF` is a valid *setting*, but `VOLT:STEP? DEF` — and `? MIN` and `? MAX` —
are not valid queries. Only the bare `VOLT:STEP?` and `CURR:STEP?` work.

`VOLT? MAX` and `CURR? MAX` *do* work, and follow the selected range, which is how the
ceilings above were measured.

The instrument's own finest steps are 0.0003644 V and 0.0003802 A.

---

## Changing range switches the output off

`VOLT:RANG` turns the output off before changing. The driver does this explicitly rather
than relying on it, so a low-range high-current setup is never carried into high-range
voltage conditions.

Switching to a range with a lower ceiling also **clips** the existing setpoint — going to
P20V with the current set to 20 A leaves it at 10.3 A, and switching back does not
restore it.

---

## Remote and local

GPIB and RS-232 are both built in, but only one is enabled at a time from the front
panel. `SYST:REM` and `SYST:LOC` are **RS-232 only** — sending them over GPIB returns
`+514,"Command allowed only with RS-232"`.

Connecting does not reset the supply. Disconnecting, and TestController's Output Off,
disable the output but leave protection trips and the programmed state alone.

`OUTP:REL` is deliberately not exposed: it drives optional TTL relay signals on the
RS-232 connector, and the manual warns against using RS-232 when those are configured.

---

## The front-panel "Display Limit" key has no remote equivalent

The whole `DISPlay` subsystem is `DISP` (on/off), `DISP:STAT`, `DISP:TEXT` and
`DISP:TEXT:CLE`. There is no command for the limit-display toggle.

It isn't needed: that key exists because the front panel has one display and must swap
between showing measured output and programmed limits. TestController shows both at
once — the measurements as logged channels, the limits as the setpoint fields.
