# Training Disclosure for multi-font-preview
This Training Disclosure, which may be more specifically titled above here (and in this document possibly referred to as "this disclosure"), is based on **Training Disclosure version 1.1.4** at https://github.com/Hierosoft/training-disclosure by Jake Gustafson. Jake Gustafson is probably *not* an author of the project unless listed as a project author, nor necessarily the disclosure editor(s) of this copy of the disclosure unless this copy is the original which among other places I, Jake Gustafson, state IANAL. The original disclosure is released under the [CC0](https://creativecommons.org/public-domain/cc0/) license, but regarding any text that differs from the original:

This disclosure also functions as a claim of copyright to the scope described in the paragraph below since potentially in some jurisdictions output not of direct human origin, by certain means of generation at least, may not be copyrightable (again, IANAL):

Various author(s) may make claims of authorship to content in the project not mentioned in this disclosure, which this disclosure by way of omission unless stated elsewhere implies is of direct human origin unless stated elsewhere. Such statements elsewhere are present and complete if applicable to the best of the disclosure editor(s) ability. Additionally, the project author(s) hereby claim copyright and claim direct human origin to any and all content in the subsections of this disclosure itself, where scope is defined to the best of the ability of the disclosure editor(s), including the subsection names themselves, unless where stated, and unless implied such as by context, being copyrighted or trademarked elsewhere, or other means of statement or implication according to law in applicable jurisdiction(s).

Disclosure editor(s): Hierosoft LLC

Project author: Hierosoft LLC

This disclosure is a voluntary of how and where content in or used by this project was produced by LLM(s) or any tools that are "trained" in any way.

The main section of this disclosure lists such tools. For each, the version, install location, and a scope of their training sources in a way that is specific as possible.

Subsections of this disclosure contain prompts used to generate content, in a way that is complete to the best ability of the disclosure editor(s).

tool(s) used:
- Grok
- Gemini

Scope of use: code described in subsections--typically modified by hand to improve logic, variable naming, integration, etc, but in this commit, unmodified.

## multi-font-preview.py
- 2026-04-16 https://grok.com/share/c2hhcmQtMg_a3a65264-c3d0-4d2a-b73f-063dd736cc2a
Make a multi-font reviewer application in wxPython. Make a FontInfo class. The program should look in the current directory (or directory passed by argparse) for OTF, TTF, and ZIP files, case insensitive, recursively. For easier collection during recursion, make a SearchState class such as with self.found = OrderedDict(). For each OTF, TTF, including in the ZIP file, make a FontInfo instance, in a dictionary of lists. key should be parent directory (or parent zip file in case of ones from a zip file). Also set self.parent and self.name in the object. Make a get_regular global function that accepts a list of fontinfo instances and returns FontInfo or None, FontInfo being the shortest name containing either "-R" or "Regular", case insensitive. For each key in the dictionary, use get_regular, and if the result is None, leave it alone, otherwise set the found[key] = [result] (so all non-regular fonts are discarded). Make a set called done_names = set() to prevent duplicates. Iterate through keys and each item in list, use and if necessary extract the font to a temporary location, then make a label on the form where the font is that font, and the text is the name.

Don't show the group nor path. Make it succinctly show only the fonts. Make them a bit smaller, maybe 16pt. Make a minimum windows size, starting at half of screen width by half of screen height, then expand to content if any.

```
Traceback (most recent call last):
  File "/home/owner/Nextcloud/d.python/wx/multi-font-preview/multi-font-preview.py", line 165, in <module>
    frame = FontReviewerFrame(state.found)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/owner/Nextcloud/d.python/wx/multi-font-preview/multi-font-preview.py", line 89, in __init__
    self.init_ui()
  File "/home/owner/Nextcloud/d.python/wx/multi-font-preview/multi-font-preview.py", line 143, in init_ui
    self.SetMinSize((min(current_size[0], initial_size[0]),
                                          ^^^^^^^^^^^^
NameError: name 'initial_size' is not defined
```

Now you must set the font of each label, not just the text. The font should be set to the full font path so we can utilize that glyph. However, when setting the text, remove the file extension for brevity.

