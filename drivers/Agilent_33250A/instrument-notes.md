# Agilent / Keysight 33250A — instrument notes

Behaviour of the 33250A worth knowing when using this driver, and the reasoning behind the
parts of the driver that are not obvious from reading it. These are characteristics of the
instrument and of the driver's design.

A note on what is measured and what is not. This file was written from the driver's own
commentary rather than from a fresh session at the instrument: the pulse command headers
below were confirmed on firmware `2.04-1.01-2.00-03-2`, and the underscore substitution was
read off the wire, but the ranges and the mode interlocks come from the programming manual
and from the driver having been in service over GPIB. Where something is untested it says
so.

---

## Two device names from one definition

The 33250A was sold as an Agilent instrument and later as a Keysight one, and the two
answer `*IDN?` with different manufacturer prefixes. Rather than ship two files that would
then drift apart, the driver declares one `#meta` base and two `#metadef` blocks over it:

| Device name | `#idString` prefix | Handle |
| --- | --- | --- |
| `Agilent 33250A` | `Agilent Technologies,33250A,` | `A33250` |
| `Keysight 33250A` | `Keysight Technologies,33250A,` | `K33250` |

The `#meta` base does not appear in the device list itself; the two `#metadef` blocks are
what create the selectable devices from it. The constraint to remember if you adapt this
pattern is that **a `#metadef` can only replace tags that already exist in the `#meta`
block** — it cannot introduce a new one. Everything a variant needs to override has to be
present in the base, even if the base's value is never used.

**There is deliberately no HEWLETT-PACKARD variant.** The 33250A was introduced after the
1999 HP/Agilent split, so no unit ships an `*IDN?` beginning with `HEWLETT-PACKARD`. A
third `#metadef` for it would be a device entry that can never match anything.

---

## The instrument fails silently, so the error queue is the instrument panel

This is the single most important thing about automating a 33250A. Give it a value it
cannot honour and it clips it, substitutes a legal one, or ignores the write — and reports
nothing. The bus stays clean, TestController shows a successful write, and the output is
doing something other than what you asked for.

`SYST:ERR?` is the only way to find out, and it is exposed as **`Last_error`** on the
System page. It pops **one** entry off a queue that holds up to twenty, so a single press
after a failed setup tells you very little; press it until it reports no error. The
`Clear_Errors` button empties the queue so that the next read shows only fresh entries.

Places in this driver where a value is likely to be quietly altered rather than refused:

- any frequency field, when the selected waveform cannot reach the value (below);
- `Duty_Cycle` above 60 MHz, where the instrument is locked at 50 %;
- `Pulse_Width` at long periods, where the enforced minimum is much larger than 8 ns;
- `Marker_Freq`, which is coerced into the sweep span when the marker is switched on;
- `Offset`, which is bounded by the amplitude currently set.

---

## Frequency limits belong to the waveform, not to the field

A TestController number field has one range, fixed when the file is loaded. The 33250A's
range moves with `FUNC`. The fields are therefore declared at the instrument's widest span,
1 µHz – 80 MHz, and the real ceiling is whichever of these applies:

| Waveform | Ceiling | Floor |
| --- | --- | --- |
| Sine, square | 80 MHz | 1 µHz |
| Pulse | 50 MHz | 500 µHz |
| Arbitrary | 25 MHz | 1 µHz |
| Ramp | 1 MHz | 1 µHz |

This is not only the Main page's `Frequency`. `Sweep / Start`, `Sweep / Stop`,
`Sweep / Marker_Freq` and `Modulation / FSK_Hop_Freq` are all capped the same way, and all
four are silent about it.

**`FM_Deviation` is bounded differently again.** It is bounded by the *carrier*, not by
80 MHz: carrier ± deviation must stay inside the active waveform's range. With a low
carrier, or with an arbitrary waveform selected, almost every value you type is refused
outright — which at least is visible. Set `Main / Frequency` before the deviation.

---

## Amplitude, offset and load are one set of interacting limits

**`Load` is a declaration, not a measurement.** `OUTP:LOAD` tells the generator what it
should assume is connected, and it scales the displayed amplitude and offset *and* changes
their legal ranges. The driver offers 50 Ω, 75 Ω, 100 Ω, 600 Ω, 1 kΩ, 10 kΩ and high-Z;
the read path maps the instrument's `9.9E+37` for high impedance back onto `INF`.

**Amplitude** is 10 mVpp – 10 Vpp into 50 Ω. Only high-Z reaches 20 Vpp, which is why the
field is declared to 20.

