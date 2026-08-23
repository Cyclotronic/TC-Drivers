# HP / Agilent / Keysight E3631A — instrument notes

Behaviour of the E3631A worth knowing when using this driver, and the reasoning behind the
parts of the driver that are not obvious from reading it. These are characteristics of the
instrument and of the driver's design, not of TestController.

Everything below was checked against an E3631A on firmware 2.1-5.0-1.0 over GPIB unless it
says otherwise.

---

## The setpoint ceilings are the instrument's own numbers

The limits shown beside each field are the data-sheet nominal times 1.03, which is the
margin this family allows above its rated output:

| Output | Voltage | Current |
| --- | --- | --- |
| +6 V | 0 – 6.18 V | 0 – 5.15 A |
| +25 V | 0 – 25.75 V | 0 – 1.03 A |
| -25 V | -25.75 – 0 V | 0 – 1.03 A |

They started as arithmetic, and they are not arithmetic any more. `VOLT? MAX` and
`CURR? MAX` were read from the instrument for all three outputs and **every one came back
exact against the computed figure**, so the table above is what the hardware says about
itself rather than what the data sheet says about it.

That matters because published ratings are not reliable — on other supplies in this family
the instrument and the data sheet have disagreed. If you adapt this driver to another
model, read the ceilings out of the instrument rather than scaling these.

---

## There are no step floors on this model

`VOLT:STEP?` and `CURR:STEP?` answer `-113` (undefined header) on the E3631A. The
subsystem is not implemented, so there is no smallest-increment figure to expose and the
driver carries none. Its absence is correct rather than an omission — do not go looking
for the fields that the E363xA driver has for this.

---

## One output enable, for all three outputs

`OUTP` is global. There is no per-output enable on the E3631A, so `Output` switches +6 V,
+25 V and -25 V together, and the driver's `setOn` is the only interface line that carries
no channel token.

The practical consequence is that you cannot bring one rail up before another from this
driver. If a device under test needs a sequence, stage the values on the Trigger page and
apply them with the output already on, or use `Track` and the trigger coupling below.

---

## Tracking and trigger coupling are mutually exclusive

`OUTP:TRAC` must be **off** before `INST:COUP` will couple the ±25 V outputs. With
tracking on, the supply refuses the coupling with error `800`. Both controls are exposed —
`Track` on the main panel, `Trigger Coupling` on the Trigger page — so it is easy to set
them in the wrong order; this one at least does report an error.

---

## The status registers are not the E363xA's

Two families that look alike do not share a register map, and the difference is the sort
that produces a confident wrong answer:

**`STAT:QUES:COND?` bit 4 (value 16) is a fan fault on the E3631A.** On the E363xA the
same bit is overtemperature. The driver's `Fan Fault` indicator reads it as the fan, which
is correct here and would be wrong there.

**Regulation does not come from `STAT:QUES:COND?` at all.** It comes from
`STAT:QUES:INST:ISUM<n>:COND?`, a separate register per output, with `<n>` being 1 for
+6 V, 2 for +25 V and 3 for -25 V:

| Value | Bit 0 | Bit 1 | Meaning |
| --- | --- | --- | --- |
| 0 | — | — | that output is off |
| 1 | CC | — | constant current |
| 2 | — | CV | constant voltage |
| 3 | CC | CV | neither quantity is regulated |

The bit *order* is the same as the E363xA's, which is the one thing that does transfer:
`DIGITAL(CC,CV)` works unchanged on both.

**The condition registers are read directly, and no enable registers are set up.**
`STAT:QUES:INST:ISUM<n>:ENAB` exists to propagate these bits up to bit 13 of the
questionable register, which this driver never reads, so it is left alone. If you ever see
a `COND?` query return 0 for an output that is plainly in CV, that assumption is wrong and
the enables are needed after all — please report it.

---

## Three regulation channels cost no chart curves

`Regulation`, `Regulation2` and `Regulation3` are declared `DIGITAL(CC,CV)` rather than as
numbers, and on a three-output supply that choice pays off more than it does on a
single-output one.

A digital value **splits into one chart channel per named bit**, so the three values become
six channels — `Regulation CC`, `Regulation CV`, and the same pair for outputs 2 and 3 —
and **all six draw on a single shared right-hand axis labelled "Digital"**. Only one
numeric axis is consumed on the chart, by `Voltage` on the left. Three regulation channels
therefore cost **zero** numeric curves, not three. The screenshot in
[`README.md`](README.md) shows all six on the one axis.

Two things follow that are easy to misread as faults:

- **A register reading 0 renders blank on screen, not `0`.** A digital value appends only
  those bits that are both named and set, so an output that is off contributes nothing to
  the column.
- **The log file is unaffected.** The saved file records the raw integer regardless of
  what the screen shows, so a fault state survives into the log even when the column looked
  empty at the time. This was the data-loss worry about `DIGITAL`, and it is settled: a log
  from an E3633A in the same family wrote its regulation channel as a bare `2` while in CV.

If the column shows a literal `0` instead of going blank, the digital formatting is not
live — the file TestController loaded is not this one. That is worth checking first,
because it is exactly how an earlier attempt at this measurement produced the opposite
conclusion.

---

## A channel re-select disarms an armed trigger

An `INST` write landing between `INIT` and `*TRG` disarms the armed trigger, and
`SYST:ERR?` is clean afterwards — nothing surfaces at all. The pending values simply never
transfer.

