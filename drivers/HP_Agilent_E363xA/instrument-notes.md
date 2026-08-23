# HP / Agilent / Keysight E363xA — instrument notes

Behaviour of the E363xA supplies worth knowing when using this driver. These are
characteristics of the instrument and the driver's design, not of TestController.

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
this as the `Regulation` logged channel, and logs it as a **digital** channel rather than
a number, so the column reads `CC` or `CV` instead of `1` or `2` and the chart draws it on
the shared digital scale rather than as a numeric curve. Register 0 leaves the column
blank rather than showing `0`; a saved log file keeps the raw integer regardless.

Beware the manual's labels here. It names bit 0 "Voltage" and bit 1 "Current" — the
quantity that is *no longer* regulated, not the mode. Bit 0 is set when the supply is in
constant **current**. The driver's names are the mode, which is what the column is for.

The same Questionable Status register also carries overtemperature (bit 4), OVP tripped
(bit 9) and OCP tripped (bit 10). Those are not named in the logged column — only a run
of bits from 0 can be labelled — but they each have their own indicator in the Setup
dialog, read directly from `VOLT:PROT:TRIP?` and `CURR:PROT:TRIP?`, and the raw integer in
a saved log still carries every bit.

---

## The supply does not enforce its own range

Setpoints are validated against the **model** maximum, not the selected range. On an
E3633A, `VOLT 15` in the 8 V range and `CURR 15` in the 20 V range are both accepted
without error; only values beyond the model maximum are rejected (`-222,"Data out of
range"`).

The driver therefore carries per-range ceilings and shows them beside each setpoint
field, so a value the active range cannot deliver cannot be entered by accident.

| E3633A | Voltage | Current |
| --- | --- | --- |
| P8V range | 0 – 8.24 V | 0 – 20.6 A |
| P20V range | 0 – 20.60 V | 0 – 10.3 A |
| OVP / OCP | 1 – 22 V | 0 – 22 A |

---

## Changing range switches the output off

`VOLT:RANG` turns the output off before changing. The driver does this explicitly, so a
low-range high-current setup is never carried into high-range voltage conditions.

Switching to a range with a lower ceiling also **clips** the existing setpoint — going to
P20V with the current set to 20 A leaves it at 10.3 A, and switching back does not
restore it.

---

## Step queries reject MIN, MAX and DEF

`VOLT:STEP DEF` is a valid *setting*, but `VOLT:STEP? DEF` — and `? MIN` and `? MAX` —
are not valid queries. Only the bare `VOLT:STEP?` and `CURR:STEP?` work. `VOLT? MAX` and
`CURR? MAX` do work and follow the selected range. The instrument's finest steps are
0.0003644 V and 0.0003802 A.

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

Charting a measurement against its setpoint shows the output sagging away from the demand
under load. `Regulation` catches the moment a load pulls the supply from constant voltage
into constant current, which is invisible from voltage and current alone. It is a digital
channel, so it costs a lane on the shared digital scale rather than a numeric curve.

**Log All** is the default and suits a single supply. Switch to **Log V and I only** when
several instruments share one logging interval and the full five-channel cycle no longer
fits the interval. Logging scope is a mode rather than a checkbox on purpose:
TestController locks the mode while a log is running, so the set of columns cannot change
partway through a log.

A `MEAS:` query costs about twice a setpoint readback, because it triggers a fresh
conversion, so logging fewer channels is the way to log faster.

---

## Remote and local

GPIB and RS-232 are both built in, but only one is enabled at a time from the front
panel. `SYST:REM` and `SYST:LOC` are **RS-232 only** — sending them over GPIB returns
`+514,"Command allowed only with RS-232"`. The driver keeps them off the GPIB path
automatically.

Connecting does not reset the supply. Disconnecting, and TestController's Output Off,
disable the output but leave protection trips and the programmed state alone.

`OUTP:REL` is deliberately not exposed: it drives optional TTL relay signals on the
RS-232 connector, and the manual warns against using RS-232 when those are configured.