**Offset** is not independent of it. The reachable maximum is (5 V into 50 Ω, 10 V into
high-Z) **minus half the amplitude**. At 2 mVpp into high-Z you get ±9.999 V and never a
full ±10 V, and at any usable amplitude the limit is well below the field's ±10 V.

**High and low levels are the same setting from the other end.** `VOLT:HIGH` and
`VOLT:LOW` express the waveform as its two rails rather than as a swing and an offset, and
the instrument keeps the two representations in step — so the driver refreshes each pair
when the other is written. The high/low pair is a high-Z pair: into 50 Ω it is limited to
±5 V.

---

## Amplitude unit is forced to VPP at connect

`#initCmd` sends `*CLS;VOLT:UNIT VPP`.

This is not a preference. `VOLT?` returns the amplitude in whatever unit the instrument
happens to be in, with nothing in the reply to say which, and **every amplitude limit in
this driver assumes Vpp**. Left in Vrms, the same number means a different output and the
field's range is wrong by a waveform-dependent factor.

The unit is still selectable, as `Amplitude_Unit` on the System page, because there are
good reasons to want Vrms or dBm. What does not follow it is the Main page's declared
range — the Vrms and dBm ranges are lower and depend on the waveform, and the field will
happily offer you values the instrument will clip.

On disconnect, `#finalCmd` sends `OUTP OFF;*CLS`, so the instrument is left with its
output off and its error queue clear.

---

## SYST:REM is an RS-232 command on this instrument

The 33250A's remote/local commands apply to the serial port only and **error over GPIB**,
so the driver does not send them at all. This costs nothing on GPIB, where the interface
handles remote state itself.

If you drive the instrument over RS-232 and want front-panel lockout, the driver has to
send `SYST:REM` conditionally rather than unconditionally — which means switching it from
`#driver SCPI` to `#driver SCPIx` and adding a command that tests the port type before
writing. The shape of that is written out in a comment beside `#initCmd` in the driver
file.

---

## GPIB framing works on the defaults

The instrument terminates on EOI and needs no inter-command padding, so no
`#gpibReadEol`, `#gpibWriteDelay` or `#eol` is declared and the defaults are correct.

If a clone GPIB adapter drops replies — the usual symptom is intermittent blank or
truncated values rather than an error — try adding `#gpibWriteDelay 5` before looking for
a fault in the driver.

---

## The underscore problem in arbitrary waveform names

Three of the five built-in arbitrary waveforms have an underscore in their name:
`EXP_RISE`, `EXP_FALL` and `NEG_RAMP`. None of the three can be selected from anything
written into a driver file.

An underscore in a parameter that comes *from the configuration file* is replaced with a
space before the text reaches the instrument, in both the parameter column of a combobox
and the `:write:` tag of a button. On the wire the command goes out as:

    Tx <FUNC:USER EXP RISE>          45 58 50 20 52 49 53 45

so the instrument is being asked for a waveform called `EXP RISE`, which does not exist.
`SINC` and `CARDIAC` work only because they have no underscore to lose.

**The way out is not to put the name in the file at all.** A text control sends what *you*
type at runtime, and typed text is not subject to the substitution — including underscores
you type yourself. So `Arb_Shape` is a text field: enter the name exactly as `DATA:CAT?`
reports it (`EXP_RISE`, `EXP_FALL`, `NEG_RAMP`, `SINC`, `CARDIAC`), unquoted. The same
field reaches any arbitrary waveform you have downloaded into the instrument yourself,
which a fixed list never could.

`Arb_Sinc` and `Arb_Cardiac` remain as buttons because those two survive the substitution.
There is deliberately no button for the other three: it would look like it worked and
would not.

A combobox with a `:writemath:` tag putting the underscore back after the substitution
would be the nicer control, and the commented-out version of it is left in the driver file
in case `:writemath:` turns out to be supported. It is easy to test: the debug log already
prints `Rx after :readmath:` lines, so a working write tag should produce a matching
`Tx after :writemath:` line. No such line means the tag was ignored.

---

## The mode interlocks are the instrument's, and the driver mirrors them

AM, FM, FSK, sweep and burst are mutually exclusive on the 33250A. Enabling any one of
them switches the other four off *at the instrument*, whatever the driver does.

So each of the five enables carries `:updatealloff:` and an `:update:` list naming the
other four along with its own dependent controls. Without that, the panel would go on
showing four modes as enabled after the instrument had already dropped them — the state on
screen would be wrong rather than merely stale.

