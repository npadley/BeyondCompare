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
    # If we are on windows - set a custom path
    if is_windows():
        if os.path.exists(get_location()):
            pass
        elif os.path.exists("%s\\Beyond Compare 4\\BCompare.exe" % os.environ['ProgramFiles(x86)']):
            settings().set("beyond_compare_path", '%s\\Beyond Compare 4\\BCompare.exe'
                           % os.environ['ProgramFiles(x86)'])
            sublime.save_settings("BeyondCompare.sublime-settings")
        elif os.path.exists("%s\\Beyond Compare 4\\BCompare.exe" % os.environ['ProgramFiles']):
            settings().set("beyond_compare_path", "%s\\Beyond Compare 4\\BCompare.exe" % os.environ['ProgramFiles'])
            sublime.save_settings("BeyondCompare.sublime-settings")
        else:
            sublime.error_message(
                "Could not find Beyond Compare. Please set the path to your tool in BeyondCompare.sublime-settings.")


def recordActiveFile(f):
    global fileA
    global fileB
    fileB = fileA
    fileA = f


def runBeyondCompare():
    if fileA is not None and fileB is not None:
        print(
            "BeyondCompare comparing: LEFT [" + fileA + "] | RIGHT [" + fileB + "]")
        subprocess.Popen([get_location(), fileA, fileB])
        print("Should be open...")
    else:
        sublime.error_message(
            "You must have activated TWO files to compare.\nPlease select two tabs to compare and try again")


class BeyondCompareCommand(sublime_plugin.ApplicationCommand):

    def run(self):
        if os.path.exists(get_location()):
            runBeyondCompare()
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
                        runBeyondCompare()
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


class BeyondCompareFileListener(sublime_plugin.EventListener):
    def on_activated(self, view):
        if view.file_name() is not None and view.file_name() != fileA:
            recordActiveFile(view.file_name())