---

## Using it over RS-232

The driver works over RS-232 as well as GPIB. Three things must be right, and all three
fail the same way — the port opens, writes appear to succeed, and nothing ever replies:

- **Switch the interface on the front panel** (`I/O Config` key). GPIB is the factory
  default, only one interface is live at a time, and the choice is held in non-volatile
  memory. Selecting RS-232 removes the supply from the GPIB bus until you switch back.
- **Use a null-modem cable.** The supply is a DTE device and so is a PC, so it needs a
  DTE-to-DTE crossover cable, DB-9 female on both ends. A straight-through cable is
  silently inert.
- **Do not enable hardware flow control.** The driver's `#baudrate 9600N82RD` asserts
  DTR and RTS and leaves flow control off, which is the "no handshake" wiring the manual
  prescribes. With hardware flow control the command goes out but the supply never
  replies.

Stop bits are fixed at 2. Baud is 300–9600 (9600 default); parity/data is none/8
(default), even/7 or odd/7. `SerialInit` sends `SYST:REM` automatically, and only when
the port is not GPIB.

If you sweep baud rates hunting for the right setting, expect `+511,"RS-232 framing
error"` in the queue afterwards and the front-panel **ERROR** annunciator lit — the
wrong-baud bytes reaching the UART, not a fault. Read the error queue empty to clear it.

RS-232 runs a little slower than GPIB (roughly +20 ms per exchange at 9600 baud) but
sustains one-second five-channel logging comfortably.

---

## A rejected query reports its error one command late

A query the supply rejects leaves a pending unread response, and its
`-420,"Query UNTERMINATED"` then surfaces on the **next** error read rather than its own.
When reading `SYST:ERR?` by hand, a failure reported against a healthy command is usually
a stale queue entry from the command before it.

---

## Clearing the display message does not clear the text buffer

`DISP:TEXT:CLE` returns the panel to its normal readout, but the instrument keeps the
string it was showing. `DISP:TEXT?` goes on answering with the text that was just
cleared — so anything that re-reads the field, including the driver's own refresh after
the button is pressed, puts the old message straight back on screen even though the
supply's front panel is genuinely blank.

Writing an empty string **before** the clear empties the buffer for real:

    DISP:TEXT ""
    DISP:TEXT:CLE

The empty write is accepted with no error, and `DISP:TEXT?` then returns an actually empty
`""`. The driver's **Clear Display Message** button sends both, in that order.

Confirmed on an **E3633A** only. The E3632A and E3634A have not been tested, and neither
manual documents the behaviour either way; if the field repopulates on those models, the
supply refused the empty-string write and the panel is still clear.

---

## The supply is offered to the Remote Readout popup

`#interfaceType` declares `Readout` alongside `PS`, and `setReadoutString` writes the text
through `DISP:TEXT`. The Remote Readout popup filters its device list on the interface
type, so a supply declaring `PS` alone could never appear there however well the readout
command worked.

This is **observed**, not inferred: a probe of the popup's device list showed exactly the
supply's handle, `HPE3633A`. The same display is reachable from Steps.

The panel holds 12 characters. Longer text is silently truncated to 12 and queues no
error — bench-confirmed, and not the `-150,"String data error"` that would be the obvious
guess. An embedded double quote is a separate trap: it closes the quoted argument early,
the supply rejects the result with `-103,"Invalid separator"`, discards it, and leaves the
previous text in place. That one fails safe, but silently.

---

## The front-panel "Display Limit" key has no remote equivalent

The whole `DISPlay` subsystem is `DISP` (on/off), `DISP:STAT`, `DISP:TEXT` and
`DISP:TEXT:CLE`. There is no command for the limit-display toggle.

It isn't needed: that key exists because the front panel has one display and must swap
between showing measured output and programmed limits. TestController shows both at
once — the measurements as logged channels, the limits as the setpoint fields.
