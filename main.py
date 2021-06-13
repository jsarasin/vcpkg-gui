import subprocess
from tkinter import ttk
import tkinter as tk
from tkinter import *
from tkinter.ttk import *
import json
from multiprocessing import Process
from tkinter import messagebox
import os

# site that shows correct way to use a treeview scrollbar
# https://www.pythontutorial.net/tkinter/tkinter-treeview/

# Explains pack grid place
# https://riptutorial.com/tkinter/example/29712/pack--



# https://www.py4u.net/discuss/23012
# Get a text name for what the user clicked on
# if treeview.identify_region(event.x, event.y) == "separator":


# get what column the user clicked on
# curItem = self.tree.item(self.tree.focus())
# col = self.tree.identify_column(event.x)

# Good explanation of grid
# https://www.pythontutorial.net/tkinter/tkinter-grid/


class EntryWithPlaceholder(tk.Entry):
    """ Provide a fancier Input
    """
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


class VCPKGInterface:
    # Provide a class based interface to communicate with vcpkg.exe
    def __init__(self):
        # Location of vcpkg execuatable TODO: Don't hardcode
        # self.vcpkg_exe_path = "/home/james/Code/vcpkg/vcpkg"
        self.vcpkg_exe_path = "C:/Code/vcpkg/vcpkg.exe"

        # Cached copy of installed packages
        self.installed_packages = None

        # The cached list of installed packages is dirty and must be refreshed
        self.installed_packages_dirty = False

        # Triplets available to be installed
        self.available_triplets = None

        # Cached searches
        self.cached_search_strings = dict()

        self.search_executing = False
    
    def remove_package(self):
        pass
    
    def install_package(self, package_name):
        pass

    def search_for_package(self, search_string):
        def spawn_search(search_string):
            # TODO: vcpkg search command ignores --x-json, look for/submit an issue, maybe it's easy to implement?
            process = subprocess.Popen([self.vcpkg_exe_path, 'search', search_string], stdout=subprocess.PIPE)
            stdout = process.communicate()[0].decode("utf-8")
            
            return stdout
        
        if self.search_executing:
            raise Exception("Cannot execute simultaneous searches")
        
        if search_string in self.cached_search_strings:
            return self.cached_search_strings[search_string]
        
        self.search_executing = True

        results = spawn_search(search_string)

        results_json = self.interpret_search_results(results)
        self.cached_search_strings[search_string] = results_json
        
        self.search_executing = False
        return results_json

    def interpret_search_results(self, results):
        packages = dict()

        for line in results.split('\n'):
            if line.strip() == "":
                break
            
            end_of_pkg_name = line.find(' ')
            package_name = line[0:end_of_pkg_name]
            packages[package_name] = dict()

            start_of_version = line.find(' ', 20)
            if(start_of_version == 20):
                version = line[20:20+17].strip()
                if version != '':
                    has_version = True
                    packages[package_name]['version'] = version

            description = line[38:]
            packages[package_name]['description'] = description
        
        return packages
        
    def get_installed_packages(self):
        # vcpkg.exe list --x-json
        if self.installed_packages is None or self.installed_packages_dirty is True:
            process = subprocess.Popen([self.vcpkg_exe_path, 'list', '--x-json'], stdout=subprocess.PIPE)
            stdout = process.communicate()[0].decode("utf-8")
            self.installed_packages = json.loads(stdout)
            self.installed_packages_dirty = False

        return self.installed_packages

    def get_available_triplets(self):
        if self.available_triplets is None:
            process = subprocess.Popen([self.vcpkg_exe_path, 'help', 'triplets', '--x-json'], stdout=subprocess.PIPE)
            stdout = process.communicate()[0].decode("utf-8")
            # print(stdout)
            # self.available_triplets =

            gathering_builtints = False
            gathering_community = False

            builtins = []
            community = []

            for line in stdout.split('\n'):
                if line.strip() == "VCPKG built-in triplets:":
                    gathering_builtints = True
                    continue

                if gathering_builtints:
                    if line.strip() == "":
                        gathering_builtints = False
                        continue
                    else:
                        builtins.append(line.strip())

                if line.strip() == "VCPKG community triplets:":
                    gathering_community = True
                    continue

                if gathering_community:
                    if line.strip() == "":
                        gathering_community = False
                        continue
                    else:
                        community.append(line.strip())

            self.available_triplets = dict()
            self.available_triplets['builtin'] = builtins
            self.available_triplets['community'] = community

        return self.available_triplets

    def get_package_info(self, package_name):
        results = dict()
        results['package_name'] = package_name
        results['versions'] = dict()
        results['description'] = None

        for pkg_entry, pkg_val in self.installed_packages.items():
            if pkg_val['package_name'] == package_name:
                # If we haven't previously configured the description, do so
                if results['description'] is None:
                    results['description'] = pkg_val['desc']

                # If we haven't previously setup our dict with this version, then do so
                if pkg_val['version'] not in results['versions']:
                    results['versions'][pkg_val['version']] = dict()
                    results['versions'][pkg_val['version']]['architectures'] = []

                # Add this triplet to the version installed
                results['versions'][pkg_val['version']]['architectures'].append(pkg_val['triplet'])

        return results


