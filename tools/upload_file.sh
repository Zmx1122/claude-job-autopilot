#!/bin/zsh
# usage: upload_file.sh <absolute-file-path> [app-process-name]
# Call right AFTER clicking a "choose file" control in the Claude desktop browser pane (default app "Claude").
# Drives the macOS Open sheet: Cmd+Shift+G → set the Go-to-folder field to the full path → Return (selects file) → Return (Open).
# Needs the Accessibility permission for the Claude app (System Settings → Privacy & Security → Accessibility → Claude ON).
set -e
F="$1"; APP="${2:-Claude}"
[ -f "$F" ] || { echo "file not found: $F"; exit 1; }
osascript - "$F" "$APP" <<'APPLESCRIPT'
on run argv
	set filePath to item 1 of argv
	set appName to item 2 of argv
	tell application "System Events"
		tell process appName
			set ok to false
			repeat 40 times -- wait up to 10 s for the file sheet
				if (exists sheet 1 of window 1) then
					set ok to true
					exit repeat
				end if
				delay 0.25
			end repeat
			if not ok then error "no file sheet open on " & appName & " window 1 (click the choose-file control first)"
			set frontmost to true
			set s to sheet 1 of window 1
		end tell
		delay 0.5
		keystroke "G" using {command down, shift down}
		tell process appName
			repeat 20 times
				if (exists sheet 1 of s) then exit repeat
				delay 0.2
			end repeat
			if not (exists sheet 1 of s) then error "Go-to-folder field did not appear"
			set tf to text field 1 of sheet 1 of s
			set focused of tf to true
			set value of tf to filePath
		end tell
		delay 0.6
		keystroke return -- closes Go-to, selects the file in the browser
		tell process appName
			repeat 20 times
				if not (exists sheet 1 of s) then exit repeat
				delay 0.2
			end repeat
		end tell
		delay 1.0
		keystroke return -- default button: Öffnen
		tell process appName
			repeat 20 times
				if not (exists sheet 1 of window 1) then return "uploaded: " & filePath
				delay 0.25
			end repeat
		end tell
		-- Newer macOS: Go-to with a file path only opens the folder and leaves the file unselected (Öffnen greyed).
		-- Fallback: focus the column browser, type-select the file name, click Öffnen/Open.
		set AppleScript's text item delimiters to "/"
		set fileName to last text item of filePath
		set AppleScript's text item delimiters to ""
		tell process appName
			if exists sheet 1 of sheet 1 of window 1 then key code 53
			delay 0.5
			set g to splitter group 1 of sheet 1 of window 1
			set focused of (browser 1 of splitter group 1 of g) to true
		end tell
		delay 0.4
		keystroke fileName
		delay 1.0
		tell process appName
			set b to missing value
			repeat with bt in (buttons of g)
				if (name of bt) is in {"Öffnen", "Open", "Hochladen", "Upload", "Auswählen", "Choose"} then set b to bt
			end repeat
			if b is missing value then error "no Open button in the file sheet"
			if not (enabled of b) then error "file not selectable in the sheet: " & fileName
			click b
			repeat 20 times
				if not (exists sheet 1 of window 1) then return "uploaded (type-select): " & filePath
				delay 0.25
			end repeat
		end tell
		error "file sheet still open after confirming"
	end tell
end run
APPLESCRIPT
