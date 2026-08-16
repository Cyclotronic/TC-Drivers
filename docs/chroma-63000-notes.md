# Chroma 63000 series — instrument notes

Behaviour of the 63000 command set that is not obvious from the programming manual,
found while building the driver and verifying it against a 63004-150-60 (firmware 2.01)
over GPIB.

Most of these are things that make the load look broken when it is working exactly as
designed. They are collected here because each one cost real time to work out.

---

## Things that make the load appear unresponsive

### Battery discharge: a timeout of 0 stops the discharge immediately

`BATT:TOUT 0` is a **zero-second timeout**, not "no limit". Set it to 0 and the discharge
starts, runs for about 100 µs and stops — `LOAD?` reads `OFF` and it looks as though the
load is refusing to switch on. There is no error.

Set a real duration. Confirmed by A/B: with `BATT:TOUT 60` the same setup runs correctly
and `FETC:TIME?` counts up; with `0` it stops instantly, repeatably.

### Von above the supply voltage looks identical to a dead load

`CONF:VOLT:ON` is the input voltage the load waits for before it starts drawing. If it is
set above your source voltage, switching Load on does nothing and reports nothing. Check
it before suspecting anything else.

### Short-circuit simulation blocks the sweep test modes

`MODE OCPH`, `MODE OPPH` and `MODE PROG` are rejected with `4,"Execution Error"` while
`LOAD:SHOR` is on, and the mode silently stays where it was. With `LOAD:SHOR OFF` all
three are accepted. The other 24 documented `MODE` values work either way.

The sweep parameters are *not* the cause — the modes are refused even with a valid
start/end/step/dwell configured. If an OCP or OPP mode button appears to do nothing,
check Short first.

---

## Ranges

### The load range is part of the MODE keyword

There is no `CONFigure:CURRent:RANGe` or `CONFigure:RESistance:RANGe`. The range is
encoded in the mode itself — `CCL`/`CCM`/`CCH`, `CRL`/`CRM`/`CRH` and so on.

`CONF:VOLT:RANGe`, `CURR:STAT:VRNG`, `RES:STAT:IRNG` and `POW:STAT:VRNG` are separate and
select **measurement** ranges only.

### Setpoint limits change with the range

Each range has its own valid span, and a value outside it is accepted by the interface
and then ignored by the load. On a 63004:

| Mode | Low | Middle | High |
| --- | --- | --- | --- |
| Current | 0–2 A | 0–6 A | 0–60 A |
| Voltage | 0–16 V | 0–80 V | 0–150 V |
| Resistance | 0.05–250 Ω | 18–1250 Ω | 64–2500 Ω |
| Power | 0–7 W | 0–35 W | 0–350 W |
| Slew | 0.0001–0.1 A/µs | 0.001–0.3 A/µs | 0.01–3 A/µs |

### Constant-resistance slew follows the *current* range

The slew rate in CR mode is a current slew, so its span tracks `RES:STAT:IRNG` — the
current measurement range — and **not** the resistance range. It is easy to measure this
wrongly: if `RES:STAT:IRNG` never moves during testing, the limits look fixed.

### Limits are briefly stale after a mode change

`<setting>? MAX` and `? MIN` keep reporting the *previous* range's limits for a short
while after a mode change, and after a change of `BATT:MODE` the mode must be re-asserted
before the reported limits catch up. Read twice and settle before trusting the answer.

---

## Queries and replies

### Rejected commands produce silence, not an error reply

A keyword this model does not implement is answered with nothing at all. Over a gateway
that reads after every write, the resulting timeout shifts later replies onto the wrong
command and the whole session looks flaky rather than wrong. Query `SYST:ERR?` to tell a
rejected command from a slow one.

### Range and state queries return words, not numbers

`RES:STAT:IRNG?` answers `Low`/`Middle`/`High`, `LOAD?` answers `ON`/`OFF`,
`VOLT:STAT:RES?` answers `Slow`/`Normal`/`Fast`. `MEAS:INP?` answers `LOAD`/`UUT`.
Settings accept either the word or the numeric index.

### Compound measurement queries must be fully qualified

TestController splits `#askValues` on `;` and sends each part as its own command, so a
continuation like `MEAS:VOLT?;CURR?;POW?` silently returns nothing for the second and
third. Write `MEAS:VOLT?;MEAS:CURR?;MEAS:POW?`.

### Battery stop conditions

`BATT:ENDVoltage` and `BATT:TOUT` only. The load has no discharged-capacity stop
condition.

### OCP/OPP sweep parameters

These live in the ADVance subsystem and use `STARt` / `END` / `STEP` / `DWELl`. `STEP` is
a step **count** (1–1000), not a current or power increment. `CONF:OCP` and `CONF:OPP`
are the separate user-defined protection limits, unrelated to the sweep.

`OCP:RES?` and `OPP:RES?` return `<pass/fail>,<value>,<max power>`, or `-1,-1,-1` when
stopped, `-2,-2,-2` when waiting for Von or a trigger, and `-3,-3,-3` while running.

---

## Protection status

`LOAD:PROT?` latches and stays set until `LOAD:PROT:CLE`. `FETC:STAT?` reports the
condition in real time and clears itself when the condition goes away.

**A forced over-current trip returns 32.** The manual's bit table predicts 8 for the same
event, so that table should not be trusted for decoding — it lists 11 condition names
across 16 bit positions and the alignment is ambiguous. The driver therefore names only
code 32 and displays anything else as a raw number, which cannot mislead you.

The candidate names, in the manual's order, are `OV1 OV2 REV OCP1 OCP2 OCP3 OPP1 OPP3
OTP FAN RMT_INH`. Confirm one by forcing its trip before relying on it.

`LOAD:PROT:CLE` clears the trip correctly but queues `4,"Execution Error"` while doing
so.