class OverviewWindow:
    """ Main GUI window, seen when the application
    """
    def __init__(self, vcpkg_obj: VCPKGInterface):
        self.vcpkg_obj = vcpkg_obj
        self.root_window = Tk()
        self.root_window.title('VCPkg GUI Tool')
        self.root_window.geometry('1000x600')

        self.package_name_to_treeview_index_dict = dict()
        self.next_treeview_id = 0

        # Setup the right click context menu for the treeview for a single item
        self.menu_package_context = Menu(self.root_window, tearoff=0)
        self.menu_package_context.add_command(label="Open Details", command=self.show_installed_package_details)
        self.menu_package_context.add_command(label="Configure Architectures")
        self.menu_package_context.add_separator()
        self.menu_package_context.add_command(label="Remove Package")

        # Setup the right click context menu for the treeview for multiple items
        self.menu_packages_context = Menu(self.root_window, tearoff=0)
        self.menu_packages_context.add_command(label="Configure Architectures")
        self.menu_packages_context.add_separator()
        self.menu_packages_context.add_command(label="Remove Packages")

        frame1 = ttk.Frame(self.root_window)
        frame1.pack(fill=X,side=TOP)

        # Setup the main menu for the window
        menubar = Menu(self.root_window)

        # App Menu
        app_menu = Menu(menubar, tearoff=0)
        app_menu.add_command(label="Select VCPkg Location")
        app_menu.add_separator()
        app_menu.add_command(label="Exit", command=self.root_window.quit)
        menubar.add_cascade(label="App", menu=app_menu)

        # Integrate Menu
        integrate_menu = Menu(menubar, tearoff=0)
        integrate_menu.add_command(label="Install System Wide", state=DISABLED)
        integrate_menu.add_command(label="Remove System Wide")
        integrate_menu.add_command(label="PowerShell Tab Complete")
        integrate_menu.add_separator()
        integrate_menu.add_command(label="Project")
        menubar.add_cascade(label="Integrate", menu=integrate_menu)

        # Package Menu
        package_menu = Menu(menubar, tearoff=0)
        package_menu.add_command(label="Install New", command=self.show_install_new_vc_package)
        package_menu.add_separator()
        package_menu.add_command(label="Open Details", command=self.show_installed_package_details)
        package_menu.add_command(label="Remove")
        menubar.add_cascade(label="Package", menu=package_menu)

        self.root_window.config(menu=menubar)

        # Installed Packages label
        installed_packages = ttk.Label(self.root_window, text = "Installed Packages", justify=LEFT)
        installed_packages.pack(anchor="w", side=TOP)

        # Treeview and scrollbar container
        frame2 = ttk.Frame(self.root_window)
        frame2.pack(expand=1, fill=BOTH, side=BOTTOM)
        frame2.columnconfigure(0, weight=1)
        frame2.rowconfigure(0, weight=1)

        # Scrollbars
        self.tv_vscb = ttk.Scrollbar(frame2, orient=VERTICAL)
        self.tv_vscb.grid(row=0, column=1, sticky='nse')
        self.tv_hscb = ttk.Scrollbar(frame2, orient=HORIZONTAL)
        self.tv_hscb.grid(row=1, column=0, sticky='ewn')

        # Installed Packages Treeview
        self.tv_ip = ttk.Treeview(frame2, yscroll=self.tv_vscb.set, xscroll=self.tv_hscb.set)
        self.tv_ip.bind("<Button-3>", self.open_package_context_menu)
        self.tv_ip.bind("<Double-1>", self.open_package_details)
        self.tv_ip['columns'] = ('package_name', 'version', 'triplet', 'description')

        self.tv_ip.column('#0', width=0, stretch=NO)
        self.tv_ip.column('package_name', width=140, anchor=W, stretch=NO)
        self.tv_ip.column('version', width=90, anchor=W, stretch=NO)
        self.tv_ip.column('triplet', width=100, anchor=W, stretch=NO)
        self.tv_ip.column('description', width=160, anchor=W, stretch=NO)

        # print(self.tv_ip.column(0))

        self.tv_ip.heading('package_name', text='Package Name', anchor=W)
        self.tv_ip.heading('version', text='Version', anchor=W)
        self.tv_ip.heading('triplet', text='Triplet', anchor=W)
        self.tv_ip.heading('description', text='Description', anchor=W)
        self.tv_ip.grid(row=0, column=0, sticky='ewns')

        # Link scrollbars
        self.tv_vscb.configure(command=self.tv_ip.yview)
        self.tv_hscb.configure(command=self.tv_ip.xview)

        self.tv_ip.columnconfigure(4, minsize=500)

        self.init_other_windows()

        # Temporary while working on search window
        # self.show_install_new_vc_package()
        # self.show_installed_package_details()

    def open_package_context_menu(self, event):
        clicked_item = self.tv_ip.identify('item',event.x,event.y)
        region_clicked = self.tv_ip.identify_region(event.x, event.y)

        # Only open the dialog if they've rightclicked on an item (Not the header etc)
        if region_clicked != 'cell':
            return

        # If they right clicked on an item that isn't selected already, then change the selection to this single item
        selected_items = self.tv_ip.selection() # TODO: Is this returning the ID's or the index?

        if clicked_item not in selected_items:
            self.tv_ip.selection_set(clicked_item)
            self.tv_ip.update()
            selected_items = self.tv_ip.selection()  # TODO: Is this returning the ID's or the index?

        if len(selected_items) > 1:
            self.menu_packages_context.tk_popup(event.x_root, event.y_root)
        elif len(selected_items) == 1:
            self.menu_package_context.tk_popup(event.x_root, event.y_root)
        else:
            raise Exception("This shouldn't happen")

    def open_package_details(self, event):
        self.show_installed_package_details()

    def init_other_windows(self):
        self.install_new_pkg_window = tk.Toplevel(self.root_window)
        self.install_new_pkg_class = InstallNewPackageWindow(self.install_new_pkg_window, self.vcpkg_obj)

        self.installed_package_details_window = tk.Toplevel(self.root_window)
        self.installed_package_details_class = InstalledPackageDetails(self.installed_package_details_window, self.vcpkg_obj)

    def show_installed_package_details(self):
        item = self.tv_ip.selection() # TODO: Is this returning the ID's or the index?
        # print(type(self.tv_ip.item(item, "text")))
        if len(item) > 1:
            return
        selected_package = item[0]
        selected_package_name = self.tv_ip.item(selected_package)['values'][0]
        self.installed_package_details_class.present_package(selected_package_name)

    def show_install_new_vc_package(self):
        self.install_new_pkg_window.update()
        self.install_new_pkg_window.deiconify()

    def add_installed_package(self, package_info):
        """add a new package to the treeview. If we have more than one architecture installed, then make children
        """
        # self.package_name_to_treeview_index_dict

        package_name = package_info['package_name']
        triplet = package_info['triplet']
        version = package_info['version']
        port_version = package_info['port_version']
        features = package_info['features']
        desc = package_info['desc']

        parent_id = None
        new_treeview_id = None

        if package_name not in self.package_name_to_treeview_index_dict:
            self.package_name_to_treeview_index_dict[package_name] = self.next_treeview_id
            new_treeview_id = self.next_treeview_id
            self.next_treeview_id = self.next_treeview_id + 1
        else:
            parent_id = self.package_name_to_treeview_index_dict[package_name]

        if parent_id is None:
            self.tv_ip.insert(parent='', index=tk.END, iid=new_treeview_id, text='', values=(package_name, version, triplet, desc))
            # self.root_window.update()
            # new_description_bbox = self.tv_ip.bbox(new_treeview_id, column=3)
            # print(new_description_bbox)
            self.tv_ip.column('description', width=2000) #width=new_description_bbox[2]
        else:
            # Query our columns for their current values
            current_triplet_string = self.tv_ip.set(parent_id, column='triplet')
            current_version_string = self.tv_ip.set(parent_id, column='version')

            # Update the triplet column if needed
            if current_triplet_string != triplet:
                new_triplet_string = current_triplet_string + ", " + triplet
                self.tv_ip.set(parent_id, column='triplet', value=new_triplet_string)

            # Update the triplet column if needed
            if current_version_string != version:
                new_version_string = current_version_string + ", " + version
                self.tv_ip.set(parent_id, column='triplet', value=new_version_string)

    def populate_installed_packages(self):
        tv_ip_id = 0

        packages = self.vcpkg_obj.get_installed_packages()
        for package in packages:
            self.add_installed_package(packages[package])
        self.tv_vscb.configure(command=self.tv_ip.yview)

    def open_gui(self):
        self.populate_installed_packages()
        self.root_window.mainloop()


