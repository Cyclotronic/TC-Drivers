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

## Using it over RS-232

Verified against an E3633A: all 26 of the driver's read queries answer correctly over
serial, with a clean error queue.

Three things are easy to get wrong, and all three fail in exactly the same way — the
port opens, writes appear to succeed, and nothing ever replies:

- **The interface must be switched on the front panel** (`I/O Config` key). GPIB is the
  factory default, only one interface is live at a time, and the choice is held in
  non-volatile memory. Selecting RS-232 removes the supply from the GPIB bus until you
  switch it back.
- **The cable must be null-modem.** The supply is a DTE device and so is a PC, so it
  needs a DTE-to-DTE crossover cable, DB-9 female on both ends. A straight-through
  cable is silently inert.
- **Stop bits are fixed at 2.** Baud is 300–9600 (9600 default); parity/data is none/8
  (default), even/7 or odd/7. The driver's `SerialInit` sends the required `SYST:REM`
  automatically, and only when the port is not GPIB.
- **Do not enable hardware flow control.** The driver uses `#baudrate 9600N82D` — `D`
  asserts DTR and leaves flow control off. On a null-modem cable our DTR drives the
  supply's DSR, which is what the manual prescribes for running without the handshake
  ("tie the DSR line to logic TRUE"). With hardware flow control the command goes out
  correctly but the supply never replies. Measured: no flow control and a DTR/DSR
  handshake both gave 500 clean queries; RTS/CTS timed out every time.

If you sweep baud rates hunting for the right setting, expect `+511,"RS-232 framing
error"` in the queue afterwards and the front-panel **ERROR** annunciator lit. That is
the wrong-baud bytes reaching the UART, not a fault — read the error queue empty to
clear it.

### Speed

Measured at 9600 baud, and it is closer to GPIB than expected:

| | RS-232 | GPIB |
| :--- | ---: | ---: |
| `MEAS:VOLT?` | 144.0 ms | 119.8 ms |
| `VOLT?` (setpoint) | 72.6 ms | 54.5 ms |
| All five logged channels | 495 ms | 399 ms |

About **1.24× slower**, a roughly flat +20 ms per exchange. Over a 400-cycle soak the
serial path sustained **1.96 readings/second** with all five channels, with 0 bad
replies in 2000 queries and a p99 within 2 ms of the median.

**Remote mode makes the supply 1.8× faster.** Servicing the front panel costs real
time, and `SYST:REM` disables it:

| | `MEAS:VOLT?` | Five channels |
| :--- | ---: | ---: |
| Local (front panel live) | 222.1 ms | 909.5 ms |
| Remote (`SYST:REM`) | 146.0 ms | 502.7 ms |

The driver sends `SYST:REM` on connect, so logging gets the fast path. It matters
mainly when interpreting a measurement taken before the driver has initialised — TC's
identification scan runs first, so `*IDN?` is answered in local mode. (It *is* answered:
`SYST:REM` is not required in order to get a reply, despite the manual's warning about
communicating outside remote mode.)

Note that a *measurement* costs about twice what a setpoint readback does on either
transport, because `MEAS:` triggers a fresh conversion. Cost scales with the number of
queries, so logging fewer channels is the way to log faster.

### No inter-command delays are needed

Some drivers for this family put a fixed ~20 ms delay after every command. Measured on
this one, that is unnecessary on both transports:

- 300 write-then-read cycles on the setpoint at 0 ms settling: **zero** mismatched
  readbacks, no queued errors. Same at 5/10/20/50 ms.
- 40 `VOLT:RANG` changes read back at 0 ms settling: **zero** wrong values.
- 120 randomised GPIB address switches with no settling: zero bad replies.

So a readback taken immediately after a write reflects the write.

---

## The front-panel "Display Limit" key has no remote equivalent

The whole `DISPlay` subsystem is `DISP` (on/off), `DISP:STAT`, `DISP:TEXT` and
`DISP:TEXT:CLE`. There is no command for the limit-display toggle.

It isn't needed: that key exists because the front panel has one display and must swap
between showing measured output and programmed limits. TestController shows both at
once — the measurements as logged channels, the limits as the setpoint fields.