The font face is still not being set. You're not even passing the font path. Since the fonts aren't installed yet you must set the full path. Example by Gemini:
```
        font_path = "path/to/your/font.ttf"

        # 2. Add the font privately to the application
        wx.AddPrivateFont(font_path)

        # 3. Create a font object using the font name from the TTF file
        # 'FaceName' must match the font's internal name
        custom_font = wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                              wx.FONTWEIGHT_NORMAL, faceName="Font Name")

        # 4. Create label and apply the font
        self.label = wx.StaticText(panel, label="Hello, Custom Font!", pos=(50, 50))
        self.label.SetFont(custom_font)

```

Add the private font this way so we actually get the face name(s) (If len 0, continue; if len > 1, show warning and use added[0]) as per Gemini https://gemini.google.com/share/64dd0cf0f252:

```
def get_added_face_names(ttf_path):
    # 1. Helper to get all current face names
    def get_all_faces():
        class FontEnumerator(wx.FontEnumerator):
            def __init__(self):
                super().__init__()
                self.faces = set()
            def OnFacename(self, facename):
                self.faces.add(facename)
                return True

        enumerator = FontEnumerator()
        enumerator.EnumerateFacenames()
        return enumerator.faces

    # 2. Get baseline
    before = get_all_faces()

    # 3. Load the font
    if not wx.Font.AddPrivateFont(ttf_path):
        return []

    # 4. Get updated list and compare
    after = get_all_faces()

    # Return only the new items
    new_faces = list(after - before)
    return new_faces
```

I added the following checks to get_added_face_names:
```
    if not os.path.isfile(ttf_path):
        raise FileNotFoundError(f"Missing {repr(ttf_path)}")
    if not wx.Font.AddPrivateFont(ttf_path):
        print(f"Failed to add {repr(ttf_path)}", file=sys.stderr)
        return []
```
They reveal that every time you call get_added_face_names you are sending it a path that doesn't exist. Make sure you are utilizing the temp file feature properly including scope.

Enumerating private fonts fails, so use this simplified method from Gemini instead:

```
from fontTools.ttLib import TTFont

def register_and_get_font(ttf_path):
    # Standard file check
    if not os.path.isfile(ttf_path):
        raise FileNotFoundError(f"Missing {repr(ttf_path)}")

    # Use fonttools to get the exact Full Font Name (ID 4)
    try:
        font = TTFont(ttf_path)
        # ID 4 is the 'Full Font Name' (e.g., "My Font Bold")
        face_name = font['name'].getDebugName(4)
    except Exception as e:
        print(f"Error reading font metadata from {ttf_path}: {e}", file=sys.stderr)
        return None

    # Register with wx
    if not wx.Font.AddPrivateFont(ttf_path):
        print(f"Failed to add {repr(ttf_path)} to wx", file=sys.stderr)
        return None

    return face_name
```

Starting from this updated version with more output:
- paste it
Make sure you don't hide errors like your previous version I fixed above.
Then try to fix the issue where there are no errors but the fonts aren't visibly used by the application. Maybe there is a way to see if the font constructor succeeded, or the custom_font object has the expected face name?

