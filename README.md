# Telemetry Update Checklist

Use this checklist when updating generated telemetry files from the telemetry sheet and copying them into the radios 2026 GroundStation project.

## 1. Pre-check the sheet and Python

- [ ] Open the telemetry sheet and confirm the Atomics and Parameters entries are correct.
- [ ] Confirm every atomic parameter uses the proper C++ type through the sheet's encoding/type columns.
- [ ] Within each atomic, order fields from largest C++ type to smallest: 32-bit, then 16-bit, then 8-bit, then bools. `char[6]` fields are exempt from this ordering rule.
- [ ] If any atomic, parameter, encoding, or C++ type is unclear, stop and contact the maintainer before generating files.
- [ ] Confirm Python is available:

```powershell
python --version
```

- [ ] From the telemetry repo, install or update parser dependencies:

```powershell
cd C:\Programming\telemetry-2026\parser
python -m pip install -r requirements.txt
```

## 2. Generate telemetry files

- [ ] Run the parser from inside the `parser` directory:

```powershell
cd C:\Programming\telemetry-2026\parser
python .\parse_sheet.py
```

- [ ] Confirm the generated files in `C:\Programming\telemetry-2026\telemetry\gen` have the latest timestamp in the first comment line.
- [ ] Before copying anything, inspect the generated files for obvious errors.
- [ ] Search especially for generated warning comments such as `TODO: Missing encoding` or `TODO: missing type`. If these appear, fix the sheet or contact the maintainer before continuing.

## 3. Commit and push telemetry repo changes

- [ ] Review the generated diff.
- [ ] Commit the telemetry repo changes.
- [ ] Push the telemetry repo changes.

```powershell
cd C:\Programming\telemetry-2026
git status
git diff
git add telemetry\gen
git commit -m "Update generated telemetry"
git push
```

## 4. Replace files in radios 2026 GroundStation

Go to the radios 2026 GroundStation project:

```powershell
cd C:\Programming\radios-2026\GroundStation
```

Replace these four generated files with the matching files from `C:\Programming\telemetry-2026\telemetry\gen`:

- [ ] `telemetry\gen\telemetry_packets.h` -> `GroundStation\lib\telemetry\telemetry_packets.h`
- [ ] `telemetry\gen\telemetry_packets.cpp` -> `GroundStation\src\telemetry\telemetry_packets.cpp`
- [ ] `telemetry\gen\telemetry_generator.cpp` -> `GroundStation\src\telemetry\telemetry_generator.cpp`
- [ ] `telemetry\gen\frame_printer.cpp` -> `GroundStation\src\telemetry\frame_printer.cpp`

Before pasting/replacing, verify the generated files do not contain obvious generated error comments or bad-looking C++ types.

Note: `telemetry_generator.h` is currently a fixed support file, not a generated file. Only replace it if the fixed API changes.

## 5. Build radios GroundStation

- [ ] Build the GroundStation project with PlatformIO using the control station environment.
- [ ] The PlatformIO environment in this repo is named `GS_Control_Station`.

```powershell
cd C:\Programming\radios-2026\GroundStation
pio run -e GS_Control_Station
```

- [ ] If the build fails, fix the telemetry sheet or generated files before committing the radios repo.

## 6. Commit and push radios repo changes

- [ ] Review the radios repo diff and confirm only the expected telemetry files changed.
- [ ] Commit the radios repo changes.
- [ ] Push the radios repo changes.

```powershell
cd C:\Programming\radios-2026
git status
git diff
git add GroundStation\lib\telemetry\telemetry_packets.h GroundStation\src\telemetry\telemetry_packets.cpp GroundStation\src\telemetry\telemetry_generator.cpp GroundStation\src\telemetry\frame_printer.cpp
git commit -m "Update GroundStation telemetry"
git push
```

## Done

- [ ] Telemetry repo generated files are committed and pushed.
- [ ] Radios repo GroundStation telemetry files are replaced, built, committed, and pushed.
