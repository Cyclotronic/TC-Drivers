# TC-Drivers

Device drivers for [TestController](https://lygte-info.dk/project/TestControllerIntro%20UK.html),
HKJ's program for logging and controlling bench instruments.

Most drivers here were written against the instrument's programming manual and then
**verified against the physical instrument** — every command exercised, and every
per-range limit read back from the hardware rather than copied from a datasheet. Three
were published from the definition already shipping with TestController, with no fresh
capture taken, and one of those carries a rename that is not in a release yet. The table
says which, and every driver's own header states exactly what stands behind it.

Discussion and support for TestController itself is on the EEVblog thread
[Program that can log/control many multimeters and other devices](https://www.eevblog.com/forum/testgear/program-that-can-log-from-many-multimeters/).

---

## Drivers

| Driver | Instruments | Interface | Rev | Verified |
| --- | --- | --- | --- | --- |
| [Chroma 63000 Series](drivers/Chroma_63000_Series/) | Chroma 63003-150-40, 63004-150-60 DC electronic load | GPIB / LXI / serial | 1.4 | On hardware |
| [HP / Agilent 6060B](drivers/HP_Agilent_6060B/) | HP / Agilent 6060B 300 W DC electronic load | GPIB / LXI / serial | 1.1 | On hardware |
| [HP / Agilent E3631A](drivers/HP_Agilent_E3631A/) | HP E3631A triple-output DC power supply, +6 V / +25 V / -25 V | GPIB / RS-232 | 1.2 | On hardware |
| [HP / Agilent E363xA](drivers/HP_Agilent_E363xA/) | HP E3632A, E3633A, E3634A DC power supply | GPIB / RS-232 | 1.8 | On hardware |
| [Agilent / Keysight E364xA Series](drivers/HP_Agilent_E364xA_Series/) | Agilent / Keysight E3640A–E3649A single- and dual-output DC power supply | GPIB / RS-232 | 1.4 | On hardware |
| [Agilent 33250A](drivers/Agilent_33250A/) | Agilent / Keysight 33250A 80 MHz function / arbitrary waveform generator | GPIB / RS-232 | 1.0 | As shipped |
| [Keithley 200X](drivers/Keithley_200X/) | Keithley 2001, 2001M, 2002 bench multimeter | GPIB | 1.0 | As shipped |
| [Guildline 6560](drivers/Guildline_6560/) | Guildline Instruments 6560 precision resistance calibrator, 0 Ω–100 MΩ | GPIB | 1.2 | On hardware |
| [Leo Bodnar LBE-1420](drivers/LeoBodnar_LBE-1420/) | Leo Bodnar LBE-1420 GPS/GNSS receiver, read-only NMEA | Serial | 1.2 | Shipped, renamed |

**On hardware** — exercised against the instrument, limits read back from it.
**As shipped** — this is the definition TestController itself ships, republished
unchanged; no instrument was on hand to re-measure it for this release.
**Shipped, renamed** — the definition TestController ships, with `#name` changed and
nothing else; the rename is requested upstream and is not in a release yet.

The Keithley 200X is co-authored and carries its own copyright line; see
[`LICENSE`](LICENSE).

Each driver has its own folder containing the driver file, notes on instrument
behaviour worth knowing before you use it, and — where the instrument was on hand —
screenshots of every mode page.

---

## Notebooks

Notes on how TestController behaves, written while building these drivers — what a
declaration actually does, and why a device does or does not turn up where you expect.
Published in Markdown and PDF under [`notebooks/`](notebooks/).

| Notebook | Subject |
| --- | --- |
| [`#interfaceType` and `#interface`](notebooks/interface-types-and-functions.md) | What declaring a device type does and does not do, and the type-plus-function requirement each feature applies before a device appears in its list |

These are working notes, not documentation, and each one states the TestController
version it describes. See [`notebooks/README.md`](notebooks/README.md).

---

## Installing a driver

Copy the `.txt` file into your TestController `Devices` folder and restart:

| Platform | Location |
| --- | --- |
| Windows | `Documents\TestController\Devices\` |
| Linux / macOS | `~/TestController/Devices/` |

TestController identifies the instrument from its `*IDN?` response, so once the file is
in place the device appears when you scan the interface it is connected to.

If a driver does not appear, check that no other driver in the folder claims the same
`#idString` — only one can win the match.

---

## Contributing and issues

Please raise problems as GitHub issues. Useful things to include:

- the instrument model and firmware revision (`*IDN?`)
- how it is connected (GPIB gateway, USB-serial, LXI)
- a TestController debug log covering the problem

Bug reports about TestController itself belong on the EEVblog thread above, not here.

---

## License

MIT — see [LICENSE](LICENSE). Attribution to **Cyclotron** is retained in the header of
each driver file; please keep it there if you redistribute or adapt one.

TestController is HKJ's work and is not covered by this license.
