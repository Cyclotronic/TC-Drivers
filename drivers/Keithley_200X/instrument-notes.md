# Keithley 2001 / 2001M / 2002 — instrument notes

Behaviour of these meters worth knowing when using this driver, and the reasoning behind
the parts of the driver that are not obvious from reading it.

**What stands behind these notes.** The driver is co-authored: `KungFuJosh` wrote the
family definition, `Cyclotron` did the 2001/2002 work and validated it against a **2002**
and a **2001M** over GPIB before the file was submitted upstream. Firmware revisions were
not recorded, and the 2001 was never on the bench — it takes the 2001M's definition
because the two meters take the same settings, not because that was tested. HKJ took the
file into TestController V3.41 on 25 July 2026, and the copy published here is
byte-identical to the one that release installs.

Nothing here was re-measured for this publication. Where a statement comes from reading
the file or from Keithley's own documentation rather than from the bench, it says so.

---

## Three meters from one file

The definition at the top of the file is marked `#meta`, so it never appears in the device
list itself. The three `#metadef` blocks above it each build a concrete device from it,
substituting the handful of values that differ:

| | 2001 | 2001M | 2002 |
| --- | --- | --- | --- |
| `NPLCrangeMax` | 10 | 10 | **50** |
| Volts column format | 8 digits | 8 digits | **9 digits** |
| 4-wire 200 kΩ, value written | 210000 | 210000 | **200000** |
| 4-wire 2 MΩ range | removed | removed | present |
| `Internal` transducer | removed | removed | present |

The `Keithley 2001` and `Keithley 2001M` definitions are identical apart from their
`#idString`, `#name` and `#handle` — both handles exist so that either meter's `*IDN?`
finds a match. Everything else in the file is common to all three: the 2-wire resistance
table, all four voltage and current range tables, every filter control, the frequency
threshold pages and the thermocouple and RTD pages.

**Why the 4-wire 200 kΩ range is written differently on the 2002.** `RANG` takes a reading
the range must be able to hold, not a range number, and the meter selects the lowest range
that holds it. Writing 210 kΩ therefore lands on the 200 kΩ range on a meter whose next
4-wire range up does not exist, and on the **2 MΩ** range on a 2002, which has one. The
2002 gets the exact 200000 for that reason. The same logic explains the over-range figures
elsewhere in the file — 1100 V for the 1000 V range, 775 V for 750 V, 2.1 A for 2 A,
1.05 GΩ for 1 GΩ.

---

## The reply to `FETC?` contains three elements, and two of them are noise

`#askValues` is `FETC?` and `#askValuesReadFormat` is `UXX`. The read format is one
character per returned element: `U` means *use this, after stripping any letters that
follow the number*, and `X` means *discard*. Three characters, so the meter returns three
comma-separated elements and only the first is the measurement — the unit suffix comes
back attached to it, and the two elements after it are dropped.

That is the reading, the timestamp and the reading number in the meter's default element
list. If you change `FORM:ELEM` on the instrument, this format string stops matching and
the logged column goes wrong rather than empty, which is the failure mode to watch for.
The driver never sends `FORM:ELEM`, so it inherits whatever `:SYST:PRES` leaves set.

---

## `FETC?` returns the last reading, it does not start a new one

`FETCh?` hands back the most recently completed conversion. Nothing in this driver
triggers a reading per logging cycle, so the meter has to be left free-running for there
to be something to fetch — which is what the connect sequence establishes and what the
`Auto_Zero` control is careful to restore (see below).

Two consequences:

- **A logging interval shorter than one conversion fetches the same reading twice.** It
  logs as two samples with two timestamps and identical values. At the driver's default of
  10 NPLC that is a real risk: ten power-line cycles is 200 ms at 50 Hz and 167 ms at
  60 Hz *before* AutoZero's reference readings are added, and the total has not been
  measured here.
- **The first reading after a mode change may predate the change.** `#modeChangeDelay 10`
  gives the mode change a 10 s timeout to complete, which is generous, but the driver does
  not discard a sample.

