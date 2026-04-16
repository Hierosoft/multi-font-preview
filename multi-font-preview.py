import os
import zipfile
import argparse
import tempfile
import shutil
import atexit
import sys
import subprocess
import threading
from collections import OrderedDict
import wx
from fontTools.ttLib import TTFont


class FontInfo:
    def __init__(self, full_path=None, name=None, parent=None, zip_path=None, zip_internal=None):
        self.full_path = full_path
        self.name = name or (os.path.basename(full_path) if full_path else os.path.basename(zip_internal or ''))
        self.parent = parent
        self.zip_path = zip_path
        self.zip_internal = zip_internal
        self.is_from_zip = zip_path is not None
        self.was_installed = False
        self.installed_path = None


class SearchState:
    def __init__(self):
        self.found = OrderedDict()


def get_regular(font_list):
    candidates = []
    for font in font_list:
        lower = font.name.lower()
        if '-r' in lower or 'regular' in lower:
            candidates.append((len(font.name), font))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def get_font_family_name(font_path):
    try:
        font = TTFont(font_path)
        family_name = font['name'].getDebugName(1)
        if not family_name:
            family_name = font['name'].getDebugName(16)
        if not family_name:
            family_name = os.path.splitext(os.path.basename(font_path))[0]
        return family_name
    except Exception:
        return os.path.splitext(os.path.basename(font_path))[0]


def register_font_linux(fi: FontInfo):
    src_path = fi.full_path
    if not os.path.isfile(src_path):
        return None

    user_font_dir = os.path.expanduser("~/.local/share/fonts")
    os.makedirs(user_font_dir, exist_ok=True)

    dest_path = os.path.join(user_font_dir, os.path.basename(src_path))

    try:
        if os.path.exists(dest_path):
            fi.was_installed = True
        else:
            shutil.copy2(src_path, dest_path)
            fi.was_installed = False
            fi.installed_path = dest_path
        return get_font_family_name(src_path)
    except Exception as e:
        print(f"Failed to register {fi.name}: {e}", file=sys.stderr)
        return None


def collect_fonts(directory):
    state = SearchState()
    for root, _, files in os.walk(directory):
        for f in files:
            lower_f = f.lower()
            if lower_f.endswith(('.ttf', '.otf')):
                full_path = os.path.join(root, f)
                parent_key = root
                if parent_key not in state.found:
                    state.found[parent_key] = []
                state.found[parent_key].append(FontInfo(full_path=full_path, parent=parent_key))

            elif lower_f.endswith('.zip'):
                zip_full = os.path.join(root, f)
                parent_key = zip_full
                try:
                    with zipfile.ZipFile(zip_full) as zf:
                        for member in zf.infolist():
                            if not member.is_dir() and member.filename.lower().endswith(('.ttf', '.otf')):
                                if parent_key not in state.found:
                                    state.found[parent_key] = []
                                name = os.path.basename(member.filename)
                                fi = FontInfo(name=name, parent=parent_key,
                                              zip_path=zip_full, zip_internal=member.filename)
                                state.found[parent_key].append(fi)
                except Exception as e:
                    print(f"Warning: could not read ZIP {zip_full} – {e}")
    return state