This driver issues `INST` on every logging cycle and on every read of the Trigger page, so
the window is real rather than theoretical, and how often you fall into it depends on the
logging cadence:

| Logging interval | Armed trigger fired |
| --- | --- |
| 3 s | 9 of 9 |
| 0.3 s | 2 of 2 **lost** |
| logging stopped (control) | fired both times |

The driver closes the window the only way a driver can: `Apply Pending Values` chains
`INIT;*TRG;*WAI` into one message, and nothing can interleave inside a single write. The
cost is that arm-now-fire-later is not available from that page, which is what a bus
trigger is for. To do that, stop logging and drive `INIT` and `*TRG` yourself.

With `Trigger Source` set to `Immediate`, the transfer happens on the arm and the trailing
`*TRG` has nothing left to fire.

---

## Recall does not restore the trigger delay faithfully

`*RCL` brings `TRIG:DEL` back changed, contrary to the manual. Measured twice, the first
confirmed on the wire with `TRIG:DEL?` returning `+2.00000000E+00`:

| Stored | Changed to before the recall | After `*RCL` |
| --- | --- | --- |
| 2.500 s | 1.000 s | 2.000 s |
| 3.750 s | 0.250 s | 3.000 s |

Isolated with `TRIG:SOUR` held constant, so it is the delay specifically and not a general
failure of the trigger subsystem to restore: setpoints, output state, tracking and trigger
source all come back correctly.

Both points are consistent with the fractional part being dropped, but two points do not
pin a rule and nothing below 1 s has been tried. An earlier session recorded this as "comes
back 0.00 whatever was saved"; that reading is superseded, and it is what a sub-second
stored delay would look like if the fraction is in fact being dropped — which is the case
still worth testing.

Re-enter the delay after a recall. Nothing warns you, and a stored delay silently losing
its fraction turns a calibrated step into a different one.

---

## TestController's automated tools will not switch the output on

A driver that declares more than one channel does not get its output switched on by
TestController's automated output control, and nothing reports that it was skipped. This
driver declares three channels, one per output.

Bench-confirmed: a five-step voltage sweep ran to completion with `OUTP?` reading `0` at
every sample, the setpoints visibly moving, and the error queue clean throughout. The run
looks identical to a successful one.

The three-channel declaration is kept anyway — it is what puts all three outputs in the
panel and in the Steps popup, and collapsing to one channel would surrender that. So the
cost is carried in the `Output` tip instead: **switch the output on by hand before an Auto
Adjust or Param Sweeper run.**

---

## The display accepts more than it can show

`DISP:TEXT` displays at most **12 characters** and drops the rest without queueing an
error. Only a string longer than 40 characters is rejected, with `-223`. Confirmed on an
E3633A of the same family: 13 characters truncate to 12 and queue nothing.

The `12` on the `Display_Message` field is a display width, not an input cap, so
TestController will accept and send a longer string quite happily. The same is true of text
written to the display by a step or by the Remote Readout popup.

**A double quote in the text breaks the command.** The message is sent as
`DISP:TEXT "<value>"`, so `AB"CD` goes out with three quotes, the supply answers
`-103,"Invalid separator"`, and the previous text stays on the panel. It fails safely, but
silently: the field snaps back and nothing is reported. Keep `"` out of display strings.

**`Clear Display Message` clears the panel but not the buffer.** `DISP:TEXT:CLE` returns
the front panel to its normal readout, but a subsequent `DISP:TEXT?` still returns the old
string — so the control's own refresh repopulates the field with the text you just cleared.
The panel is clear; the field is stale.

---

## Why the logging cycle interleaves channel selects with queries

A measurement can name its channel directly (`MEAS:VOLT? P6V`), but reading a *setpoint*
(`VOLT?` / `CURR?`) cannot — the channel has to be selected first. So the value-read
sequence alternates `INST P<n>` writes with bare `VOLT?` / `CURR?` queries rather than
grouping the queries together.

That shape is load-bearing for a second, undocumented reason. Within a single value read,
query replies are cached against the literal text of the query. This sequence asks the
identical string `VOLT?` three times, once per channel, so on the query text alone the
second and third reads would be served the +6 V answer. What prevents it is that each write
flushes that cache, so every `INST P<n>` clears it immediately before its own channel's
queries refill it.

**Do not reorder the sequence to group the queries, and do not hoist the `INST` commands
out of it.** Either change makes all three channels silently report the +6 V setpoint —
plausible numbers, no error, and wrong for two outputs out of three.

The value indices survive for a related reason: only a sub-command containing `?` appends
to the reply, so the `INST` writes and the inter-command delays consume no value slot. That
is what lines `readVoltage 0 2 4` and `readCurrent 1 3 5` up with the fifteen `#value`
declarations.

---

## Trigger Delay displays its range as "-0.000 - 3600.000"

A cosmetic artefact, not an error. `Trigger Delay` is a three-decimal field with a declared
minimum of 0, and the stored `-0.0` prints with its sign. Four-decimal fields with a zero
minimum are unaffected, which is why no other field on the driver shows it. It is left
alone rather than papered over by declaring the minimum as 0.001, which would be a lie
about the instrument.

---

## Remote and local

`SYST:REM` and `SYST:LOC` are RS-232 commands in this family and are not accepted over
GPIB, so the driver only sends them when the port is not GPIB, and returns the supply to
local control on disconnect.

There is no programmable overvoltage or overcurrent protection on the E3631A. The current
fields are regulation limits: the supply crosses into constant current and keeps going,
rather than tripping and latching off.
