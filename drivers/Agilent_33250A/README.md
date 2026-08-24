# Agilent / Keysight 33250A 80 MHz Function / Arbitrary Waveform Generator

TestController driver for the **33250A**, the 80 MHz function and arbitrary waveform
generator, covering both the Agilent-badged and the Keysight-badged instrument from a
single definition.

Seven pages reach the whole instrument: waveform and level, the waveform-specific
parameters, AM/FM/FSK, sweep, burst, the trigger subsystem those two share, and a system
page for the error queue, output conditioning, display and stored states. Frequency,
amplitude and offset are logged.

| | |
| --- | --- |
| **Driver** | [`Agilent_33250A.txt`](Agilent_33250A.txt) |
| **Revision** | 1.0 |
| **Device names** | `Agilent 33250A`, `Keysight 33250A` |
| **Interface** | GPIB, RS-232 |
| **Instrument notes** | [`instrument-notes.md`](instrument-notes.md) |

## This driver already ships with TestController

HKJ took this file into TestController in **V3.48**, released 12 August 2026, listed in
the release notes as *"Added: Agilent 33250A ARB (Thanks Cyclotron)"*
([release post](https://www.eevblog.com/forum/testgear/program-that-can-log-from-many-multimeters/msg6332536/#msg6332536)).
If you run V3.48 or later, you have it already, as `Agilent 33250a.txt` in the shipped
`Devices` folder — there is nothing to install and no reason to.

The copy here is published for the same reason the other drivers in this repository are:
so the file, its documentation and its revision history sit in one place that does not
depend on a release archive.

**What this copy is, and what it is not.** It is the working copy as it stood on 30 July
2026, the day it was posted to the thread — dated a few hours before the post itself. So
it is almost certainly the file that was posted and taken up, but that is an inference
from the timing rather than something that has been checked, and it has **not** been
diffed against the copy inside a TestController distribution. Treat it as *the copy that
was posted*, not as a verified image of what ships.

Against that working copy, only the header block differs: the development header has been
replaced by the short field block this repository uses. The body — every directive, every
control, every comment — is byte-for-byte unchanged, and no edit has been made to the
driver itself for this publication.

Because it is shipped, **it is not edited here**. A change would fork this file from the
one every other user has, silently, since it still lints and still loads. Anything worth
changing is a request to HKJ on the thread — `#name` above all, which is the key saved
setups are stored against.

---

## Read this before automating the generator

### The instrument clips and refuses settings silently

The 33250A accepts an out-of-range value, substitutes something legal, and says nothing.
Nothing reaches TestController, no control turns red, and the number you typed is simply
not what the output is doing. The **`Last_error`** control on the System page is the only
way to find out: it pops one entry off a queue that holds up to twenty, so press it
repeatedly until it reports no error.

Get into the habit of clearing errors before a run and checking them after one.

### Almost every frequency limit depends on the selected waveform

The fields on the Main, Sweep and Modulation pages all declare 1 µHz – 80 MHz, because a
control's range is fixed at load time and the instrument's is not. What the hardware
actually allows depends on `Waveform`:

| Waveform | Maximum frequency |
| --- | --- |
| Sine, square | 80 MHz |
| Pulse | 50 MHz (and no lower than 500 µHz) |
| Arbitrary | 25 MHz |
| Ramp | 1 MHz |

Entering 80 MHz with an arbitrary waveform selected gets you 25 MHz and no complaint. The
same ceiling applies to `Sweep / Start`, `Sweep / Stop`, `Sweep / Marker_Freq` and
`Modulation / FSK_Hop_Freq`.

`Modulation / FM_Deviation` is bounded by something else again — the carrier, not 80 MHz.
Carrier ± deviation has to stay inside the active waveform's range, so with a low carrier
almost every value you type is refused outright. Set `Main / Frequency` first.

### Three built-in arbitrary waveforms cannot be selected from a button

`EXP_RISE`, `EXP_FALL` and `NEG_RAMP` contain an underscore, and an underscore in a
parameter written from a driver file is turned into a space before it reaches the
instrument. `SINC` and `CARDIAC` have no underscore to lose and are provided as buttons;
the other three are reachable only by typing the name into the **`Arb_Shape`** text field,
which sends what you type unaltered. Type it exactly as `Arb_Catalog` reports it, and do
not quote it. The full account is in
[`instrument-notes.md`](instrument-notes.md#the-underscore-problem-in-arbitrary-waveform-names).

### Amplitude is read and written as Vpp

The driver sets `VOLT:UNIT VPP` at connect, because `VOLT?` otherwise answers in whatever
unit the instrument was left in and every amplitude limit in the file assumes Vpp. The
unit remains selectable on the System page — but the Main page limits do not follow it,
and Vrms and dBm ranges are lower and waveform-dependent.

---

## Main

Output enable, the expected load, waveform selection, and the level controls.

**`Load`** is the load the generator should assume, not one it measures. It scales the
displayed amplitude and offset *and* changes their legal ranges: into 50 Ω the amplitude
range is 10 mVpp – 10 Vpp, and only `High_Z` reaches 20 Vpp.

**`Waveform`** drives most of the rest of the driver. Changing it refreshes the frequency
and amplitude fields and the waveform-specific controls on the Wave page, and enables or
disables modulation, sweep and burst according to what the selected waveform supports.

**`Amplitude`** and **`Offset`** interact. The reachable offset is (5 V into 50 Ω, 10 V
into high-Z) *minus half the amplitude* — at 2 mVpp into high-Z you get ±9.999 V, never a
full ±10 V.

**`High_Level`** and **`Low_Level`** are the same setting expressed as rails instead of a
swing, which is usually what you want for logic-level work. The two pairs stay in step:
setting either updates the other. High/low is a high-Z pair; into 50 Ω it is limited to
±5 V.

---

## Wave

The parameters that only apply to some waveforms. Each control is enabled only for the
waveform it belongs to.

- **`Duty_Cycle`** (square) — 20–80 % up to 25 MHz, 40–60 % from 25 to 60 MHz, and
  **locked at 50 % above 60 MHz**, where writes are silently ignored.
- **`Symmetry`** (ramp) — 0 % is a falling sawtooth, 50 % a triangle, 100 % a rising one.
- **`Pulse_Period`**, **`Pulse_Width`**, **`Edge_Time`** (pulse) — period is an
  alternative to `Frequency` and the two track each other. The 8 ns width floor applies
  only at short periods; with a long period the instrument enforces a much larger minimum
  and substitutes it without a word.
- **`Arb_Shape`** (arbitrary) — a text field, for the reason given above. `Arb_Sinc` and
  `Arb_Cardiac` are shortcut buttons for the two built-ins that a fixed list can select.
- **`Arb_Catalog`** lists every waveform currently available — built-in, volatile and
  stored — and **`Free_Arb_Slots`** reports the non-volatile slots left.

---

## Modulation

AM, FM and FSK, each with its own enable, and each disabled for noise and DC carriers.

The instrument allows only one of AM, FM, FSK, sweep and burst at a time. Enabling any one
switches the other four off at the instrument, and the driver refreshes all of them so the
panel does not show four modes that are no longer running.

- **AM** — depth 0–120 % (above 100 % the envelope clips at peak output), internal shape
  and rate, or an external source on the rear-panel Modulation In BNC (±5 V full scale).
- **FM** — deviation bounded by the carrier as described above, internal shape and rate,
  or external.
- **FSK** — the hop frequency is the alternate frequency; the carrier stays on the Main
  page. The internal keying rate reaches 100 kHz; external keying uses the Ext Trig BNC.

---

## Sweep

Start, stop, sweep time and linear or logarithmic spacing, plus the marker.

A stop below the start gives a descending sweep. **`Marker_Freq`** is coerced into the
start–stop span the moment the marker is switched on, and is capped by the active waveform
like every other frequency here — if it looks wrong, check start and stop first. With the
marker off, the Sync BNC marks the whole sweep instead.

---

## Burst

Triggered or gated burst, for sine, square, ramp, pulse or arbitrary carriers.

**`Cycles`** takes 1 to 1,000,000; **`Set_Infinite`** is a separate control rather than an
entry in that field, because controls sharing a name are grouped and synchronised together.
An infinite burst reads back as `9.9E+37`.

**`Burst_Period`** applies to the internal trigger only, and must exceed
cycles / carrier frequency. **`Gate_Polarity`** applies in gated mode only.

---

## Trigger

Shared by sweep and burst.

`Immediate` free-runs, `External` uses the rear BNC with a selectable slope, and `Bus`
waits for the **`Send_Trigger`** button. `Delay` inserts 0–85 s between the trigger and
the start of the sweep or burst.

**`Trig_Out`** cannot be enabled while the Ext Trig BNC is in use as an input — set
`Source` away from `External` first.

---

## System

**`Last_error`** and **`Clear_Errors`** — the error queue, and the reason to read the
first warning above.

**Output conditioning** — `Amplitude_Unit` (Vpp, Vrms, dBm; the Main page limits assume
Vpp), `Auto_Range` (off freezes the output attenuator, which avoids glitches when stepping
amplitude at the cost of range), `Polarity` (inverts about the offset voltage, not about
zero), and `Sync_Output` (off reduces feedthrough on the main output at low amplitudes).

**Instrument** — display on/off, display text, and the beeper. The text write is the one
control in this driver that has never been exercised: `DISP:TEXT` expects a quoted
argument, so if nothing appears, try typing the text inside double quotes and check
`Last_error`.

**Stored states** — `Recall` and `Store` for the five state registers, and
`Reset_Instrument` for a full `*RST`, which turns the output off and returns every setting
to default.

---

## Logged channels

| Channel | Source |
| --- | --- |
| `Frequency` | `FREQ?` |
| `Amplitude` | `VOLT?` |
| `Offset` | `VOLT:OFFS?` |

Three channels, no mode selector. The instrument has no logging modes to switch between,
and a fourth column here would stop the three being displayed at all — see
[`instrument-notes.md`](instrument-notes.md#why-there-is-no-mode-selector).

The driver also declares `#interfaceType ARB` with the generator functions, so the
33250A can be driven from scripts and from TestController's generator-aware features by
frequency, amplitude, offset, waveform and duty cycle rather than by control name.

---

## Installing

**If you run TestController V3.48 or later, this driver is already installed.**

To use this copy instead, put [`Agilent_33250A.txt`](Agilent_33250A.txt) in your
TestController `Devices` folder and **move the shipped `Agilent 33250a.txt` out of it
first**. Both files claim the same `#idString` values and only one can win the match, so
leaving both in place gets you whichever TestController happens to load — not an error
message.

Restart TestController after either change.

---

## What the driver does not have

Two directives are missing and are worth having: `#notes`/`#helpurl`, which is where a
driver puts its setup guidance, and an explicit `#eol`. Neither has been added here,
because the file is shipped and changing it locally would fork it from what everyone else
runs. They are requests to make on the thread. See
[`instrument-notes.md`](instrument-notes.md#known-gaps) for what the missing `#eol` means
in practice — the short version is that GPIB framing works without it.