class FontReviewerFrame(wx.Frame):
    def __init__(self, directory):
        super().__init__(None, title="Hierosoft Multi-Font Preview", size=(1050, 750))

        self.directory = directory
        self.default_dir = None
        self.temp_dir = tempfile.mkdtemp(prefix="multi-font-preview_")
        self.all_fontinfos = []
        self.found_dict = None
        self.current_size = 14
        self.regular_only = True

        self.scroll_panel = None
        self.main_sizer = None
        self.spinner = None
        self.regular_checkbox = None
        self.activity = None
        self.status_label = None

        # Store all created labels: (StaticText, lower_name)
        self.font_labels = []

        self.CreateStatusBar()
        self.create_status_panel()

        self.create_menu()

        atexit.register(self.cleanup_temp)

        if os.path.isdir(directory):
            self.default_dir = directory

        wx.CallAfter(self.start_loading)

        self.Centre()

    def create_status_panel(self):
        self.status_panel = wx.Panel(self.GetStatusBar())
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.status_label = wx.StaticText(self.status_panel, label="Initializing...")
        self.activity = wx.ActivityIndicator(self.status_panel, size=(20, 20))
        self.activity.Hide()

        sizer.Add(self.status_label, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        sizer.Add(self.activity, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        self.status_panel.SetSizer(sizer)
        self.Bind(wx.EVT_SIZE, self.on_frame_size)

    def on_frame_size(self, event):
        if hasattr(self, 'status_panel'):
            rect = self.GetStatusBar().GetFieldRect(0)
            self.status_panel.SetSize(rect)
        event.Skip()

    def set_status_text(self, text):
        if self.status_label:
            self.status_label.SetLabel(text)

    def start_activity(self):
        if self.activity:
            self.activity.Show()
            self.activity.Start()

    def stop_activity(self):
        if self.activity:
            self.activity.Stop()
            self.activity.Hide()

    def create_menu(self):
        menubar = wx.MenuBar()
        file_menu = wx.Menu()

        open_item = file_menu.Append(wx.ID_OPEN, "Open Directory...\tCtrl+O")
        save_item = file_menu.Append(wx.ID_SAVEAS, "Save Image...\tCtrl+S")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, "Exit\tCtrl+Q")

        self.Bind(wx.EVT_MENU, self.on_open_directory, open_item)
        self.Bind(wx.EVT_MENU, self.on_save_image, save_item)
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), exit_item)

        menubar.Append(file_menu, "&File")
        self.SetMenuBar(menubar)

    def cleanup_temp(self):
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass
        for fi in self.all_fontinfos:
            if not fi.was_installed and fi.installed_path and os.path.isfile(fi.installed_path):
                try:
                    os.remove(fi.installed_path)
                except Exception:
                    pass

    def start_loading(self, new_directory=None):
        if new_directory:
            self.directory = new_directory
            self.default_dir = new_directory

        self.set_status_text("Scanning fonts...")
        self.start_activity()

        thread = threading.Thread(target=self.load_fonts_background, daemon=True)
        thread.start()

    def load_fonts_background(self):
        try:
            state = collect_fonts(self.directory)
            self.found_dict = state.found

            wx.CallAfter(self.set_status_text, "Extracting and registering fonts...")
            done_names = set()
            self.all_fontinfos = []
            self.font_labels = []

            for fontlist in self.found_dict.values():
                for fi in fontlist:
                    if fi.name in done_names:
                        continue
                    done_names.add(fi.name)

                    if fi.is_from_zip:
                        try:
                            with zipfile.ZipFile(fi.zip_path) as zf:
                                safe_name = os.path.basename(fi.zip_internal).replace('/', '_').replace('\\', '_')
                                extract_to = os.path.join(self.temp_dir, safe_name)
                                zf.extract(fi.zip_internal, self.temp_dir)

                                extracted_actual = os.path.join(self.temp_dir, fi.zip_internal)
                                if os.path.isfile(extracted_actual) and extracted_actual != extract_to:
                                    if os.path.exists(extract_to):
                                        os.remove(extract_to)
                                    os.rename(extracted_actual, extract_to)
                                fi.full_path = extract_to
                        except Exception as e:
                            print(f"Failed to extract {fi.name}: {e}")
                            continue

                    if os.path.isfile(fi.full_path):
                        self.all_fontinfos.append(fi)
                        register_font_linux(fi)

            wx.CallAfter(self.set_status_text, "Refreshing system font cache...")
            subprocess.call(["fc-cache", "-f"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            wx.CallAfter(self.build_ui)

        except Exception as e:
            wx.CallAfter(self.set_status_text, f"Error: {e}")
            print(f"Loading error: {e}", file=sys.stderr)
        finally:
            wx.CallAfter(self.stop_activity)

    def build_ui(self):
        self.set_status_text("Building font preview...")

        if not self.scroll_panel:
            top_panel = wx.Panel(self)
            top_sizer = wx.BoxSizer(wx.HORIZONTAL)

            top_sizer.Add(wx.StaticText(top_panel, label="Font Size: "), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
            self.spinner = wx.SpinCtrl(top_panel, value=str(self.current_size), min=6, max=999, initial=self.current_size)
            self.spinner.Bind(wx.EVT_SPINCTRL, self.on_size_change)
            top_sizer.Add(self.spinner, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)

            self.regular_checkbox = wx.CheckBox(top_panel, label="Regular Only (if present)")
            self.regular_checkbox.SetValue(self.regular_only)
            self.regular_checkbox.Bind(wx.EVT_CHECKBOX, self.on_regular_checkbox)
            top_sizer.Add(self.regular_checkbox, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)

            top_sizer.AddStretchSpacer()
            top_panel.SetSizer(top_sizer)

            self.scroll_panel = wx.ScrolledWindow(self)
            self.scroll_panel.SetScrollRate(20, 20)
            self.scroll_panel.SetBackgroundColour(wx.WHITE)

            self.main_sizer = wx.BoxSizer(wx.VERTICAL)

            outer_sizer = wx.BoxSizer(wx.VERTICAL)
            outer_sizer.Add(top_panel, 0, wx.EXPAND | wx.ALL, 5)
            outer_sizer.Add(self.scroll_panel, 1, wx.EXPAND)

            self.SetSizer(outer_sizer)
            self.Layout()

        self.rebuild_labels(full_rebuild=True)

        self.Fit()
        current_size = self.GetSize()
        self.SetMinSize((950, 600))
        self.SetSize(max(current_size[0], 1050), max(current_size[1], 750))

        self.set_status_text("Ready - Use spinner to change font size")
        self.stop_activity()

    def rebuild_labels(self, full_rebuild=False):
        if not self.main_sizer:
            return

        if full_rebuild:
            # First time: create widgets
            self.main_sizer.Clear(True)
            self.font_labels = []

            for fontlist in self.found_dict.values():
                for fi in fontlist:
                    if not os.path.isfile(fi.full_path):
                        continue

                    display_name = os.path.splitext(fi.name)[0]
                    family_name = get_font_family_name(fi.full_path)

                    label = wx.StaticText(self.scroll_panel, label=display_name)
                    label.SetForegroundColour(wx.BLACK)

                    custom_font = wx.Font(self.current_size,
                                          wx.FONTFAMILY_DEFAULT,
                                          wx.FONTSTYLE_NORMAL,
                                          wx.FONTWEIGHT_NORMAL,
                                          faceName=family_name)

                    if not custom_font.IsOk():
                        custom_font = wx.Font(self.current_size, wx.FONTFAMILY_DEFAULT,
                                              wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

                    label.SetFont(custom_font)

                    self.font_labels.append((label, display_name.lower()))
                    self.main_sizer.Add(label, 0, wx.TOP | wx.LEFT, 3, 16)

        else:
            # Filter mode: hide all, then show only the ones we want
            for label, lower_name in self.font_labels:
                label.Hide()

            for label, lower_name in self.font_labels:
                if not self.regular_only or ('-r' in lower_name or 'regular' in lower_name):
                    label.Show()
                    # self.main_sizer.Add(label, 0, wx.TOP | wx.LEFT, 3, 16)

        self.scroll_panel.SetSizer(self.main_sizer)
        self.scroll_panel.Layout()
        self.scroll_panel.Refresh()
        if full_rebuild:
            self.rebuild_labels(False)

    def on_size_change(self, event):
        new_size = self.spinner.GetValue()
        if new_size != self.current_size:
            self.current_size = new_size
            self.rebuild_labels(full_rebuild=True)

    def on_regular_checkbox(self, event):
        self.regular_only = self.regular_checkbox.GetValue()
        self.rebuild_labels(full_rebuild=False)

    def on_open_directory(self, event):
        start_dir = self.default_dir if self.default_dir and os.path.isdir(self.default_dir) else self.directory

        dlg = wx.DirDialog(self, "Choose font directory", start_dir,
                           style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            new_dir = dlg.GetPath()
            self.default_dir = new_dir
            self.set_status_text(f"Opening directory: {new_dir}")
            if self.main_sizer:
                self.main_sizer.Clear(True)
            self.all_fontinfos = []
            self.found_dict = None
            self.font_labels = []
            wx.CallAfter(self.start_loading, new_dir)
        dlg.Destroy()

    def on_save_image(self, event):
        if not self.scroll_panel or not self.found_dict:
            self.set_status_text("No preview available to save.")
            return

        start_dir = self.default_dir if self.default_dir else os.getcwd()

        dlg = wx.FileDialog(self, "Save Preview Image as PNG",
                            defaultDir=start_dir,
                            wildcard="PNG files (*.png)|*.png",
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            filepath = dlg.GetPath()
            if not filepath.lower().endswith('.png'):
                filepath += '.png'

            try:
                virt_size = self.scroll_panel.GetVirtualSize()
                width = max(virt_size.GetWidth(), self.scroll_panel.GetClientSize().GetWidth())
                height = virt_size.GetHeight()

                bmp = wx.Bitmap(width, height)
                mem_dc = wx.MemoryDC(bmp)
                mem_dc.SetBackground(wx.WHITE_BRUSH)
                mem_dc.Clear()

                dc = wx.ClientDC(self.scroll_panel)
                mem_dc.Blit(0, 0, width, height, dc, 0, 0)

                img = bmp.ConvertToImage()
                img.SaveFile(filepath, wx.BITMAP_TYPE_PNG)

                self.set_status_text(f"Saved: {os.path.basename(filepath)}")

            except Exception as e:
                self.set_status_text(f"Save failed: {str(e)}")
                print(f"Save error: {e}", file=sys.stderr)
        dlg.Destroy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hierosoft Multi-Font Preview")
    parser.add_argument("directory", nargs="?", default=".", help="Directory to scan")
    args = parser.parse_args()

    app = wx.App(False)
    frame = FontReviewerFrame(args.directory)
    frame.Show()
    app.MainLoop()
