import sublime
import sublime_plugin
import os
import webbrowser
import subprocess

fileA = fileB = None


def settings():
    return sublime.load_settings('BeyondCompare.sublime-settings')


def is_windows():
    return sublime.platform() == "windows"


def is_osx():
    return sublime.platform() == "osx"


def get_location():
    if isinstance(settings().get('beyond_compare_path'), dict):
        return settings().get('beyond_compare_path').get(sublime.platform(), "")
    else:
        return settings().get('beyond_compare_path')


def plugin_loaded() -> None:
    if not is_windows():
        return
    location = get_location()
    if location and os.path.exists(location):
        return

    # Prefer BC5, but keep detecting BC4 for users who have not upgraded.
    for version in (5, 4):
        for variable in ('ProgramFiles', 'ProgramFiles(x86)'):
            root = os.environ.get(variable)
            if not root:
                continue
            path = os.path.join(root, 'Beyond Compare %s' % version, 'BCompare.exe')
            if os.path.exists(path):
                settings().set("beyond_compare_path", path)
                sublime.save_settings("BeyondCompare.sublime-settings")
                return

    sublime.error_message(
        "Could not find Beyond Compare. Please set the path to your tool in BeyondCompare.sublime-settings.")


def recordActiveFile(f):
    global fileA
    global fileB
    fileB = fileA
    fileA = f


def runBeyondCompare(file_left, file_right):
    if file_left is not None and file_right is not None:
        print(
            "BeyondCompare comparing: LEFT [" + file_left + "] | RIGHT [" + file_right + "]")
        subprocess.Popen([get_location(), file_left, file_right])
        print("Should be open...")
    else:
        sublime.error_message(
            "You must have activated TWO files to compare.\nPlease select two tabs to compare and try again")


def compareFiles(file_left, file_right):
    if os.path.exists(get_location()):
        runBeyondCompare(file_left, file_right)
    elif is_osx():
        commandLinePrompt = sublime.ok_cancel_dialog(
            "Could not find bcompare.\nPlease install the command line tools.", "Do it now!")
        if commandLinePrompt:
            new = 2  # open in a new tab, if possible
            url = "http://www.scootersoftware.com/support.php?zz=kb_OSXInstallCLT"
            webbrowser.open(url, new=new)
            bCompareInstalled = sublime.ok_cancel_dialog(
                "Once you have installed the command line tools, click the ok button to continue")
            if bCompareInstalled:
                if os.path.exists("/usr/local/bin/bcompare"):
                    runBeyondCompare(file_left, file_right)
                else:
                    sublime.error_message(
                        "Still could not find bcompare. \nPlease make sure it exists at:\n/usr/local/bin/bcompare\n"
                        "and try again")
            else:
                sublime.error_message("Please try again after you have command line tools installed.")
        else:
            sublime.error_message("Please try again after you have command line tools installed.")
    else:
        sublime.error_message(
            "Could not find Beyond Compare. Please set the path to your tool in BeyondCompare.sublime-settings.")


class BeyondCompareCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        compareFiles(fileA, fileB)


class BeyondCompareTabCommand(sublime_plugin.WindowCommand):
    def comparison_paths(self, group, index):
        if group < 0 or group >= self.window.num_groups():
            return None
        # Tab menu indices refer to sheets, which can also include non-text tabs.
        sheets = self.window.sheets_in_group(group)
        if index < 0 or index >= len(sheets):
            return None
        active = self.window.active_view()
        target = sheets[index].view()
        if active is None or target is None:
            return None
        file_left, file_right = active.file_name(), target.file_name()
        if not file_left or not file_right or file_left == file_right:
            return None
        return file_left, file_right

    def is_enabled(self, group=-1, index=-1):
        return self.comparison_paths(group, index) is not None

    def run(self, group=-1, index=-1):
        paths = self.comparison_paths(group, index)
        if paths is not None:
            compareFiles(*paths)


class BeyondCompareFileListener(sublime_plugin.EventListener):
    def on_activated(self, view):
        if view.file_name() is not None and view.file_name() != fileA:
            recordActiveFile(view.file_name())
