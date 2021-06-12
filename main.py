import subprocess
from tkinter import ttk
import tkinter as tk
from tkinter import *
from tkinter.ttk import *
import json

# site that shows correct way to use a treeview scrollbar
# https://www.pythontutorial.net/tkinter/tkinter-treeview/

# Explains pack grid place
# https://riptutorial.com/tkinter/example/29712/pack--


# Provide a fancier Input
class EntryWithPlaceholder(tk.Entry):
    def __init__(self, master=None, placeholder="PLACEHOLDER", color='grey'):
        super().__init__(master)

        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['fg']

        self.bind("<FocusIn>", self.foc_in)
        self.bind("<FocusOut>", self.foc_out)

        self.put_placeholder()

    def put_placeholder(self):
        self.insert(0, self.placeholder)
        self['fg'] = self.placeholder_color

    def foc_in(self, *args):
        if self['fg'] == self.placeholder_color:
            self.delete('0', 'end')
            self['fg'] = self.default_fg_color

    def foc_out(self, *args):
        if not self.get():
            self.put_placeholder()

# Provide a class based interface to communicate with vcpkg.exe
class VCPKGInterface:
    def __init__(self):
        # Location of vcpkg execuatable TODO: Don't hardcode
        self.vcpkg_exe_path = "C:/Code/vcpkg/vcpkg.exe"

        # Cached copy of installed packages
        self.installed_packages = None

        # The cached list of installed packages is dirty and must be refreshed
        self.installed_packages_dirty = False


    def get_installed_packages(self):
        # vcpkg.exe list --x-json
        if self.installed_packages is None or self.installed_packages_dirty is True:
            process = subprocess.Popen([self.vcpkg_exe_path, 'list', '--x-json'], stdout=subprocess.PIPE)
            stdout = process.communicate()[0].decode("utf-8")
            self.installed_packages = json.loads(stdout)
            self.installed_packages_dirty = False

        return self.installed_packages

# Main GUI Window
class OverviewWindow:
    def __init__(self, vcpkg_obj: VCPKGInterface):
        self.vcpkg_obj = vcpkg_obj
        self.root_window = Tk()
        self.root_window.title('VCPkg GUI Tool')
        self.root_window.geometry('1000x600')

        self.package_name_to_treeview_index_dict = dict()
        self.next_treeview_id = 0

        frame1 = ttk.Frame(self.root_window)
        frame1.pack(fill=X,side=TOP)

        menubar = Menu(self.root_window)

        # App Menu
        app_menu = Menu(menubar, tearoff=0)
        app_menu.add_command(label="Select VCPkg Location")
        app_menu.add_separator()
        app_menu.add_command(label="Exit", command=self.root_window.quit)
        menubar.add_cascade(label="App", menu=app_menu)

        # Integrate Menu
        integrate_menu = Menu(menubar, tearoff=0)
        integrate_menu.add_command(label="Install", state=DISABLED)
        integrate_menu.add_command(label="Remove")
        integrate_menu.add_command(label="PowerShell Tab Complete")
        integrate_menu.add_separator()
        integrate_menu.add_command(label="Project")
        menubar.add_cascade(label="Integrate", menu=integrate_menu)

        # Package Menu
        package_menu = Menu(menubar, tearoff=0)
        package_menu.add_command(label="Install New", command=self.install_new_vc_package)
        package_menu.add_separator()
        package_menu.add_command(label="Open Details")
        package_menu.add_command(label="Remove")
        menubar.add_cascade(label="Package", menu=package_menu)

        self.root_window.config(menu=menubar)

        # Toolbar
        # menubutton = Menubutton(frame1, text="Package")
        # menubutton.pack(side=LEFT)
        # menubutton2 = Menubutton(frame1, text="Packages")
        # menubutton2.pack(side=LEFT)
        # menubutton.menu = Menu(menubutton, tearoff=0)
        # menubutton["menu"] = menubutton.menu

        # Installed Packages label
        installed_packages = ttk.Label(self.root_window, text = "Installed Packages", justify=LEFT)
        installed_packages.pack(anchor="w")

        frame2 = ttk.Frame(self.root_window)
        frame2.pack(expand=1, fill=BOTH, side=LEFT)

        # Scrollbars
        self.tv_vscb = ttk.Scrollbar(self.root_window, orient=VERTICAL)
        self.tv_vscb.pack(side=RIGHT, fill=Y);
        self.tv_hscb = ttk.Scrollbar(frame2, orient=HORIZONTAL)
        self.tv_hscb.pack(side=BOTTOM, fill=X)

        # Installed Packages Treeview
        self.tv_ip = ttk.Treeview(frame2, yscroll=self.tv_vscb.set, xscroll=self.tv_hscb.set)
        self.tv_ip['columns'] = ('package_name', 'version', 'triplet', 'description')

        self.tv_ip.column('#0', width=20, stretch=NO)
        self.tv_ip.column('package_name', width=140, anchor=W, stretch=NO)
        self.tv_ip.column('version', width=90, anchor=W, stretch=NO)
        self.tv_ip.column('triplet', width=100, anchor=W, stretch=NO)
        self.tv_ip.column('description', width=160, anchor=W, stretch=YES)

        self.tv_ip.heading('package_name', text='Package Name', anchor=W)
        self.tv_ip.heading('version', text='Version', anchor=W)
        self.tv_ip.heading('triplet', text='Triplet', anchor=W)
        self.tv_ip.heading('description', text='Description', anchor=W)
        self.tv_ip.pack(expand=1, fill=BOTH, side=TOP)

        # Scrollbars
        self.tv_vscb.configure(command=self.tv_ip.yview)
        self.tv_hscb.configure(command=self.tv_ip.xview)
        self.tv_hscb.pack(anchor=SE);

        self.tv_ip.columnconfigure(4, minsize=500)

        self.init_install_new_vc_pkg_window()

        # Temporary while working on search window
        # self.install_new_vc_package()

    def init_install_new_vc_pkg_window(self):
        self.install_new_pkg_window = tk.Toplevel(self.root_window)
        self.install_new_pkg_class = InstallNewPackageWindow(self.install_new_pkg_window)

    def install_new_vc_package(self):
        self.install_new_pkg_window.update()
        self.install_new_pkg_window.deiconify()

    # add a new package to the treeview. If we have more than one architecture installed, then make children
    def add_installed_package(self, package_info):
        # self.package_name_to_treeview_index_dict

        package_name = package_info['package_name']
        triplet = package_info['triplet']
        version = package_info['version']
        port_version = package_info['port_version']
        features = package_info['features']
        desc = package_info['desc']

        parent_id = None

        if package_name not in self.package_name_to_treeview_index_dict:
            self.package_name_to_treeview_index_dict[package_name] = self.next_treeview_id
        else:
            parent_id = self.package_name_to_treeview_index_dict[package_name]

        if parent_id is None:
            self.tv_ip.insert(parent='', index=tk.END, iid=self.next_treeview_id, text='', values=(package_name, version, triplet, desc))
        else:
            self.tv_ip.insert(parent=parent_id, index=tk.END, iid=self.next_treeview_id, text='', values=(package_name, version, triplet, desc))

        self.next_treeview_id = self.next_treeview_id + 1


    def populate_installed_packages(self):
        tv_ip_id=0

        packages = self.vcpkg_obj.get_installed_packages()
        for package in packages:
            self.add_installed_package(packages[package])

        self.tv_vscb.configure(command=self.tv_ip.yview)

        # self.tv_ip.insert(parent='', index=0, iid=0, text='', values=('1', 'Vineet', 'Alpha'))
        # self.tv_ip.insert(parent='', index=1, iid=1, text='', values=('2', 'Anil', 'Bravo'))
        # self.tv_ip.insert(parent='', index=2, iid=2, text='', values=('3', 'Vinod', 'Charlie'))
        # self.tv_ip.insert(parent='', index=3, iid=3, text='', values=('4', 'Vimal', 'Delta'))
        # self.tv_ip.insert(parent='', index=4, iid=4, text='', values=('5', 'Manjeet', 'Echo'))

    def open_gui(self):
        self.populate_installed_packages()
        self.root_window.mainloop()