I am on Linux Mint zena, and this is the output, though the font isn't visibly applied to the labels:
```
owner@roamtop:~/Nextcloud/Fonts$ python3 ~/Nextcloud/d.python/wx/multi-font-preview/multi-font-preview.py arkandis.tuxfamily.org
Using face_name 'Solothurn-Regular' for Solothurn-Regular.otf
Applying to 'Solothurn-Regular' → faceName='Solothurn-Regular' | IsOk=True | Actual GetFaceName()='Solothurn-Regular'
Using face_name 'TribunADFStd-Regular' for TribunADFStd-Regular.otf
Applying to 'TribunADFStd-Regular' → faceName='TribunADFStd-Regular' | IsOk=True | Actual GetFaceName()='TribunADFStd-Regular'
Using face_name 'IkariusADFStd-Regular' for IkariusADFStd-Regular.otf
Applying to 'IkariusADFStd-Regular' → faceName='IkariusADFStd-Regular' | IsOk=True | Actual GetFaceName()='IkariusADFStd-Regular'
Using face_name 'MekanusADFStd-Regular' for MekanusADFStd-Regular.otf
Applying to 'MekanusADFStd-Regular' → faceName='MekanusADFStd-Regular' | IsOk=True | Actual GetFaceName()='MekanusADFStd-Regular'
Using face_name 'AccanthisADFStd-Regular' for AccanthisADFStd-Regular.otf
Applying to 'AccanthisADFStd-Regular' → faceName='AccanthisADFStd-Regular' | IsOk=True | Actual GetFaceName()='AccanthisADFStd-Regular'
Using face_name 'BaskervaldADFStd-BoldItalic' for BaskervaldADFStd-BoldItalic.otf
Applying to 'BaskervaldADFStd-BoldItalic' → faceName='BaskervaldADFStd-BoldItalic' | IsOk=True | Actual GetFaceName()='BaskervaldADFStd-BoldItalic'
Using face_name 'BaskervaldADFStd-Bold' for BaskervaldADFStd-Bold.otf
Applying to 'BaskervaldADFStd-Bold' → faceName='BaskervaldADFStd-Bold' | IsOk=True | Actual GetFaceName()='BaskervaldADFStd-Bold'
Using face_name 'BaskervaldADFStd-HeavyItalic' for BaskervaldADFStd-HeavyItalic.otf
Applying to 'BaskervaldADFStd-HeavyItalic' → faceName='BaskervaldADFStd-HeavyItalic' | IsOk=True | Actual GetFaceName()='BaskervaldADFStd-HeavyItalic'
Using face_name 'BaskervaldADFStd-Heavy' for BaskervaldADFStd-Heavy.otf
Applying to 'BaskervaldADFStd-Heavy' → faceName='BaskervaldADFStd-Heavy' | IsOk=True | Actual GetFaceName()='BaskervaldADFStd-Heavy'
Using face_name 'BaskervaldADFStd-Italic' for BaskervaldADFStd-Italic.otf
Applying to 'BaskervaldADFStd-Italic' → faceName='BaskervaldADFStd-Italic' | IsOk=True | Actual GetFaceName()='BaskervaldADFStd-Italic'
Using face_name 'BaskervaldADFStd' for BaskervaldADFStd.otf
Applying to 'BaskervaldADFStd' → faceName='BaskervaldADFStd' | IsOk=True | Actual GetFaceName()='BaskervaldADFStd'
Using face_name 'Berenis ADF Pro Regular' for BerenisADFPro-Regular.otf
Applying to 'BerenisADFPro-Regular' → faceName='Berenis ADF Pro Regular' | IsOk=True | Actual GetFaceName()='Berenis ADF Pro Regular'
Using face_name 'AurelisADFNo2Std-Regular' for AurelisADFNo2Std-Regular.otf
Applying to 'AurelisADFNo2Std-Regular' → faceName='AurelisADFNo2Std-Regular' | IsOk=True | Actual GetFaceName()='AurelisADFNo2Std-Regular'
Using face_name 'LibrisADFStd-Regular' for LibrisADFStd-Regular.otf
Applying to 'LibrisADFStd-Regular' → faceName='LibrisADFStd-Regular' | IsOk=True | Actual GetFaceName()='LibrisADFStd-Regular'
Using face_name 'UniversalisADFStd-Regular' for UniversalisADFStd-Regular.otf
Applying to 'UniversalisADFStd-Regular' → faceName='UniversalisADFStd-Regular' | IsOk=True | Actual GetFaceName()='UniversalisADFStd-Regular'
Using face_name 'IrianisADFStd-Regular' for IrianisADFStd-Regular.otf
Applying to 'IrianisADFStd-Regular' → faceName='IrianisADFStd-Regular' | IsOk=True | Actual GetFaceName()='IrianisADFStd-Regular'
Using face_name 'Romande ADF Std Regular' for RomandeADFStd-Regular.ttf
Applying to 'RomandeADFStd-Regular' → faceName='Romande ADF Std Regular' | IsOk=True | Actual GetFaceName()='Romande ADF Std Regular'
Using face_name 'ElectrumADFExp-Regular' for ElectrumADFExp-Regular.otf
Applying to 'ElectrumADFExp-Regular' → faceName='ElectrumADFExp-Regular' | IsOk=True | Actual GetFaceName()='ElectrumADFExp-Regular'
Using face_name 'GilliusADF-Regular' for GilliusADF-Regular.otf
Applying to 'GilliusADF-Regular' → faceName='GilliusADF-Regular' | IsOk=True | Actual GetFaceName()='GilliusADF-Regular'
Using face_name 'MintSpirit-Regular' for MintSpirit-Regular.otf
Applying to 'MintSpirit-Regular' → faceName='MintSpirit-Regular' | IsOk=True | Actual GetFaceName()='MintSpirit-Regular'
Using face_name 'Mintysis Regular' for MintysisAH-Regular.ttf
Applying to 'MintysisAH-Regular' → faceName='Mintysis Regular' | IsOk=True | Actual GetFaceName()='Mintysis Regular'
```

