# Agilent / Keysight E364xA Series — instrument notes

Behaviour of the E364x supplies worth knowing when using this driver. These are
characteristics of the instrument and the driver's design, not of TestController.
Facts below apply to the whole family unless marked SINGLE- or DUAL-only, and were
confirmed on an **E3641A** (SINGLE, firmware 1.8-5.0-1.0) and an **E3648A** (DUAL,
firmware 1.7-5.0-1.0) unless noted otherwise.

---

## There is no CV/CC mode command

Each output runs in **constant voltage** until the load draws the current limit, then
crosses into **constant current** by itself. Nothing selects the mode — the load decides.

So there is one voltage setpoint and one current limit per output, and a status register
reports which side the hardware is on:

| Value | Meaning |
| --- | --- |
| 0 | Output off, or unregulated |
| 1 | Constant current |
| 2 | Constant voltage |
| 3 | Regulation fault |

**SINGLE** reads this from `STAT:QUES:COND?` directly. **DUAL** has one such register
*per output* — `STAT:QUES:INST:ISUM1:COND?` for Output 1, `ISUM2` for Output 2 — and it
must be armed once with `STAT:QUES:INST:ENAB 6;STAT:QUES:INST:ISUM1:ENAB 3;
STAT:QUES:INST:ISUM2:ENAB 3` before either summary register reports anything; the driver
does this once in its init sequence.

Those bits are **not latched**, so each reading is the live state. The driver exposes
this as the `Mode` field (SINGLE) or `O1 Mode`/`O2 Mode` (DUAL) and logs it as a
**digital** channel, so the column reads `CC` or `CV` instead of `1` or `2` and the chart
draws it on the shared digital scale rather than as a numeric curve. Register 0 leaves
the column blank rather than showing `0`; a saved log file keeps the raw integer
regardless.

Bench check (SINGLE): with the output into an electronic load, the register read **2** at
5 V / 50 mA (load below the limit), **1** once the load demand exceeded the current
limit, and **0** with the output off. `MEAS:VOLT?` / `MEAS:CURR?` agreed with the load's
own readback.

The same Questionable Status register also carries overtemperature (bit 4) and OVP
tripped (bit 9). Overtemperature has its own indicator in the Setup dialog; OVP tripped
is read directly from `VOLT:PROT:TRIP?` (SINGLE) or `INST:SEL OUTn;VOLT:PROT:TRIP?`
(DUAL).

---

## There is no overcurrent protection

No model in this family has a `CURR:PROT` subsystem — `CURR:PROT?`, `CURR:PROT:STAT?`
and `CURR:PROT:TRIP?` all return `-113,"Undefined header"`. The driver omits every OCP
control so it cannot queue a header error. The current *limit* still regulates the output
into constant current; it just cannot be made to trip.

Overvoltage protection is present and normal on every model: `VOLT:PROT` with a per-model
1 V–ceiling range, plus `:STAT`, `:TRIP` and `:CLE`. On DUAL models, every OVP command
takes the same `INST:SEL OUTn` prefix as everything else.

---

## The low range does not enforce its own ceiling

Setpoints on the **low** range are validated against the *high* range maximum, not the
low one. On an E3641A, `VOLT 40` on the 35 V range is accepted without error; only values
beyond the 60 V range maximum are rejected (`VOLT 65` → `-222,"Data out of range"`, and
the setpoint is left unchanged). Current is rejected against the active range
(`CURR 0.9` → `-222`). The same behaviour was confirmed on the E3648A's low range.

The driver therefore carries per-range ceilings and shows them beside each setpoint
field, so a value the active range cannot deliver cannot be entered from the dialog by
accident.

| Model | Low range | High range | OVP |
| --- | --- | --- | --- |
| E3641A | 0–36.05 V / 0–0.824 A | 0–61.80 V / 0–0.515 A | 1–66 V |
| E3648A | 0–8.24 V / 0–5.15 A | 0–20.60 V / 0–2.575 A | 1–22 V |

These figures were read from each instrument with `VOLT? MAX` / `CURR? MAX` on each
range. The figures for the other eight models are from the family User's Guide and have
not been checked against hardware.