`#readingDelay 5` is likewise a **timeout**, not a pacing delay — it is how long
TestController will wait for the reply, not how long it waits between requests.

---

## Connecting resets the meter, and so does disconnecting

The connect sequence is not just a remote-mode switch:

    *CLS; *RST; :SYST:PRES; SAMP:COUN 1; :TRIG:SOURCE IMM; :TRIG:SEQ:COUNT 1;
    :UNIT:TEMP C; :SENS:TEMP:TC:TYPE K; :SENS:TEMP:TC:RJUN:RSEL SIM;
    :SENS:TEMP:TC:RJUN:SIM 23; :SYST:AZER:STAT 1;
    :VOLT:DC:NPLC 10; :CURR:DC:NPLC 10; :RES:NPLC 10; :FRES:NPLC 10; :TEMP:NPLC 10;
    VOLT:DC:AVER:STAT 0

and the disconnect sequence is `*CLS; *RST; :SYST:PRES` again.

So the meter is put into a known state on connect and left in a different one on
disconnect, and a front-panel setup does not survive either. That is deliberate — every
control in the driver reads its value back from the instrument, and a known starting state
is what makes the first read of each page meaningful. But it means **the driver is the
place to configure this meter**, not the front panel, and a careful manual setup will be
gone the moment TestController connects.

The one thing to note about the defaults chosen: **10 NPLC on every function** is slow and
deliberate on a meter of this class, and the DC voltage averaging filter is explicitly
turned *off* so that the filter controls start from a known state rather than from
whatever the meter remembered.

---

## AutoZero cannot be changed while the trigger model is running

`Auto_Zero` does not write `:SYST:AZER:STAT` on its own. It writes:

    :INIT:CONT OFF; :ABOR; :SYST:AZER:STAT <n>; :INIT:CONT ON

The setting will not take while the meter is initiating readings continuously, so the
control stops the trigger model, changes the setting and starts it again — and the final
`:INIT:CONT ON` is what keeps `FETC?` working afterwards. The control carries a one-second
delayed update because the meter needs that long before its reply is trustworthy.

**Do not simplify this to a bare `:SYST:AZER:STAT` write.** The setting silently fails to
apply, and the panel then shows a value the meter is not using.

---

## The frequency trigger level is a percentage of a tracked range

The instrument sets its frequency threshold level in absolute volts or amps
(`:SENS:FREQ:THR:VOLT:LEV`), but the level is naturally expressed — and is expressed on
the meter itself — as a percentage of the selected threshold range. The driver presents
the percentage and does the conversion, which requires it to know the range.

It knows the range through two internal variables, `freqVoltRange` and `freqCurrRange`:

- both are seeded to **1.0** by the connect sequence;
- each is updated by the `#scpiCmd` that **writes** the range — `setFreqVoltRange` and
  `setFreqCurrRange` set the variable at the same time as they send `THR:*:RANG`;
- `Trigger_Level` divides the level read back by the variable and multiplies by 100 to
  display a percentage, and multiplies back the other way to write one;
- `Trigger_Voltage` and `Trigger_Current` are read-only echoes of the absolute level, so
  you can see what a percentage worked out to.

**Reading the range back does not update the variable.** The `Voltage_Range` and
`Current_Range` controls read `THR:*:RANG?` to show the current range, but only the write
path sets the tracking variable. So if the meter is already on, say, the 100 V threshold
range when TestController connects, the variable still says 1.0 and both the percentage
and the calculated absolute level are wrong by a factor of 100 until the range is set from
the page. Setting it once from the driver makes the two agree.

The conversion is written defensively — `varExists("freqVoltRange") ? freqVoltRange : 1.0`
— so it degrades to treating the range as 1 rather than failing, which is why the symptom
is a wrong number rather than an error.

---

## A page name that starts with a digit breaks `:enable:`

The two resistance pages are called `Two_Wire_Resistance` and `Four_Wire_Resistance`
rather than the obvious `2W_Resistance` and `4W_Resistance`, and that is not a style
choice.

