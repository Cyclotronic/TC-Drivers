# TC Device Driver Notebooks

Notes on how TestController actually behaves, written while building the drivers in
this repository.

These exist because the information was scattered. Most of what is here can be found
in [HKJ's documentation](https://lygte-info.dk/project/TestControllerIntro%20UK.html)
and across the [EEVblog thread](https://www.eevblog.com/forum/testgear/program-that-can-log-from-many-multimeters/),
and the documentation is the place to start. What a notebook adds is arrangement: one
question followed all the way down, with the reasoning kept in, so that picking it back
up in six months costs minutes instead of an afternoon. They were written for that
purpose and are published in case they save someone else the same afternoon.

Each notebook comes in two forms. The Markdown is the source and reads fine in the
browser; the PDF is the same document laid out for reading end to end or printing. Both
are committed together, and the two cannot drift: `pdf-sources.sha256` records the hash
of the Markdown each PDF was rendered from, and a change that updates one without the
other fails its check.

To re-render after editing a notebook:

    python3 notebooks/tools/render_pdf.py notebooks/<name>.md
    python3 notebooks/tools/record_sources.py

## Notebooks

| Notebook | Subject | Version described |
| --- | --- | --- |
| [`#interfaceType` and `#interface`](interface-types-and-functions.md) &nbsp;·&nbsp; [PDF](interface-types-and-functions.pdf) | What declaring a device type does and does not do, what the interface map is for, and the type-plus-function requirement each feature applies before a device appears in its list | 3.49 |
| [Silent failures in `#cmdSetup` and `Ascii`](silent-failures-in-cmdsetup-and-ascii.md) &nbsp;·&nbsp; [PDF](silent-failures-in-cmdsetup-and-ascii.pdf) | Five ways a definition parses cleanly and then does nothing without logging anything: a malformed parameter line taking the whole Setup dialog down, a `#scpiCmd` body under five characters, an undefined name in `#initCmd`, `infoAsk` ignoring `:update:`, and `:readmath:` running on a timed-out read | 3.51 |

## What these are not

**Not documentation.** HKJ is the author of TestController and the only authority on
what it is supposed to do. Where a notebook and he disagree, he is right and the
notebook has a bug. Anything attributed to him is quoted from a public source and
listed under Sources at the end of the notebook.

**Version-specific.** Each notebook states the release it describes at the top. These
are the kind of details that change between versions, and a later release
contradicting a notebook makes the notebook out of date, not the release wrong.

**Not uniformly reviewed.** Where a notebook has been read by the author, it says so,
and it says which parts he did not comment on.

Corrections are welcome — the EEVblog thread above is the best place, or open an issue
here.