```
Traceback (most recent call last):
  File "/home/owner/Nextcloud/d.python/wx/multi-font-preview/multi-font-preview.py", line 118, in on_paint
    gc.SetFont(gfont, wx.BLACK)
TypeError: GraphicsContext.SetFont(): arguments did not match any overloaded call:
  overload 1: argument 1 has unexpected type 'GraphicsFont'
  overload 2: too many arguments
Traceback (most recent call last):
  File "/home/owner/Nextcloud/d.python/wx/multi-font-preview/multi-font-preview.py", line 118, in on_paint
    gc.SetFont(gfont, wx.BLACK)
TypeError: GraphicsContext.SetFont(): arguments did not match any overloaded call:
  overload 1: argument 1 has unexpected type 'GraphicsFont'
  overload 2: too many arguments
Traceback (most recent call last):
  File "/home/owner/Nextcloud/d.python/wx/multi-font-preview/multi-font-preview.py", line 118, in on_paint
    gc.SetFont(gfont, wx.BLACK)
TypeError: GraphicsContext.SetFont(): arguments did not match any overloaded call:
  overload 1: argument 1 has unexpected type 'GraphicsFont'
  overload 2: too many argument
```

The font still isn't visibly applied. Is there something special we have to do for private fonts?
```
owner@roamtop:~/Nextcloud/Fonts$ python3 ~/Nextcloud/d.python/wx/multi-font-preview/multi-font-preview.py arkandis.tuxfamily.org
Using face_name 'Solothurn-Regular' for Solothurn-Regular.otf
Using face_name 'TribunADFStd-Regular' for TribunADFStd-Regular.otf
Using face_name 'IkariusADFStd-Regular' for IkariusADFStd-Regular.otf
Using face_name 'MekanusADFStd-Regular' for MekanusADFStd-Regular.otf
Using face_name 'AccanthisADFStd-Regular' for AccanthisADFStd-Regular.otf
Using face_name 'BaskervaldADFStd-BoldItalic' for BaskervaldADFStd-BoldItalic.otf
Using face_name 'BaskervaldADFStd-Bold' for BaskervaldADFStd-Bold.otf
Using face_name 'BaskervaldADFStd-HeavyItalic' for BaskervaldADFStd-HeavyItalic.otf
Using face_name 'BaskervaldADFStd-Heavy' for BaskervaldADFStd-Heavy.otf
Using face_name 'BaskervaldADFStd-Italic' for BaskervaldADFStd-Italic.otf
Using face_name 'BaskervaldADFStd' for BaskervaldADFStd.otf
Using face_name 'Berenis ADF Pro Regular' for BerenisADFPro-Regular.otf
Using face_name 'AurelisADFNo2Std-Regular' for AurelisADFNo2Std-Regular.otf
Using face_name 'LibrisADFStd-Regular' for LibrisADFStd-Regular.otf
Using face_name 'UniversalisADFStd-Regular' for UniversalisADFStd-Regular.otf
Using face_name 'IrianisADFStd-Regular' for IrianisADFStd-Regular.otf
Using face_name 'Romande ADF Std Regular' for RomandeADFStd-Regular.ttf
Using face_name 'ElectrumADFExp-Regular' for ElectrumADFExp-Regular.otf
Using face_name 'GilliusADF-Regular' for GilliusADF-Regular.otf
Using face_name 'MintSpirit-Regular' for MintSpirit-Regular.otf
Using face_name 'Mintysis Regular' for MintysisAH-Regular.ttf
```

Ok, but keep track of whether the file already existed there, and make a was_installed = False attribute for FontInfo, and if it was already present before copying, set was_installed = True then don't delete it afterward.