class InstalledPackageDetails:
    """ Details window for installed packages
    """
    def __init__(self, tk_window, vcpkg_obj: VCPKGInterface):
        self.vcpkg_obj = vcpkg_obj
        self.tk_window = tk_window;
        self.tk_window.withdraw()
        self.tk_window.title('Package Details')
        self.tk_window.protocol("WM_DELETE_WINDOW", self.close_install_pkg_window)
        self.tk_window.geometry('500x400')

        frame1 = ttk.Frame(self.tk_window)
        frame1.pack(fill=X, expand=0, padx=30, pady=10)
        frame1.columnconfigure(1, weight=1)

        # Package Name
        label_pkg_name = ttk.Label(frame1, text='Package Name')
        label_pkg_name.grid(row=0, column=0, sticky='e', pady=5, padx=5)
        self.entry_pkg_name = ttk.Entry(frame1, exportselection=0)
        self.entry_pkg_name.insert(END, 'The packages Name')
        self.entry_pkg_name.grid(row=0, column=1, sticky='ewn', pady=5, padx=5)

        # Package Description
        label_pkg_description = ttk.Label(frame1, text='Package Description')
        label_pkg_description.grid(row=1, column=0, sticky='e', pady=5, padx=5)
        self.entry_pkg_description = ttk.Entry(frame1, exportselection=0)
        self.entry_pkg_description.insert(END, 'This is a long detailed writeup about what the package is for')
        self.entry_pkg_description.grid(row=1, column=1, sticky='ewn', pady=5, padx=5)

        # Installed Versions / Architectures viewer
        # Label
        label_instd_ver_pkg = ttk.Label(self.tk_window, text='Installed Versions/Architectures')
        label_instd_ver_pkg.pack(side=TOP, fill=X)

        # Frame
        frame2 = ttk.Frame(self.tk_window)
        frame2.pack(side=LEFT, anchor='ne', fill=BOTH, expand=1)
        frame2.columnconfigure(0, weight=1)
        frame2.rowconfigure(0, weight=1)

        # Treeview
        self.tv_instd_ver_pkg = ttk.Treeview(frame2, selectmode=BROWSE)
        self.tv_instd_ver_pkg.grid(row=0, column=0, sticky='nsew')
        self.tv_instd_ver_pkg.bind('<<TreeviewSelect>>', self.selection_change)

        self.tv_instd_ver_pkg['columns'] = ('version', 'architecture')

        self.tv_instd_ver_pkg.column('#0', width=0, stretch=NO)
        self.tv_instd_ver_pkg.column('version', width=140, anchor=W, stretch=YES)
        self.tv_instd_ver_pkg.column('architecture', width=90, anchor=W, stretch=YES)

        self.tv_instd_ver_pkg.heading('version', text='Version', anchor=W)
        self.tv_instd_ver_pkg.heading('architecture', text='Architecture', anchor=W)

        # Buttons to manipulated installed versions / architeectures
        frame3 = ttk.Frame(self.tk_window)
        frame3.pack(side=LEFT, fill=Y)

        self.but_remove_selected = ttk.Button(frame3, text="Add Version", state=DISABLED)
        self.but_remove_selected.pack(side=TOP, fill=X)

        self.but_remove_selected = ttk.Button(frame3, text="Add Architecture")
        self.but_remove_selected.pack(side=TOP, fill=X)

        self.but_remove_selected = ttk.Button(frame3, text="Remove Selected", state=DISABLED, command=self.remove_selected_package)
        self.but_remove_selected.pack(side=TOP, fill=X)

        self.but_remove_all = ttk.Button(frame3, text="Remove All")
        self.but_remove_all.pack(side=BOTTOM, fill=X)

    def close_install_pkg_window(self):
        self.tk_window.withdraw()

    def present_package(self, package_name):
        self.tk_window.update()
        self.tk_window.deiconify()
        self.tv_instd_ver_pkg.delete(*self.tv_instd_ver_pkg.get_children())
        self.but_remove_selected.config(state=DISABLED)
        self.but_remove_selected.update()
        pkg_info = self.vcpkg_obj.get_package_info(package_name)

        self.entry_pkg_name.delete(0, END)
        self.entry_pkg_name.insert(0, pkg_info['package_name'])

        self.entry_pkg_description.delete(0, END)
        self.entry_pkg_description.insert(0, pkg_info['description'][0])

        next_tv_id = 0

        for package_version, package_prop in pkg_info['versions'].items():
            for package_arch in package_prop['architectures']:
                new_treeview_id = next_tv_id
                self.tv_instd_ver_pkg.insert(parent='', index=tk.END, iid=new_treeview_id, text='', values=(package_version, package_arch))

                next_tv_id = next_tv_id + 1

    def selection_change(self, event):
        selected_items = self.tv_instd_ver_pkg.selection() # TODO: Is this returning the ID's or the index?

        if len(selected_items) == 0:
            self.but_remove_selected.config(state=DISABLED)
        else:
            self.but_remove_selected.config(state=ACTIVE)
    
    def remove_selected_package(self):
        selected_items = self.tv_instd_ver_pkg.selection()

        selected_package = selected_items[0]
        selected_package_architecture = self.tv_instd_ver_pkg.item(selected_package)['values'][1]
        selected_package_name = self.entry_pkg_name.get()

        # print(selected_package_name, selected_package_architecture)
        complete_package_name = selected_package_name + ':' + selected_package_architecture

        answer = messagebox.askokcancel(title="Remove Package", message="Removing package '" + complete_package_name + "'", parent=self.tk_window)

        if answer == True:
            self.vcpkg_obj.remove_package(complete_package_name)