---

## Changing range switches the output off

`VOLT:RANG` turns the output off before changing. The driver does this explicitly, so a
low-range high-current setup is never carried into high-range voltage conditions.
`VOLT:RANG?` answers `P35V` / `P60V` (or `P8V` / `P20V` on the 8 V/20 V models), which the
driver maps to the `LOW` / `HIGH` labels on the range control. **On DUAL models this is
instrument-wide** — changing either output's range switches *both* outputs off, not just
the one being changed.

---

## DUAL only: everything addresses an output, not the instrument

The four dual-output models (E3646A–E3649A) have a single command interpreter shared by
both outputs. `INSTrument:SELect OUT1` / `OUT2` (or `INSTrument:NSELect 1`/`2`) picks
which output every subsequent `VOLT`, `CURR`, `VOLT:RANG`, `VOLT:PROT*` and `VOLT:STEP*`
command addresses. `OUTPut` itself is the one exception — it is instrument-wide, so there
is a single Output on/off control in the dialog, not one per output; the family's own
front panel works the same way.

`INSTrument:SELect` needs on the order of tens of milliseconds to take effect before the
next query can be answered reliably. The driver's DUAL read chains pace a query after
`INST:SEL` with a margin well above what was measured as the failure threshold on one
serial link — see the RS-232 section below. This has no visible cost on GPIB, where the
transport's own handshake already absorbs it.

---

## DUAL only: voltage/range Track

`OUTPut:TRACk {0|1}` links the two outputs: with Track on, Output 2's voltage setpoint
and range follow Output 1's — set Output 1 to 3 V on the low range and Output 2 reads
back 3 V on the low range too, without being written directly. Bench-confirmed at two
setpoints with the error queue clean throughout. Output 2's voltage and range controls
are disabled by the driver while Track is on, since writing them directly has no effect.

A related but different command, `INSTrument:COUPle {0|1|2}` (`ALL`/`NONE` are rejected
with `-224`), exists on this family but does **not** link the outputs' voltage or
trigger arming — tested both ways, no effect found, and it is not exposed here. Do not
confuse it with `OUTPut:TRACk`, which is the real tracking command. (The E363xA driver
documents the same split on that model: `OUTP:TRAC` for voltage tracking, `INST:COUP`
for something unrelated.)

---

## The finest step sits just below the sixth decimal

`VOLT:STEP DEF` and `CURR:STEP DEF` set the instrument's finest resolution. On an E3641A
that is **0.00112706 V** and **0.0000144676 A**; on an E3648A, per output, roughly
**0.00038 V** and **0.000095 A** on the low range. Shown to the six decimals the Fine
Adjust fields carry, those exact values are the floor each field accepts — an earlier
revision floored them slightly higher and the field lit red the moment the "Smallest
Increment" button wrote the true default back.

`VOLT:STEP?` and `CURR:STEP?` are the only valid step queries — `? MIN`, `? MAX` and
`? DEF` are rejected (`-224,"Illegal parameter value"`). `VOLT? MAX` / `CURR? MAX` do
work and follow the selected range. On DUAL models every step command takes the
`INST:SEL OUTn` prefix.

---

## Remote and local

`SYST:REM` and `SYST:LOC` are **RS-232 only**. The driver keeps them off the GPIB path
automatically — over GPIB the supply is already in remote once addressed. Connecting does
not reset the supply; disconnecting, and TestController's Output Off, disable the output
but leave protection state and the programmed setpoints alone.

`OUTP:REL` drives an optional TTL relay-control signal on the RS-232 connector (pins 1
and 9) and is **deliberately not exposed** by this driver. The family's User's and
Service Guide warns twice that using the RS-232 interface while relay-control signals are
configured can damage the RS-232 circuitry — a driver that offers this family over serial
should not also carry a one-click control that makes that configuration live. Query it by
hand if you need it and understand the risk.

---

## RS-232 timing: two separate thresholds, not one

Both problems below are invisible over GPIB, where the transport's own handshake absorbs
the instrument's processing time; a raw RS-232 link has no such handshake and exposes
both. They were found and fixed together, but they are different failures with different
scope:

