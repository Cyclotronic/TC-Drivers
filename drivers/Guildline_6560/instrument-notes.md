# Guildline 6560 — instrument notes

Behaviour of the 6560 command set worth knowing when using this driver. These are
characteristics of the instrument, not of TestController. Everything below was
confirmed on a **6560** (firmware rev D) over GPIB.

The 6560 predates SCPI. Its command set is a small, flat vocabulary of plain-English
verbs (`RESISTOR`, `TERSE`, `CAL?`, `KEY`) rather than the `:`-hierarchical style later
instruments use, and it has a few sharp edges a modern instrument would not.

---

## GPIB transport

### The 6560 never asserts EOI

Every reply ends in a bare Line Feed; the EOI line is never asserted on a reply,
regardless of Terse/Verbose mode. A controller or gateway that waits for EOI to decide
a reply is complete will hang to its full timeout on every single read. The driver sets
`#gpibReadEol 10` (terminate on LF) for exactly this reason.

### A read timeout needs real margin, not the fastest safe number

Relay-driven writes on this instrument settle in visibly variable time. A timing sweep
around a `RESISTOR` write, reading back with `RESISTOR?` at fixed intervals, found the
old value still being returned at 423 ms and 624 ms after the write, with the new value
only appearing by 1413 ms — for one specific transition. Other transitions, including
some spanning more decades, settled in under 300 ms. There is no fixed worst case to
target, so the driver's `#readingDelay` is set generously (2.5 s) rather than tuned to
whichever transition happened to be measured.

**A short timeout does not just fail — it can return a *plausible wrong answer*.** If a
read times out, the reply it was waiting for does not vanish: it arrives late and sits
in the pipe until the *next* read consumes it. That next read then returns a real,
well-formatted value that is simply the answer to a different, earlier question. This
looks exactly like a working instrument returning wrong data rather than like a comms
fault, and it is the more dangerous failure mode of the two — a fast, self-detected
timeout costs a slow poll cycle, an unnoticed stale reply corrupts the log.

### The 8-second deadlock fallback

If the GPIB controller demands data and the instrument's output buffer is empty for 8
continuous seconds, the 6560 places its current resistance reading into the buffer to
satisfy the read rather than leaving the bus hung. A stray, unmatched read on this
instrument therefore does not time out cleanly — it silently returns a real resistance
reading that answers no query anyone actually sent.

---

## Command parser

### `*CLS` does not exist

It is not in the instrument's command list, and sending it sets the Command Error (CME)
bit in the Event Status Register rather than doing anything. The Event Status Register
is cleared by *reading* `*ESR?`, not by a command.

### Commands cannot be `;`-joined

Unlike SCPI instruments, this parser does not accept a compound line like `*CLS;TERSE`.
Each command needs its own message.

### `TERSE` / `VERBOSE` change the shape of every reply

In Verbose mode, `RESISTOR?` answers e.g. `1.9000345 Ohms`; in Terse mode, the same
query answers `1.9000345` — no unit suffix. The driver forces Terse mode at connect
(`#initCmd TERSE`) so replies parse as plain numbers.

### `RESISTOR` accepts values the front panel and this driver do not offer

The 19 nominal values in this driver's `Resistor` combobox are the calibrated
standards; the instrument's own `RESISTOR` command take any value in range and selects
the *nearest* available standard. A driver or script writing an arbitrary resistance
therefore does not get a resolution error — it gets a silently substituted nearby
value.

---

## Terminal configuration has no remote readback

There is no query anywhere in the command set — not a dedicated command, and no bit in
either `*STB?` or `*ESR?` — that reports whether the instrument is currently in 2-wire
or 4-wire mode. `KEY T` / `KEY F` (what this driver's `Terminals` control sends) are
write-only. **Device Clear resets the instrument to 4-wire**, so that much can be
assumed immediately after a reset; any front-panel toggle after that is untrackable
remotely; the 2-TERMINAL / 4-TERMINAL LEDs on the front panel are the only ground
truth once the mode may have changed by hand.

---

## Device Clear defaults

A GPIB Device Clear resets the instrument to: Open Circuit selected, guard OFF, 4-wire
mode, and Terse response mode. The driver's `#outputOff` and `#initCmd` are written to
land in a state consistent with this.

---

## `KEY` command side effects

The `KEY` command replays a front-panel keystroke remotely (`KEY 1900E` behaves like
typing `1900` then Enter). Sending one sets the User Request (URQ) bit in the Event
Status Register, the same bit a genuine front-panel keypress sets — a script that
treats a non-zero `*ESR?` as an error should mask out URQ, or a `KEY` command will look
like a fault when nothing is wrong.