class InstallNewPackageWindow:
    """ Dialog to search for and install new packages
    """
    # Allows users to search for and install packages
    def __init__(self, tk_window, vcpkg_obj: VCPKGInterface):
        self.tk_window = tk_window;
        self.tk_window.withdraw()
        self.tk_window.title('Install a new library')
        self.tk_window.protocol("WM_DELETE_WINDOW", self.close_install_pkg_window)
        self.tk_window.geometry('800x500')
        
        self.vcpkg_obj = vcpkg_obj

        frame1 = Frame(self.tk_window)
        frame1.pack(side=TOP, fill=X, expand=0)

        self.search_entry = EntryWithPlaceholder(frame1, "Enter a package name to search for")
        self.search_entry.pack(side=LEFT, fill=BOTH, expand=1)

        self.search_but = Button(frame1, text='Search', command=self.search_for_package)
        self.search_but.pack(side=RIGHT)

        # Search results area
        frame2 = ttk.Frame(self.tk_window)
        frame2.pack(expand=1, fill=BOTH, side=TOP)
        frame2.columnconfigure(0, weight=1)
        frame2.rowconfigure(0, weight=1)

        # Scrollbars
        self.tv_vscb = ttk.Scrollbar(frame2, orient=VERTICAL)
        self.tv_vscb.grid(row=0, column=1, sticky='nse')
        self.tv_hscb = ttk.Scrollbar(frame2, orient=HORIZONTAL)
        self.tv_hscb.grid(row=1, column=0, sticky='ewn')

        # Installed Packages Treeview
        self.tv_ip = ttk.Treeview(frame2, yscroll=self.tv_vscb.set, xscroll=self.tv_hscb.set)
        self.tv_ip['columns'] = ('package_name', 'version', 'description')
        self.tv_ip.bind('<<TreeviewSelect>>', self.selection_change)

        self.tv_ip.column('#0', width=0, stretch=NO)
        self.tv_ip.column('package_name', width=140, anchor=W, stretch=NO)
        self.tv_ip.column('version', width=100, anchor=W, stretch=NO)
        self.tv_ip.column('description', width=160, anchor=W, stretch=YES)

        self.tv_ip.heading('package_name', text='Package Name', anchor=W)
        self.tv_ip.heading('version', text='Version', anchor=W)
        self.tv_ip.heading('description', text='Description', anchor=W)
        self.tv_ip.grid(row=0, column=0, sticky='ewns')

        self.no_pkg_inst_label = ttk.Label(self.tv_ip, text="No results", background='#FFFFFF')
        self.no_pkg_inst_label.pack()
        self.no_pkg_inst_label.place(relx=0.5, rely=0.5)
        
        # Link scrollbars
        self.tv_vscb.configure(command=self.tv_ip.yview)
        self.tv_hscb.configure(command=self.tv_ip.xview)

        # Bottom Info panel
        separator = ttk.Separator(self.tk_window, orient='horizontal')
        separator.pack(side=TOP, fill=X)

        frame3 = ttk.Frame(self.tk_window)
        frame3.pack(fill=BOTH, side=BOTTOM)
        frame3.columnconfigure(0, weight=1)

        self.label_name = ttk.Label(frame3, text='Package Name')
        self.label_name.grid(sticky='nsw')
        self.label_description = ttk.Label(frame3, text='Package Description')
        self.label_description.grid(row=1, sticky='nsw')

        label3 = ttk.Label(frame3, text='Version')
        label3.grid(row=0, column=1, sticky='nsw')
        self.combo_version = ttk.Combobox(frame3, values=['Default'], state="readonly")
        self.combo_version.grid(column=1, row=1)
        self.combo_version.current(0)

        label4 = ttk.Label(frame3, text='Architecture')
        label4.grid(row=0, column=2, sticky='nsw')
        self.combo_architecture = ttk.Combobox(frame3, state="readonly")
        self.populate_architecture_combo()
        self.combo_architecture.grid(column=2, row=1)
        self.combo_architecture.current(0)

        self.but_install_pkg = ttk.Button(frame3, text="Install", state=DISABLED)
        self.but_install_pkg.grid(column=3, rowspan=2, row=0, sticky='ns')

    def populate_architecture_combo(self):
        archs_list = ['System Default']

        archs = self.vcpkg_obj.get_available_triplets()


        for arch in archs['builtin']:
            archs_list.append(arch)
        for arch in archs['community']:
            archs_list.append(arch)
        
        self.combo_architecture.config(values=archs_list)
        self.combo_architecture.update()

    def selection_change(self, event):
        selected_items = self.tv_ip.selection() # TODO: Is this returning the ID's or the index?
        if len(selected_items) == 0:
            self.but_install_pkg.config(state=DISABLED)
        else:
            self.but_install_pkg.config(state=ACTIVE)
        
        if len(selected_items) > 1:
            self.combo_version.config(state=DISABLED)
        else:
            self.combo_version.config(state="readonly")

    def search_for_package(self):
        if self.search_entry.get() == "Enter a package name to search for":
            return
        
        search_string = self.search_entry.get()

        # Update the GUI
        self.search_but.config(state=DISABLED)
        self.no_pkg_inst_label.config(text="Searching")
        self.no_pkg_inst_label.place(relx=0.5, rely=0.5)
        self.tk_window.update()

        search_results = self.vcpkg_obj.search_for_package(search_string)
        
        if len(search_results) == 0:
            self.no_pkg_inst_label.config(text="No results")
        else:
            self.no_pkg_inst_label.place_forget()
            self.no_pkg_inst_label.update()

        self.search_but.config(state=ACTIVE)
        self.search_but.update()

        self.populate_search_results(search_results)
    
    def populate_search_results(self, search_results):
        self.tv_ip.delete(*self.tv_ip.get_children())

        next_tv_id = 0

        for package_name, value in search_results.items():
            new_treeview_id = next_tv_id
            
            if 'version' in value:
                version = value['version']
            else:
                version = ''

            self.tv_ip.insert(parent='', index=tk.END, iid=new_treeview_id, text='', values=(package_name, version, value['description']))
            
            next_tv_id = next_tv_id + 1

    def close_windows(self):
        self.tk_window.withdraw()

    def close_install_pkg_window(self):
        self.tk_window.withdraw()

if __name__ == '__main__':
    vcpkg = VCPKGInterface()
    search_package_gui = OverviewWindow(vcpkg)
    search_package_gui.open_gui()
