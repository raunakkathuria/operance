# Tray and Live Command Regression Checklist

Run this on a Fedora KDE Plasma Wayland session before tagging a release.

It exists because two things cannot be verified anywhere else. The tray's Qt
surface is not covered by automated tests: `tests/unit/test_tray.py` exercises
`TrayController`, the portable state projection, while `run_tray_app` and its Qt
call sites are only exercised by a human. And live command execution needs a real
KWin session, PipeWire audio, and systemd user services, none of which a
container provides.

Work top to bottom. Sections 1 and 2 are regression checks on behavior that
already shipped; treat a failure there as a release blocker. Section 3 is
promotion evidence for new commands and can be deferred without blocking.

## Before you start

```bash
operance --version              # confirm the build you intend to test
operance --installed-smoke      # expect status ok on a packaged install
operance --doctor
```

Record the build identity from `--version` in the release evidence directory.

## 1. Tray surface

The tray is the primary end-user surface, so a failure here blocks the release
regardless of how the command surface behaves.

- [ ] Tray icon appears in the Plasma system tray after login or after
      `systemctl --user start operance-tray.service`.
- [ ] Left-clicking the tray icon starts click-to-talk and shows the `Listening`
      notification.
- [ ] Speaking `what time is it` returns the time, and the notification stays
      visible long enough to read.
- [ ] Tray menu opens and shows: setup and status, supported commands, recent
      interaction details, update check, beta feedback guide.
- [ ] **Setup and status** opens and reports one clear next action.
- [ ] **Supported commands** lists only commands available on this host.
- [ ] Confirmation flow: say `delete file on desktop called <name>` for a
      throwaway file, confirm from the tray dialog, and check the file is gone.
- [ ] Cancel flow: repeat, then cancel, and check the file still exists.
- [ ] Undo appears after an undoable command and reverses it.

### Voice-loop service control

These paths changed when host-service commands moved behind the platform
provider, and no automated test executes them.

- [ ] Enabling always-on listening from the tray starts
      `operance-voice-loop.service`.
- [ ] Disabling it stops the service.
- [ ] `systemctl --user status operance-voice-loop.service` agrees with what the
      tray reported.
- [ ] With always-on enabled, a sound trigger followed by no command reports a
      sound trigger rather than claiming a wake phrase was heard.

## 2. Already-verified command regression

Every tool below is already in the release-verified subset, and each one had its
execution path rewritten when dispatch became registry-driven. Routing to the
real adapters is covered by tests; actual execution is not.

- [ ] `open firefox` launches the browser (`apps.launch`).
- [ ] `open google.com` opens the URL (`apps.launch`).
- [ ] `search google for linux automation` opens a search (`apps.launch`).
- [ ] `focus firefox` focuses the app (`apps.focus`).
- [ ] `quit <app>` asks for confirmation before quitting (`apps.quit`).
- [ ] `what apps are open` lists real windows (`windows.list`).
- [ ] `is firefox open` answers from real windows (`windows.find`).
- [ ] `switch to <visible window title>` switches focus (`windows.switch`).
- [ ] `what time is it` answers (`time.now`).
- [ ] `battery` reports real battery state (`power.battery_status`).
- [ ] `volume` reports the real level (`audio.get_volume`).
- [ ] `volume 40 percent` changes it (`audio.set_volume`).
- [ ] `mute` and `unmute` work (`audio.set_muted`, `audio.mute_status`).
- [ ] `is wifi on` reports real Wi-Fi state (`network.wifi_status`).
- [ ] `show a notification saying release check` displays one
      (`notifications.show`).
- [ ] `show recent files` lists real files (`files.list_recent`).
- [ ] `list files in downloads` lists real files (`files.list_folder`).
- [ ] `find file named <name>` finds it (`files.find`).
- [ ] `show details for <name>` reports size and modified time
      (`files.get_info`).
- [ ] `show recent downloads` lists real files (`files.list_recent_folder`).
- [ ] `open downloads` opens the folder (`files.open`).
- [ ] `copy file on desktop called <name> to documents` copies without
      overwriting an existing destination (`files.copy`).
- [ ] `create folder on desktop called <name>` creates it
      (`files.create_folder`).
- [ ] `rename folder on desktop from <a> to <b>` renames after confirmation
      (`files.rename`).
- [ ] `move folder on desktop called <a> to <b>` moves after confirmation
      (`files.move`).
- [ ] `delete file on desktop called <name>` deletes after confirmation
      (`files.delete_file`, `files.delete_folder`).

Also run the scripted path, which asserts filesystem outcomes automatically:

```bash
./scripts/run_live_command_smoke.sh
```

## 3. Promotion evidence for new commands

Only tick these if the command behaves correctly. Anything unticked stays out of
`release_verified_tools`.

### Window management

Open a window with a known title first.

- [ ] `minimize <title>` minimizes it.
- [ ] `restore <title>` restores it.
- [ ] `maximize <title>` maximizes it.
- [ ] `close the <title> window` asks for confirmation, then closes it.

### Media control

Start any MPRIS-compatible player, such as VLC or a browser playing audio.

- [ ] `pause` pauses playback.
- [ ] `play` or `resume music` resumes it.
- [ ] `next track` skips forward.
- [ ] `previous track` goes back.
- [ ] With no player running, `pause` reports that no media player is running
      rather than appearing to succeed.

## After the run

```bash
./scripts/run_release_readiness_gate.sh
operance --support-bundle            # attach if anything failed
```

Promote only the tools whose section 3 boxes are ticked by adding them to
`CURRENT_RELEASE_VERIFIED_TOOLS` in `src/operance/platforms/linux.py`, then rerun
the gate. Record which checks passed in the release evidence directory so the
next release can tell what was actually exercised.