The problem was that you were getting the face name but that was not accepted by Python. Try the new get family name function and use that instead. Comment any cache refreshing code for now, and remove any other odd stuff we tried like manual on_paint to simpify the code, and just use a label and setfont. Here is a correct usage example, along with the new function (proven to work):
```
import os
import subprocess
import sys

from pathlib import Path

import wx

from fontTools.ttLib import TTFont

def get_font_family_name(font_path):
    """Reads the Font Family Name (ID 1) from a font file."""
    font = TTFont(font_path)
    # ID 1 is the Font Family Name
    family_name = font['name'].getDebugName(1)

    # Optional: If ID 1 is empty, fallback to ID 16 (Preferred Family)
    if not family_name:
        family_name = font['name'].getDebugName(16)

    return family_name

class FontWindow(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Debug Font Loader", size=(600, 400))

        # 1. Path Setup
        raw_path = "~/Nextcloud/Fonts/arkandis.tuxfamily.org/Electrum-Exp/OTF/ElectrumADFExp-Regular.otf"
        font_path = str(Path(raw_path).expanduser())

        print(f"--- Font Loading Process ---")
        print(f"Target Path: {font_path}")

# 2. Extract Family Name (ID 1)
        family_name = get_font_family_name(font_path)
        print(f"Extracted Family Name: {family_name}")

        # 3. Register Font (still required)
        if not wx.Font.AddPrivateFont(font_path):
            raise RuntimeError(f"wx.Font.AddPrivateFont failed to load: {font_path}")

        # 4. Create Font using the Family Name
        # Note: We provide familyName to faceName argument, and use font parameters
        # to define the specific style
        custom_font = wx.Font(24, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                              wx.FONTWEIGHT_NORMAL, faceName=family_name)

        # Check validity
        is_valid = wx.FontEnumerator.IsValidFacename(family_name)
        print(f"Is font face in system: {is_valid}")

        # ADD THIS: Force the font to resolve if it didn't trigger initially
        # if custom_font.GetFaceName() != face_name:
        #     print(f"Warning: wx failed to bind to {face_name}, trying a fallback...")
            # On some Linux distros, you might need to use the family name
            # or ensure the font is truly initialized via a paint event.
        # 5. Debug Verification
        actual_face_name = custom_font.GetFaceName()
        print(f"wx.Font internal face name: {actual_face_name}")

        # 6. UI Implementation
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # this_face_name = face_name  # fails with Face name
        # this_face_name = "Electrum ADF Exp"  # works with family name
        # print(f"Is font face in system: {wx.FontEnumerator.IsValidFacename(face_name)}")
        # print(f"Is font face in system: {wx.FontEnumerator.IsValidFacename(this_face_name)}")

        label = wx.StaticText(panel, label=f"Font Face: {actual_face_name}")
        label.SetFont(custom_font)
        sizer.Add(label, 0, wx.ALL, 20)

        panel.SetSizer(sizer)
        self.Show()

if __name__ == "__main__":
    app = wx.App()
    frame = FontWindow()
    app.MainLoop()
```
- above is pasted from Gemini

Ok, it is much better now! Fonts that were previously installed work only though, so lets re-add font list reload code. Make a separate loop for installing the fonts, so that the font list only gets reloaded once. Then loop through again and do the label creation code, but keep it intact since it now sets the font correctly.

It still only is able to load fonts that were installed before the program started.

Ok, now make less space between the fonts, and make a number up down spinner at the  top (min 6, max 999, default 14) for the font size, that regenerates the labels on change.

Defer initialization using wx.After. Make a status bar. Show the loading fonts message there before starting the thread that does font loading and font list reload. Show all status messages there (other than list items such as font names)

Make the background white and the font color black.

Remove horizontal rules so more labels fit. Rename symbols from Reviewer to Preview and change title of argparse and window both to "Hierosoft Multi-Font Preview" and set temp prefix to multi-font-preview.

Put no space between the labels.

Add 3px before each label, 16px on left.

Add a "File" menu with two options: "Open Directory..." and "Save Image..." (dialog with "PNG (*.png)" filter). Open directory should clear all labels and start the loading process (show loading status then start thread) over again. The Save Image should save the entire white area including scrollable parts if possible.

Failed to save image:
'ScrolledWindow' object has no attribute 'DrawToDC'

Ok, but it only works the first time. If I open another directory, after "Building font preview..." caption appears, I get:
```
RuntimeError: wrapped C/C++ object of type ScrolledWindow has been deleted
Traceback (most recent call last):
  File "/home/owner/Nextcloud/d.python/wx/multi-font-preview/multi-font-preview.py", line 306, in on_open_directory
    self.scroll_panel.Destroy()
RuntimeError: wrapped C/C++ object of type ScrolledWindow has been deleted
```
It doesn't seem like we should delete the whole scrolledwindow on open, maybe just its contents?

Set a self.default_dir = None, but whenever a directory is opened at startup or any other time, set that. If not none during open director or save file, use it as the starting directory for the dialogs.

Instead of having a successfully saved dialog, show the outcome in the status bar.
