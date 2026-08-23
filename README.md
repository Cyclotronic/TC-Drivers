# TC-Drivers

Device drivers for [TestController](https://lygte-info.dk/project/TestControllerIntro%20UK.html),
HKJ's program for logging and controlling bench instruments.

Each driver here has been written against the instrument's programming manual and then
**verified against the physical instrument** — every command exercised, and every
per-range limit read back from the hardware rather than copied from a datasheet.

Discussion and support for TestController itself is on the EEVblog thread
[Program that can log/control many multimeters and other devices](https://www.eevblog.com/forum/testgear/program-that-can-log-from-many-multimeters/).

---

## Drivers

| Driver | Instruments | Interface | Rev |
| --- | --- | --- | --- |
| [Chroma 63000 Series](drivers/Chroma_63000_Series/) | Chroma 63003-150-40, 63004-150-60 DC electronic load | GPIB / LXI / serial | 1.4 |
| [HP / Agilent E363xA](drivers/HP_Agilent_E363xA/) | HP E3632A, E3633A, E3634A DC power supply | GPIB / RS-232 | 1.5 |

Each driver has its own folder containing the driver file, screenshots of every mode
page, and notes on instrument behaviour worth knowing before you use it.

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
