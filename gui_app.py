import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
from data_manager import DataManager
from bulk_editor import BulkEditor
import os

class GUI_App:
    """Main GUI application for LoRA Dataset Tagger"""
    
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.data_manager = DataManager(config)
        
        self.current_index = 0
        self.filtered_files = []
        self.zoom_level = 1.0
        self.fit_to_view = True  # Start with fit-to-view mode
        self.original_image = None
        self.current_image_path = None
        self.dragged_tag = None  # For drag-and-drop
        self.drag_ghost = None  # Visual ghost of dragged item
        self.drop_indicator = None  # Visual indicator of drop position
        
        self._setup_ui()
        self._setup_keyboard_shortcuts()
        
    def _setup_ui(self):
        """Build the main UI layout"""
        # Main container with three panels
        main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=5)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # LEFT PANEL: Image Viewer
        self._create_image_viewer(main_container)
        
        # MIDDLE PANEL: Tag Editor
        self._create_tag_editor(main_container)
        
        # RIGHT PANEL: Suggestions
        self._create_suggestion_panel(main_container)
        
        # Bottom status bar
        self._create_status_bar()
        
        # Top menu bar
        self._create_menu_bar()
        
    def _create_image_viewer(self, parent):
        """Create the image viewer panel with zoom controls"""
        viewer_frame = tk.Frame(parent, bg='#2b2b2b')
        parent.add(viewer_frame, width=700)
        
        # Zoom controls
        zoom_controls = tk.Frame(viewer_frame, bg='#2b2b2b')
        zoom_controls.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        tk.Button(zoom_controls, text="Zoom In (+)", command=self._zoom_in).pack(side=tk.LEFT, padx=2)
        tk.Button(zoom_controls, text="Zoom Out (-)", command=self._zoom_out).pack(side=tk.LEFT, padx=2)
        tk.Button(zoom_controls, text="Fit to View (0)", command=self._zoom_reset).pack(side=tk.LEFT, padx=2)
        
        self.zoom_label = tk.Label(zoom_controls, text="100%", bg='#2b2b2b', fg='white')
        self.zoom_label.pack(side=tk.LEFT, padx=10)
        
        # Image canvas with scrollbars
        canvas_frame = tk.Frame(viewer_frame, bg='#2b2b2b')
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.image_canvas = tk.Canvas(canvas_frame, bg='#1e1e1e', highlightthickness=0)
        h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.image_canvas.xview)
        v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.image_canvas.yview)
        
        self.image_canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.image_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.image_label = tk.Label(self.image_canvas, bg='#1e1e1e')
        self.canvas_image_id = self.image_canvas.create_window(0, 0, anchor=tk.NE, window=self.image_label)
        
    def _create_tag_editor(self, parent):
        """Create the tag editor panel with pill-style tags"""
        editor_frame = tk.Frame(parent, bg='white')
        parent.add(editor_frame, width=400)
        
        # Title
        title = tk.Label(editor_frame, text="Tag Editor", font=('Arial', 14, 'bold'), bg='white')
        title.pack(pady=10)
        
        # Navigation controls
        nav_frame = tk.Frame(editor_frame, bg='white')
        nav_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(nav_frame, text="← Previous", command=self._previous_image).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Next →", command=self._next_image).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Save", command=self._save_current, bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=2)
        
        # File info
        self.file_label = tk.Label(editor_frame, text="No file loaded", bg='white', fg='#666')
        self.file_label.pack(pady=5)
        
        # Scrollable tag container with wrapping
        tag_scroll_frame = tk.Frame(editor_frame, bg='white')
        tag_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tag_canvas = tk.Canvas(tag_scroll_frame, bg='white', highlightthickness=0)
        tag_scrollbar = tk.Scrollbar(tag_scroll_frame, orient=tk.VERTICAL, command=tag_canvas.yview)

        self.tag_container = tk.Frame(tag_canvas, bg='white')
        self.tag_container.bind('<Configure>', lambda e: tag_canvas.configure(scrollregion=tag_canvas.bbox('all')))

        # Important: set a width for the container so tags know when to wrap
        self.tag_canvas_window = tag_canvas.create_window((0, 0), window=self.tag_container, anchor=tk.NW, width=380)
        tag_canvas.configure(yscrollcommand=tag_scrollbar.set)

        # Bind canvas resize to update container width
        tag_canvas.bind('<Configure>', lambda e: tag_canvas.itemconfig(self.tag_canvas_window, width=e.width - 5))

        tag_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tag_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add new tag input
        add_frame = tk.Frame(editor_frame, bg='white')
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(add_frame, text="Add new tag:", bg='white').pack(side=tk.LEFT)
        self.new_tag_entry = tk.Entry(add_frame, width=20)
        self.new_tag_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.new_tag_entry.bind('<Return>', lambda e: self._add_tag())
        
        tk.Button(add_frame, text="Add", command=self._add_tag, bg='#2196F3', fg='white').pack(side=tk.LEFT)
        
    def _create_suggestion_panel(self, parent):
        """Create the suggestion panel with global and local tags"""
        suggest_frame = tk.Frame(parent, bg='#f5f5f5')
        parent.add(suggest_frame, width=300)
        
        # Search/Filter
        search_frame = tk.Frame(suggest_frame, bg='#f5f5f5')
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(search_frame, text="Filter:", bg='#f5f5f5').pack(side=tk.LEFT)
        self.filter_entry = tk.Entry(search_frame, width=20)
        self.filter_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.filter_entry.bind('<KeyRelease>', self._on_filter_change)
        
        # Notebook for Global/Local tabs
        notebook = ttk.Notebook(suggest_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Global frequency tab
        global_frame = tk.Frame(notebook, bg='white')
        notebook.add(global_frame, text='Global Tags')
        
        # Frame for listbox and button
        global_list_frame = tk.Frame(global_frame, bg='white')
        global_list_frame.pack(fill=tk.BOTH, expand=True)
        
        global_scroll = tk.Scrollbar(global_list_frame)
        global_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.global_listbox = tk.Listbox(global_list_frame, yscrollcommand=global_scroll.set, font=('Arial', 10))
        self.global_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.global_listbox.bind('<Double-Button-1>', self._add_from_global)
        global_scroll.config(command=self.global_listbox.yview)
        
        # Add button for global
        tk.Button(global_frame, text="← Add Selected Tag", command=self._add_from_global_btn,
                bg='#2196F3', fg='white').pack(fill=tk.X, padx=5, pady=5)
        
        # Local suggestions tab
        local_frame = tk.Frame(notebook, bg='white')
        notebook.add(local_frame, text='Similar Tags')
        
        # Frame for listbox and button
        local_list_frame = tk.Frame(local_frame, bg='white')
        local_list_frame.pack(fill=tk.BOTH, expand=True)
        
        local_scroll = tk.Scrollbar(local_list_frame)
        local_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.local_listbox = tk.Listbox(local_list_frame, yscrollcommand=local_scroll.set, font=('Arial', 10))
        self.local_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.local_listbox.bind('<Double-Button-1>', self._add_from_local)
        local_scroll.config(command=self.local_listbox.yview)
        
        # Add button for local
        tk.Button(local_frame, text="← Add Selected Tag", command=self._add_from_local_btn,
                bg='#2196F3', fg='white').pack(fill=tk.X, padx=5, pady=5)
        
        # Global operations
        ops_frame = tk.LabelFrame(suggest_frame, text="Global Operations", bg='#f5f5f5', padx=10, pady=10)
        ops_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(ops_frame, text="Add Tag to All", command=self._add_tag_globally).pack(fill=tk.X, pady=2)
        tk.Button(ops_frame, text="Remove Tag from All", command=self._remove_tag_globally).pack(fill=tk.X, pady=2)
        tk.Button(ops_frame, text="Rename Tag Globally", command=self._rename_tag_globally).pack(fill=tk.X, pady=2)

    def _add_from_global_btn(self):
        """Add tag from global list (button click)"""
        selection = self.global_listbox.curselection()
        if selection:
            self._add_from_global(None)

    def _add_from_local_btn(self):
        """Add tag from local suggestions (button click)"""
        selection = self.local_listbox.curselection()
        if selection:
            self._add_from_local(None)
    def _create_status_bar(self):
        """Create bottom status bar"""
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W, bg='#e0e0e0')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def _create_menu_bar(self):
        """Create top menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Folder", command=self._open_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo (Ctrl+Z)", command=self._undo)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Bulk Editor", command=self._open_bulk_editor)

    def _open_bulk_editor(self):
        """Open the bulk editor window"""
        if not self.data_manager.image_files:
            messagebox.showwarning("No Data", "Please open a folder first")
            return
        
        BulkEditor(self.root, self.data_manager)       

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind('<Control-z>', lambda e: self._undo())
        self.root.bind('<Control-s>', lambda e: self._save_current())
        # self.root.bind('<Control-Right>', lambda e: self._next_image())
        self.root.bind('<Control-Left>', lambda e: self._previous_image())
        self.root.bind('<Control-Right>', lambda e: self._save_and_next())
        self.root.bind('<Control-plus>', lambda e: self._zoom_in())
        self.root.bind('<Control-minus>', lambda e: self._zoom_out())
        self.root.bind('<Key-0>', lambda e: self._zoom_reset())
        
    def _open_folder(self):
        """Open folder dialog and load dataset"""
        folder = filedialog.askdirectory(title="Select Dataset Folder")
        if folder:
            count = self.data_manager.load_data(folder)
            self.filtered_files = self.data_manager.image_files.copy()
            
            if count > 0:
                self.current_index = 0
                self._load_image(0)
                self._update_global_list()
                self._update_status(f"Loaded {count} images")
            else:
                messagebox.showwarning("No Images", "No supported images found in the selected folder.")
                
    def _load_image(self, index):
        """Load and display image at given index"""
        if not self.filtered_files or index < 0 or index >= len(self.filtered_files):
            return
        
        self.current_index = index
        self.current_image_path = self.filtered_files[index]
        
        # Load image
        try:
            self.original_image = Image.open(self.current_image_path)
            self._display_image()
            self._load_tags()
            self._update_local_suggestions()
            
            filename = os.path.basename(self.current_image_path)
            self.file_label.config(text=f"{filename} ({index + 1}/{len(self.filtered_files)})")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
    
    def _display_image(self):
        """Display image with current zoom level or fit-to-view"""
        if not self.original_image:
            return
        
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        
        # Wait for canvas to be properly sized
        if canvas_width <= 1 or canvas_height <= 1:
            self.root.after(100, self._display_image)
            return
        
        if self.fit_to_view:
            # Calculate zoom to fit image in canvas
            width_ratio = canvas_width / self.original_image.width
            height_ratio = canvas_height / self.original_image.height
            self.zoom_level = min(width_ratio, height_ratio) * 0.95  # 95% to leave some margin
        
        # Calculate display size
        width = int(self.original_image.width * self.zoom_level)
        height = int(self.original_image.height * self.zoom_level)
        
        # Resize image
        display_img = self.original_image.resize((width, height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(display_img)
        
        self.image_label.config(image=photo)
        self.image_label.image = photo
        
        # Update zoom label
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        
        # Position image to the right side of canvas
        x_pos = max(canvas_width, width)
        self.image_canvas.coords(self.canvas_image_id, x_pos, 0)
        
        # Update scroll region
        self.image_canvas.configure(scrollregion=(0, 0, max(canvas_width, width), max(canvas_height, height)))
        
    def _load_tags(self):
        """Load and display tags for current image with wrapping layout"""
        # Clear current tags
        for widget in self.tag_container.winfo_children():
            widget.destroy()
        
        if not self.current_image_path:
            return
        
        tags = self.data_manager.get_tags(self.current_image_path)
        
        if not tags:
            return
        
        # Create rows dynamically based on available width
        container_width = 360  # Approximate width, adjust if needed
        current_row = tk.Frame(self.tag_container, bg='white')
        current_row.pack(anchor=tk.W, fill=tk.X, pady=2)
        
        current_width = 0
        
        for i, tag in enumerate(tags):
            # Estimate pill width (rough approximation)
            estimated_width = len(tag) * 8 + 60  # char width + padding + buttons
            
            # Check if we need a new row
            if current_width + estimated_width > container_width and current_width > 0:
                # Start new row
                current_row = tk.Frame(self.tag_container, bg='white')
                current_row.pack(anchor=tk.W, fill=tk.X, pady=2)
                current_width = 0
            
            # Create pill in current row
            pill = self._create_tag_pill_in_row(tag, i, current_row)
            current_width += estimated_width

    def _create_tag_pill_in_row(self, tag, index, parent_row):
        """Create a pill-style tag widget in a specific row"""
        pill_frame = tk.Frame(parent_row, bg='#E3F2FD', bd=0, relief=tk.FLAT)
        pill_frame.pack(side=tk.LEFT, padx=3, pady=3)
        
        # Inner frame for padding
        inner = tk.Frame(pill_frame, bg='#E3F2FD')
        inner.pack(padx=8, pady=4)
        
        # Make pill rounded appearance
        pill_frame.config(highlightbackground='#90CAF9', highlightthickness=1)
        
        # Store tag reference on frame for drag-drop
        pill_frame.tag_name = tag
        
        # Drag handle
        drag_label = tk.Label(inner, text="⋮⋮", bg='#E3F2FD', fg='#757575', 
                            font=('Arial', 8), cursor='fleur')
        drag_label.pack(side=tk.LEFT, padx=(0, 4))
        
        # Bind drag to entire pill
        for widget in [pill_frame, inner, drag_label]:
            widget.bind('<Button-1>', lambda e, t=tag, f=pill_frame: self._start_drag(e, t, f))
            widget.bind('<B1-Motion>', lambda e: self._on_drag_motion(e))
            widget.bind('<ButtonRelease-1>', lambda e, f=pill_frame: self._end_drag(e, f))
        
        # Tag text (double-click to edit)
        tag_label = tk.Label(inner, text=tag, bg='#E3F2FD', fg='#1565C0',
                        font=('Arial', 10))
        tag_label.pack(side=tk.LEFT, padx=2)
        tag_label.bind('<Double-Button-1>', lambda e, t=tag, f=pill_frame: self._edit_tag(t, f))
        
        # Remove button
        remove_btn = tk.Label(inner, text="✕", bg='#E3F2FD', fg='#D32F2F',
                            font=('Arial', 10, 'bold'), cursor='hand2')
        remove_btn.pack(side=tk.LEFT, padx=(4, 0))
        remove_btn.bind('<Button-1>', lambda e, t=tag: [self._remove_tag(t), e.widget.master.master.master.focus_set()])
        
        # Hover effects
        def on_enter(e):
            pill_frame.config(bg='#BBDEFB', highlightbackground='#64B5F6')
            inner.config(bg='#BBDEFB')
            drag_label.config(bg='#BBDEFB')
            tag_label.config(bg='#BBDEFB')
            remove_btn.config(bg='#BBDEFB')
        
        def on_leave(e):
            if not hasattr(self, 'dragged_frame') or self.dragged_frame != pill_frame:
                pill_frame.config(bg='#E3F2FD', highlightbackground='#90CAF9')
                inner.config(bg='#E3F2FD')
                drag_label.config(bg='#E3F2FD')
                tag_label.config(bg='#E3F2FD')
                remove_btn.config(bg='#E3F2FD')
        
        pill_frame.bind('<Enter>', on_enter)
        pill_frame.bind('<Leave>', on_leave)
        
        return pill_frame
    
    def _create_tag_pill(self, tag, index):
        """Create a pill-style tag widget with improved design and drag-and-drop"""
        pill_frame = tk.Frame(self.tag_container, bg='#E3F2FD', bd=0, relief=tk.FLAT)
        pill_frame.pack(side=tk.LEFT, padx=3, pady=3)
        
        # Inner frame for padding
        inner = tk.Frame(pill_frame, bg='#E3F2FD')
        inner.pack(padx=8, pady=4)
        
        # Make pill rounded appearance
        pill_frame.config(highlightbackground='#90CAF9', highlightthickness=1)
        
        # Store tag reference on frame for drag-drop
        pill_frame.tag_name = tag
        
        # Drag handle
        drag_label = tk.Label(inner, text="⋮⋮", bg='#E3F2FD', fg='#757575', 
                            font=('Arial', 8), cursor='fleur')
        drag_label.pack(side=tk.LEFT, padx=(0, 4))
        
        # Bind drag to entire pill
        for widget in [pill_frame, inner, drag_label]:
            widget.bind('<Button-1>', lambda e, t=tag, f=pill_frame: self._start_drag(e, t, f))
            widget.bind('<B1-Motion>', lambda e: self._on_drag_motion(e))
            widget.bind('<ButtonRelease-1>', lambda e, f=pill_frame: self._end_drag(e, f))
        
        # Tag text (double-click to edit)
        tag_label = tk.Label(inner, text=tag, bg='#E3F2FD', fg='#1565C0',
                        font=('Arial', 10))
        tag_label.pack(side=tk.LEFT, padx=2)
        tag_label.bind('<Double-Button-1>', lambda e, t=tag, f=pill_frame: self._edit_tag(t, f))
        
        # Remove button
        remove_btn = tk.Label(inner, text="✕", bg='#E3F2FD', fg='#D32F2F',
                            font=('Arial', 10, 'bold'), cursor='hand2')
        remove_btn.pack(side=tk.LEFT, padx=(4, 0))
        remove_btn.bind('<Button-1>', lambda e, t=tag: [self._remove_tag(t), e.widget.master.master.master.focus_set()])
        
        # Hover effects
        def on_enter(e):
            pill_frame.config(bg='#BBDEFB', highlightbackground='#64B5F6')
            inner.config(bg='#BBDEFB')
            drag_label.config(bg='#BBDEFB')
            tag_label.config(bg='#BBDEFB')
            remove_btn.config(bg='#BBDEFB')
        
        def on_leave(e):
            if not hasattr(self, 'dragged_frame') or self.dragged_frame != pill_frame:
                pill_frame.config(bg='#E3F2FD', highlightbackground='#90CAF9')
                inner.config(bg='#E3F2FD')
                drag_label.config(bg='#E3F2FD')
                tag_label.config(bg='#E3F2FD')
                remove_btn.config(bg='#E3F2FD')
        
        pill_frame.bind('<Enter>', on_enter)
        pill_frame.bind('<Leave>', on_leave)
    
    def _start_drag(self, event, tag, frame):
        """Start dragging a tag with ghost preview"""
        self.dragged_tag = tag
        self.dragged_frame = frame
        self.drag_start_widget = event.widget
        
        # Create ghost label (floating copy of the tag)
        self.drag_ghost = tk.Toplevel(self.root)
        self.drag_ghost.wm_overrideredirect(True)
        self.drag_ghost.wm_attributes('-alpha', 0.7)
        self.drag_ghost.wm_attributes('-topmost', True)
        
        ghost_label = tk.Label(self.drag_ghost, text=tag, bg='#FFF59D', fg='#1565C0',
                            font=('Arial', 10, 'bold'), padx=15, pady=6,
                            relief=tk.RAISED, bd=2)
        ghost_label.pack()
        
        # Position ghost at cursor
        self.drag_ghost.geometry(f'+{event.x_root + 10}+{event.y_root + 10}')
        
        # Create drop indicator (a line showing where tag will drop)
        self.drop_indicator = tk.Frame(self.tag_container, bg='#4CAF50', height=3)
        
        # Dim the original frame
        frame.config(bg='#E0E0E0', highlightbackground='#BDBDBD')
        for child in frame.winfo_children():
            child.config(bg='#E0E0E0')
            for subchild in child.winfo_children():
                if isinstance(subchild, tk.Label):
                    subchild.config(bg='#E0E0E0')

    def _on_drag_motion(self, event):
        """Update ghost position and show drop indicator"""
        if not self.drag_ghost:
            return
        
        # Move ghost with cursor
        self.drag_ghost.geometry(f'+{event.x_root + 10}+{event.y_root + 10}')
        
        # Find target frame under cursor
        x, y = event.x_root, event.y_root
        target = self.root.winfo_containing(x, y)
        
        # Find frame with tag_name
        target_frame = None
        temp = target
        for _ in range(10):
            if temp and hasattr(temp, 'tag_name') and temp != self.dragged_frame:
                target_frame = temp
                break
            temp = temp.master if hasattr(temp, 'master') else None
        
        # Show drop indicator
        if target_frame and self.drop_indicator:
            # Position indicator before or after target
            self.drop_indicator.pack_forget()
            
            # Determine if we're on left or right half of target
            target_x = target_frame.winfo_rootx()
            target_width = target_frame.winfo_width()
            
            if event.x_root < target_x + target_width / 2:
                # Drop before target
                self.drop_indicator.place(in_=target_frame, relx=0, rely=0, relheight=1, width=3, x=-5)
            else:
                # Drop after target
                self.drop_indicator.place(in_=target_frame, relx=1, rely=0, relheight=1, width=3, x=2)
        else:
            if self.drop_indicator:
                self.drop_indicator.place_forget()

    def _end_drag(self, event, source_frame):
        """End dragging and reorder if needed"""
        # Destroy ghost
        if self.drag_ghost:
            self.drag_ghost.destroy()
            self.drag_ghost = None
        
        # Hide drop indicator
        if self.drop_indicator:
            self.drop_indicator.place_forget()
        
        if not self.dragged_tag or not self.current_image_path:
            self._reset_drag_visual()
            return
        
        # Find target widget
        x, y = event.x_root, event.y_root
        target = self.root.winfo_containing(x, y)
        
        # Walk up to find a frame with tag_name attribute
        target_frame = None
        temp = target
        for _ in range(10):
            if temp and hasattr(temp, 'tag_name') and temp != source_frame:
                target_frame = temp
                break
            temp = temp.master if hasattr(temp, 'master') else None
        
        if target_frame:
            target_tag = target_frame.tag_name
            
            # Reorder
            tags = self.data_manager.get_tags(self.current_image_path)
            if self.dragged_tag in tags and target_tag in tags:
                old_idx = tags.index(self.dragged_tag)
                new_idx = tags.index(target_tag)
                
                # Determine if dropping before or after
                target_x = target_frame.winfo_rootx()
                target_width = target_frame.winfo_width()
                
                if event.x_root >= target_x + target_width / 2:
                    # Drop after target
                    if new_idx > old_idx:
                        new_idx = new_idx
                    else:
                        new_idx = new_idx + 1
                
                # Remove from old position and insert at new
                tags.pop(old_idx)
                tags.insert(new_idx, self.dragged_tag)
                
                self.data_manager.save_tags(self.current_image_path, tags)
                self._load_tags()
                self._update_local_suggestions()
        
        self._reset_drag_visual()

    def _reset_drag_visual(self):
        """Reset drag visual feedback"""
        if self.drag_ghost:
            self.drag_ghost.destroy()
            self.drag_ghost = None
        
        if self.drop_indicator:
            try:
                self.drop_indicator.place_forget()
            except tk.TclError:
                pass  # Widget already destroyed
        
        if hasattr(self, 'dragged_frame') and self.dragged_frame:
            try:
                self.dragged_frame.config(bg='#E3F2FD', highlightbackground='#90CAF9', highlightthickness=1)
                for child in self.dragged_frame.winfo_children():
                    child.config(bg='#E3F2FD')
                    for subchild in child.winfo_children():
                        if isinstance(subchild, tk.Label):
                            subchild.config(bg='#E3F2FD')
            except tk.TclError:
                pass  # Widget already destroyed
        
        self.dragged_tag = None
        self.dragged_frame = None
    
    def _edit_tag(self, old_tag, frame):
        """Enable in-place editing of a tag"""
        # Clear inner frame
        for child in frame.winfo_children():
            child.destroy()
        
        frame.config(bg='#FFF9C4', highlightbackground='#FBC02D')
        
        inner = tk.Frame(frame, bg='#FFF9C4')
        inner.pack(padx=8, pady=4)
        
        entry = tk.Entry(inner, font=('Arial', 10), bg='#FFF9C4', relief=tk.FLAT, width=15)
        entry.insert(0, old_tag)
        entry.pack(side=tk.LEFT, padx=2)
        entry.focus()
        entry.select_range(0, tk.END)
        
        def save_edit(event=None):
            new_tag = entry.get().strip()
            if new_tag and new_tag != old_tag:
                tags = self.data_manager.get_tags(self.current_image_path)
                if old_tag in tags:
                    idx = tags.index(old_tag)
                    tags[idx] = new_tag
                    self.data_manager.save_tags(self.current_image_path, tags)
            self._load_tags()
            self._update_local_suggestions()
        
        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', lambda e: self._load_tags())
        
        save_btn = tk.Label(inner, text="✓", bg='#FFF9C4', fg='#4CAF50',
                        font=('Arial', 12, 'bold'), cursor='hand2')
        save_btn.pack(side=tk.LEFT, padx=4)
        save_btn.bind('<Button-1>', lambda e: save_edit())
    
    def _add_tag(self):
        """Add a new tag from the input field"""
        new_tag = self.new_tag_entry.get().strip()
        if not new_tag or not self.current_image_path:
            return
        
        tags = self.data_manager.get_tags(self.current_image_path)
        if new_tag not in tags:
            tags.append(new_tag)
            self.data_manager.save_tags(self.current_image_path, tags)
            self._load_tags()
            self._update_local_suggestions()
            self._update_global_list()
        
        self.new_tag_entry.delete(0, tk.END)
    
    def _remove_tag(self, tag):
        """Remove a tag from current image"""
        if not self.current_image_path:
            return
        
        tags = self.data_manager.get_tags(self.current_image_path)
        if tag in tags:
            tags.remove(tag)
            self.data_manager.save_tags(self.current_image_path, tags)
            self._load_tags()
            self._update_local_suggestions()
            self._update_global_list()
    
    def _move_tag(self, tag, direction):
        """Move tag up or down in the list (legacy - drag and drop preferred)"""
        if not self.current_image_path:
            return
        
        tags = self.data_manager.get_tags(self.current_image_path)
        if tag not in tags:
            return
            
        idx = tags.index(tag)
        new_idx = idx + direction
        
        if 0 <= new_idx < len(tags):
            tags[idx], tags[new_idx] = tags[new_idx], tags[idx]
            self.data_manager.save_tags(self.current_image_path, tags)
            self._load_tags()
    
    def _update_global_list(self, filter_text=''):
        """Update the global tag frequency list"""
        self.global_listbox.delete(0, tk.END)
        
        tags_by_freq = self.data_manager.get_all_tags_by_frequency()
        
        for tag, count in tags_by_freq:
            if not filter_text or filter_text.lower() in tag.lower():
                self.global_listbox.insert(tk.END, f"{tag} ({count})")
    
    def _update_local_suggestions(self):
        """Update the local similarity suggestions"""
        self.local_listbox.delete(0, tk.END)
        
        if not self.current_image_path:
            return
        
        current_tags = self.data_manager.get_tags(self.current_image_path)
        suggestions = self.data_manager.get_local_suggestions(current_tags)
        
        for tag, count in suggestions:
            self.local_listbox.insert(tk.END, f"{tag} ({count})")
    
    def _add_from_global(self, event):
        """Add tag from global list (double-click)"""
        selection = self.global_listbox.curselection()
        if not selection or not self.current_image_path:
            return
        
        item = self.global_listbox.get(selection[0])
        tag = item.split(' (')[0]
        
        tags = self.data_manager.get_tags(self.current_image_path)
        if tag not in tags:
            tags.append(tag)
            self.data_manager.save_tags(self.current_image_path, tags)
            self._load_tags()
            self._update_local_suggestions()
    
    def _add_from_local(self, event):
        """Add tag from local suggestions (double-click)"""
        selection = self.local_listbox.curselection()
        if not selection or not self.current_image_path:
            return
        
        item = self.local_listbox.get(selection[0])
        tag = item.split(' (')[0]
        
        tags = self.data_manager.get_tags(self.current_image_path)
        if tag not in tags:
            tags.append(tag)
            self.data_manager.save_tags(self.current_image_path, tags)
            self._load_tags()
            self._update_local_suggestions()
    
    def _on_filter_change(self, event):
        """Handle filter text change"""
        filter_text = self.filter_entry.get()
        self._update_global_list(filter_text)
        
        # Also filter images if there's text
        if filter_text:
            self.filtered_files = self.data_manager.filter_images_by_tag(filter_text)
            if self.filtered_files and self.current_image_path not in self.filtered_files:
                self._load_image(0)
        else:
            self.filtered_files = self.data_manager.image_files.copy()
    
    def _zoom_in(self):
        """Zoom in the image"""
        self.fit_to_view = False
        self.zoom_level = min(self.zoom_level + 0.25, 5.0)
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        self._display_image()
    
    def _zoom_out(self):
        """Zoom out the image"""
        self.fit_to_view = False
        self.zoom_level = max(self.zoom_level - 0.25, 0.25)
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        self._display_image()
    
    def _zoom_reset(self):
        """Reset zoom to fit-to-view mode"""
        self.fit_to_view = True
        self._display_image()
    
    def _next_image(self):
        """Navigate to next image"""
        if self.current_index < len(self.filtered_files) - 1:
            self._load_image(self.current_index + 1)
    
    def _previous_image(self):
        """Navigate to previous image"""
        if self.current_index > 0:
            self._load_image(self.current_index - 1)
    
    def _save_current(self):
        """Save current tags"""
        if self.current_image_path:
            tags = self.data_manager.get_tags(self.current_image_path)
            self.data_manager.save_tags(self.current_image_path, tags)
            self._update_status("Saved successfully")
    
    def _save_and_next(self):
        """Save current and move to next image"""
        self._save_current()
        self._next_image()
    
    def _undo(self):
        """Undo last operation"""
        filename = self.data_manager.undo()
        if filename:
            if filename == self.current_image_path:
                self._load_tags()
                self._update_local_suggestions()
            self._update_global_list()
            self._update_status("Undo successful")
        else:
            self._update_status("Nothing to undo")
    
    def _add_tag_globally(self):
        """Add a tag to all images"""
        tag = tk.simpledialog.askstring("Add Tag Globally", "Enter tag to add to all images:")
        if tag and tag.strip():
            count = self.data_manager.add_tag_globally(tag.strip())
            self._load_tags()
            self._update_global_list()
            self._update_local_suggestions()
            messagebox.showinfo("Success", f"Added '{tag}' to {count} images")
    
    def _remove_tag_globally(self):
        """Remove a tag from all images"""
        tag = tk.simpledialog.askstring("Remove Tag Globally", "Enter tag to remove from all images:")
        if tag and tag.strip():
            count = self.data_manager.remove_tag_globally(tag.strip())
            self._load_tags()
            self._update_global_list()
            self._update_local_suggestions()
            messagebox.showinfo("Success", f"Removed '{tag}' from {count} images")
    
    def _rename_tag_globally(self):
        """Rename a tag globally across all images"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Tag Globally")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Old tag (case-sensitive):").pack(pady=5)
        old_entry = tk.Entry(dialog, width=40)
        old_entry.pack(pady=5)
        
        tk.Label(dialog, text="New tag:").pack(pady=5)
        new_entry = tk.Entry(dialog, width=40)
        new_entry.pack(pady=5)
        
        def confirm():
            old_tag = old_entry.get().strip()
            new_tag = new_entry.get().strip()
            
            if not old_tag or not new_tag:
                messagebox.showwarning("Invalid Input", "Both fields are required")
                return
            
            if old_tag == new_tag:
                messagebox.showwarning("Invalid Input", "Tags are identical")
                return
            
            # Confirmation dialog
            if messagebox.askyesno("Confirm Rename", 
                                   f"Replace all instances of:\n'{old_tag}'\nwith:\n'{new_tag}'?\n\n"
                                   f"This is case-sensitive and cannot be undone through undo history."):
                count = self.data_manager.rename_tag_globally(old_tag, new_tag)
                self._load_tags()
                self._update_global_list()
                self._update_local_suggestions()
                messagebox.showinfo("Success", f"Renamed '{old_tag}' to '{new_tag}' in {count} images")
                dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Rename", command=confirm, bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _update_status(self, message):
        """Update status bar message"""
        self.status_bar.config(text=message)
        self.root.after(3000, lambda: self.status_bar.config(text="Ready"))