class InstallNewPackageWindow:
    def __init__(self, tk_window):
        self.tk_window = tk_window;
        self.tk_window.withdraw()
        self.tk_window.title('Install a new library')
        self.tk_window.protocol("WM_DELETE_WINDOW", self.close_install_pkg_window)

        frame1 = Frame(self.tk_window)
        frame1.pack(side=TOP, fill=X, expand=0)

        self.search_entry = EntryWithPlaceholder(frame1, "Enter a package name to search for")
        self.search_entry.pack(side=LEFT, fill=BOTH, expand=1)

        self.search_but = Button(frame1, text='Search')
        self.search_but.pack(side=RIGHT)

        # Search results area
        frame2 = ttk.Frame(self.tk_window)
        frame2.pack(expand=1, fill=BOTH, side=BOTTOM)

        frame3 = ttk.Frame(frame2)
        frame3.pack(expand=1, fill=BOTH, side=LEFT)

        # Scrollbars
        self.tv_vscb = ttk.Scrollbar(frame2, orient=VERTICAL)
        self.tv_vscb.pack(side=RIGHT, fill=Y)
        self.tv_hscb = ttk.Scrollbar(frame3, orient=HORIZONTAL)
        self.tv_hscb.pack(side=BOTTOM, fill=X)

        # Installed Packages Treeview
        self.tv_ip = ttk.Treeview(frame3, yscroll=self.tv_vscb.set, xscroll=self.tv_hscb.set)
        self.tv_ip['columns'] = ('package_name', 'version', 'triplet', 'description')

        self.tv_ip.column('#0', width=0, stretch=NO)
        self.tv_ip.column('package_name', width=140, anchor=W, stretch=NO)
        self.tv_ip.column('version', width=90, anchor=W, stretch=NO)
        self.tv_ip.column('triplet', width=100, anchor=W, stretch=NO)
        self.tv_ip.column('description', width=160, anchor=W, stretch=YES)

        self.tv_ip.heading('package_name', text='Package Name', anchor=W)
        self.tv_ip.heading('version', text='Version', anchor=W)
        self.tv_ip.heading('triplet', text='Triplet', anchor=W)
        self.tv_ip.heading('description', text='Description', anchor=W)
        self.tv_ip.pack(expand=1, fill=BOTH, side=TOP)



    def close_windows(self):
        self.tk_window.withdraw()

    def close_install_pkg_window(self):
        self.tk_window.withdraw()

if __name__ == '__main__':
    vcpkg = VCPKGInterface()
    search_package_gui = OverviewWindow(vcpkg)
    search_package_gui.open_gui()