Which carriers each mode accepts is the instrument's rule too. None of the five run on
noise or DC, and that is what the `:enable:` expressions test, so all five controls grey
out for those two waveforms. The remaining restrictions are narrower than an `:enable:`
can express and live in the tips instead: modulation wants a sine, square, ramp or
arbitrary carrier, burst additionally accepts pulse, and sweep is the one that refuses
pulse outright — its `:enable:` excludes pulse along with noise and DC.

---

## Pulse parameters

The pulse command headers `PULS:PER`, `PULS:WIDT` and `PULS:TRAN` were **confirmed on
firmware 2.04-1.01-2.00-03-2**. They are worth stating because the pulse subsystem is one
place where the 33250A's headers do not read the way the rest of the SCPI tree would
suggest.

`Pulse_Period` is an alternative to `Frequency` and the two track each other; setting one
updates the other's field.

**The 8 ns width floor only applies at short periods.** With a long period the instrument
enforces a much larger minimum width and silently substitutes it — one of the clearest
cases of the silent-clipping behaviour above. `Edge_Time` applies to both edges, with a
5 ns minimum.

`Duty_Cycle` is carrier-frequency dependent: 20–80 % up to 25 MHz, 40–60 % from 25 to
60 MHz, and **locked at 50 % above 60 MHz**, where writes are ignored without comment.

---

## Burst: infinite cycles, and why it is a separate control

`BURS:NCYC INF` reads back as `9.9E+37`, not as a keyword, so the `Cycles` field shows a
number that no one typed. That is the instrument reporting infinity in the only way a
numeric query can.

`Set_Infinite` is a separate control rather than an entry inside `Cycles` because
**controls sharing a name are grouped and synchronised together** — giving the button the
same name would tie it to the number field rather than leaving it as an independent write.
The two are linked by an `:update:` instead, so pressing the button refreshes the field.

`Burst_Period` applies to the internal trigger only and must exceed
cycles / carrier frequency. `Gate_Polarity` applies only in gated mode.

---

## Trigger output conflicts with external trigger input

`OUTP:TRIG` cannot be enabled while the Ext Trig BNC is being used as an input, because it
is one connector. Set `Trigger / Source` away from `External` before switching the trigger
output on.

---

## Display text: quoted on the way back, and untested on the way out

`DISP:TEXT?` answers with the string still wrapped in double quotes, so the read path
strips them with `:readmath: unQuote(value)`. Without it the field would show the quotes
as part of the message.

**The write has never been exercised.** `DISP:TEXT` expects a quoted argument, and whether
TestController adds the quotes itself has not been established. If the text does not
appear, try typing it inside double quotes, and check `Last_error` on the same page.

Underscores typed into this field are safe — the substitution described above affects only
text that comes from the configuration file, not text entered at runtime.

---

## Why there is no mode selector

The driver logs three values — `Frequency`, `Amplitude` and `Offset` — and offers no
choice of logging mode.

That is not an omission. The instrument has nothing to switch between: there is no
`#askMode`/`#cmdMode` pair here, and adding a fourth field for the sake of a selector
would prevent the three columns from ever being displayed.

The three are read once per logging interval by `#askValues FREQ?;VOLT?;VOLT:OFFS?`. The
semicolons matter: they make the queries go out as three separate lines rather than as one
compound message, which sidesteps SCPI's rules about header paths inside a compound
command. The reply indices `0`, `1`, `2` that `#interface readFrequency`, `readAmplitude`
and `readOffset` use are positions in that answer, so **reordering `#askValues` breaks the
interface functions** even though the logged columns would still look right.

---

## Known gaps

Two directives that this driver would be better for are absent.

**No `#notes` or `#helpurl`.** There is no in-application guidance on connecting to or
setting up the instrument; a user has to come here for it.

**No explicit `#eol`.** The framing is left to the default. That is why the missing
declaration has never caused trouble: the instrument has been driven over GPIB, where the
default framing is correct and termination is by EOI in any case. Over RS-232 at 57600
baud the default has not been exercised, and an explicit `#eol` would make the framing
deterministic rather than inherited.

Neither is fixed here. This file ships with TestController, and editing the copy in this
repository would fork it from the one every other user runs while still linting and
loading cleanly. Both are requests to make on the
[thread](https://www.eevblog.com/forum/testgear/program-that-can-log-from-many-multimeters/),
not local changes.