With the digit-leading names, the `:enable:` expressions on those pages — which reference
controls as `Page.Control` — behaved erratically: some controls enabled and disabled
correctly and others did not, with no error reported anywhere. Renaming both pages to
start with a letter fixed it. This was observed on the bench and worked around, **not
root-caused**; the leading digit is the suspected cause because an expression like
`2W_Resistance.Filter==1` starts with something that parses as a number, and
TestController's documented rule for names used as variables is that they start with a
letter and contain only letters, digits and underscores.

The practical rule: if an `:enable:` or `:visible:` expression misbehaves and nothing is
reported, check that every identifier in it starts with a letter before looking anywhere
else.

---

## Temperature, and what the 2001 and 2001M do not have

`Transducer_Type` offers thermocouple, 2-wire RTD, 4-wire RTD and `Internal` — and the
`Internal` entry is **removed from the 2001 and 2001M definitions**, which do not have that
sensor. A `Transducer_Type` selection also swaps the sub-page below it via a second
selector, so the thermocouple fields and the RTD fields are never on screen together.

Within the thermocouple page, `TC_Ref_Junction` gates the rest: the simulated reference
temperature is enabled only for `Simulated`, and the coefficient and 0 °C offset only for
`Real`. Within the RTD page, `RTD_R0` is enabled for `USER` and `SPRTD`, and the alpha,
beta and delta constants for `USER` alone. Both RTD types — 2-wire and 4-wire — share one
page, because the instrument's `RTD` subsystem is shared.

**The logged column's unit stays `°C` whatever `Temperature_Unit` is set to.** The
`#value` unit is a fixed string; switching the meter to Fahrenheit or Kelvin changes the
number the meter reports and the label follows nothing. A log taken in Kelvin is labelled
`°C`, so record the unit yourself if you change it. The connect sequence sets Celsius, so
the label is correct until you change it.

---

## The mode list, the column list, and `Period`

Eight `#cmdMode` entries and eight `#value` columns, with each column selected by the mode
that produces it. Only one column is live at a time, which is what a bench multimeter
does, and `Resistance` is deliberately shared by the 2-wire and 4-wire modes so a log that
switches between them keeps one column instead of splitting into two.

`#askMode FUNC?` reports the meter's function and the `Mode_settings` selector uses the
same query to show the matching settings page, so the Setup dialog follows the instrument
rather than TestController's idea of it. `FUNC?` answers with the mode quoted, hence the
`unQuote(value)` on the read; `Active_Mode` maps the same answer to a plain-English label
for display.

**`Period` is declared and unreachable.** `#value Period s D3 Period` names `Period` as its
selecting mode, and no `#cmdMode` defines a mode with that name, so nothing ever activates
that column. It is harmless — a column that never becomes active costs no query and no
space in the log — but period is not something this revision can measure, despite the file
having a section header that mentions it.

---

## Known gaps

Reported rather than fixed. The file is shipped: editing it here would fork it from the
copy every other user runs, silently, because it still lints and still loads. Each of
these is a request to make on the thread instead.

- **No `#eol`.** The line ending is left at the default. GPIB framing does not depend on
  it, so this costs nothing in practice, but it makes the file's behaviour dependent on a
  default rather than a declaration.
- **Eleven `comboboxHot` controls send non-numeric parameters with no `:string:` tag** —
  the six `Moving`/`Repeat` filter controls, `AVG_Type`, `TC_Type`, `TC_Ref_Junction`,
  `RTD_Type` and `AutoZero_Type`. The default read handling expects a number. They work as
  written; the tag is what would make the string handling explicit rather than incidental.
- **`#helpurl` is not documentation.** F1 on a mode or setup page opens a joke link left in
  the file. Nothing in the driver depends on it.
- **No `#notes`.** The *view* button in the device list, which is where a driver puts its
  setup guidance and its limitations, has nothing to show for this one.
- **`°C` is not one of the standard `#value` unit strings**, and as noted above it does not
  track `Temperature_Unit`.
- **Three `:enable:` lines carry trailing whitespace** on the RTD page. Cosmetic.