1. **DUAL only: `INSTrument:SELect` needs on the order of 30 ms** before the next query
   answers reliably over RS-232. Below that threshold, every field whose read chain
   selects an output first (voltage, current, range on either output) fails to populate,
   while fields that never select an output (mode, temperature, display) populate fine —
   that split is the signature of this specific timing issue. The driver's DUAL read
   chains, and its startup value-refresh sequence, pace comfortably above the measured
   threshold. Because single-output models have no `INSTrument` subsystem at all, this
   fix applies to DUAL only, by construction — there is nothing to pace on SINGLE models.

2. **Family-wide: TestController's built-in "wait for operation complete" token** (which
   writes `*OPC` and immediately queries `*ESR?`) can time out over RS-232 if the gap
   between the two is too short, and this was measured as real on **both** a dual-output
   and a single-output unit, with different thresholds per unit — the margin the driver
   uses clears both with room to spare. This affects a handful of infrequent actions
   (range change, state recall, clearing an OVP trip) and costs a fraction of a second on
   each; it has no effect at all over GPIB.

If a serial-connected supply's setpoint and range fields come up blank while mode and
display populate normally, suspect problem 1 before suspecting the adapter or the cable —
that exact split was misdiagnosed as USB-serial adapter flakiness, then stop bits, then
GPIB bus contention before the actual timing threshold was measured directly and found to
be completely deterministic.

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
This control is single, one per instrument, on every model including the dual-output
ones.

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
behind a `Settings View` selector, identical on SINGLE and DUAL models. In
TestController, a selector must name **every** page the file defines — a page the
selector does not name paints *over* the selector-driven content instead of beside it.
The controls that stay visible above the selector (the output, the range(s), the
setpoint(s) and the temperature indicator — plus, on DUAL models, Track) belong to no
page at all, which is a different thing from belonging to an unnamed one.

---

## DUAL only: triggering is arm-and-fire in one message

On SINGLE models, `Arm` (`INIT`) and `Trigger Now` (`*TRG`) are separate buttons — set
the source to Bus and the two steps can happen independently. On DUAL models an
`INSTrument:SELect` write between `INIT` and `*TRG` disarms the trigger, so the driver
cannot offer separate Arm and Trigger Now buttons per output without risking exactly that
sequence. Instead each output gets one **Apply Pending** button that selects the output
and chains `INIT;*TRG;*WAI` in a single message, arming and firing together.

---

## Logged channels and the two logging modes

Logging scope is selected from the **mode menu**:

- **Log All** — Voltage, Current, VoltageSet, CurrentSet, Regulation, per output on DUAL
  models (five channels on SINGLE, ten on DUAL)
- **Log V and I only** — Voltage and Current, per output on DUAL models

| Channel | Source | Meaning |
| --- | --- | --- |
| `Voltage`, `Current` | `MEAS:VOLT?`, `MEAS:CURR?` | what the terminals are doing |
| `VoltageSet`, `CurrentSet` | `VOLT?`, `CURR?` | what the supply was asked for |
| `Regulation` / `Mode` | status register | which side it is regulating on |

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

**1.3** — dropped the `HEWLETT-PACKARD` `#metadef` blocks; nothing in this family reports
that manufacturer string in `*IDN?`.

**1.4** — replaces the single-output-only driver with one file covering the whole ten-
model line. Adds the four dual-output models (E3646A–E3649A) via `#sections`/
`#metaSection`, so Output 2 and the voltage/range Track toggle appear only where the
hardware has them; `#name`/`#idString`/`#handle` for the six existing models are
unchanged, so this is a drop-in replacement, not a break. Three fixes reach the
single-output models as a side effect of the merge: `OUTP:REL` (External Relay) is
removed for the RS-232 safety reason documented above, the family's `[*OPC]`-equivalent
delay is widened family-wide after being measured as marginal on RS-232 on both a single-
and dual-output unit, and `Readout` is added to the dual branch's declared interface type
so its Remote Readout text is reachable. Both branches hardware-verified as described in
the header.
