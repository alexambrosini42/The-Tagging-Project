"""
Tag Editor Window - Single image detailed editing
Works with a subset of images from bulk editor
"""

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
from pathlib import Path

class TagEditor:
    """Detailed tag editor for selected images"""
    
    def __init__(self, parent, data_manager, image_list, bulk_editor):
        self.parent = parent
        self.data_manager = data_manager
        self.image_list = image_list  # Subset of images to edit
        self.bulk_editor = bulk_editor
        
        self.window = tk.Toplevel(parent)
        self.window.title(f"Tag Editor - {len(image_list)} images")
        
        # Make fullscreen
        try:
            self.window.state('zoomed')
        except:
            try:
                self.window.attributes('-zoomed', True)
            except:
                w = self.window.winfo_screenwidth()
                h = self.window.winfo_screenheight()
                self.window.geometry(f"{w}x{h}+0+0")
        
        # State
        self.current_index = 0
        self.zoom_level = 1.0
        self.fit_to_view = True
        self.original_image = None
        self.current_image_path = None
        self.dragged_tag = None
        self.drag_ghost = None
        self.drop_indicator = None
        
        self._setup_ui()
        self._setup_keyboard_shortcuts()
        
        # Load first image
        if self.image_list:
            self._load_image(0)
    
    def _setup_ui(self):
        """Build the tag editor UI"""
        main_container = tk.PanedWindow(self.window, orient=tk.HORIZONTAL, sashwidth=5)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # LEFT: Image viewer
        self._create_image_viewer(main_container)
        
        # MIDDLE: Tag editor
        self._create_tag_editor_panel(main_container)
        
        # RIGHT: Suggestions (from selected images only)
        self._create_suggestion_panel(main_container)
        
        # Bottom status
        self.status_bar = tk.Label(self.window, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W, bg='#e0e0e0')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _create_image_viewer(self, parent):
        """Create image viewer panel"""
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
        
        # Back button
        tk.Button(zoom_controls, text="← Back to Bulk Editor", command=self._close_editor,
                 bg='#FF5722', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.RIGHT, padx=10)
        
        # Canvas
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
        self.canvas_image_id = self.image_canvas.create_window(0, 0, anchor=tk.NW, window=self.image_label)
    
    def _create_tag_editor_panel(self, parent):
        """Create tag editor panel"""
        editor_frame = tk.Frame(parent, bg='white')
        parent.add(editor_frame, width=400)
        
        # Title
        title = tk.Label(editor_frame, text="Tag Editor", font=('Arial', 14, 'bold'), bg='white')
        title.pack(pady=10)
        
        # Navigation
        nav_frame = tk.Frame(editor_frame, bg='white')
        nav_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(nav_frame, text="← Previous", command=self._previous_image).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Next →", command=self._next_image).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="Save", command=self._save_current, bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=2)
        
        # File info
        self.file_label = tk.Label(editor_frame, text="No file loaded", bg='white', fg='#666')
        self.file_label.pack(pady=5)
        
        # Tag container (scrollable)
        tag_scroll_frame = tk.Frame(editor_frame, bg='white')
        tag_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tag_canvas = tk.Canvas(tag_scroll_frame, bg='white', highlightthickness=0)
        tag_scrollbar = tk.Scrollbar(tag_scroll_frame, orient=tk.VERTICAL, command=tag_canvas.yview)
        
        self.tag_container = tk.Frame(tag_canvas, bg='white')
        self.tag_container.bind('<Configure>', lambda e: tag_canvas.configure(scrollregion=tag_canvas.bbox('all')))
        
        self.tag_canvas_window = tag_canvas.create_window((0, 0), window=self.tag_container, anchor=tk.NW, width=380)
        tag_canvas.configure(yscrollcommand=tag_scrollbar.set)
        
        tag_canvas.bind('<Configure>', lambda e: tag_canvas.itemconfig(self.tag_canvas_window, width=e.width - 5))
        
        tag_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tag_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add new tag
        add_frame = tk.Frame(editor_frame, bg='white')
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(add_frame, text="Add new tag:", bg='white').pack(side=tk.LEFT)
        self.new_tag_entry = tk.Entry(add_frame, width=20)
        self.new_tag_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.new_tag_entry.bind('<Return>', lambda e: self._add_tag())
        
        tk.Button(add_frame, text="Add", command=self._add_tag, bg='#2196F3', fg='white').pack(side=tk.LEFT)
    
    def _create_suggestion_panel(self, parent):
        """Create suggestions panel (from selected images only)"""
        suggest_frame = tk.Frame(parent, bg='#f5f5f5')
        parent.add(suggest_frame, width=300)
        
        # Info label
        info = tk.Label(
            suggest_frame, 
            text=f"Suggestions from {len(self.image_list)} selected images",
            bg='#f5f5f5', font=('Arial', 9), wraplength=280
        )
        info.pack(pady=10, padx=10)
        
        # Filter
        search_frame = tk.Frame(suggest_frame, bg='#f5f5f5')
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(search_frame, text="Filter:", bg='#f5f5f5').pack(side=tk.LEFT)
        self.filter_entry = tk.Entry(search_frame, width=20)
        self.filter_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.filter_entry.bind('<KeyRelease>', self._on_filter_change)
        
        # Global frequency (from selected images)
        global_frame = tk.LabelFrame(suggest_frame, text='Tags in Selection', bg='white')
        global_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        global_scroll = tk.Scrollbar(global_frame)
        global_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.global_listbox = tk.Listbox(global_frame, yscrollcommand=global_scroll.set, font=('Arial', 10))
        self.global_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.global_listbox.bind('<Double-Button-1>', self._add_from_global)
        global_scroll.config(command=self.global_listbox.yview)
        
        tk.Button(suggest_frame, text="← Add Selected Tag", command=self._add_from_global_btn,
                bg='#2196F3', fg='white').pack(fill=tk.X, padx=10, pady=5)
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.window.bind('<Control-s>', lambda e: self._save_current())
        self.window.bind('<Right>', lambda e: self._next_image())
        self.window.bind('<Left>', lambda e: self._previous_image())
        self.window.bind('<Control-Right>', lambda e: self._save_and_next())
        self.window.bind('<plus>', lambda e: self._zoom_in())
        self.window.bind('<minus>', lambda e: self._zoom_out())
        self.window.bind('<Key-0>', lambda e: self._zoom_reset())
        self.window.bind('<Escape>', lambda e: self._close_editor())
    
    def _load_image(self, index):
        """Load image at index"""
        if index < 0 or index >= len(self.image_list):
            return
        
        self.current_index = index
        self.current_image_path = self.image_list[index]
        
        try:
            self.original_image = Image.open(self.current_image_path)
            self._display_image()
            self._load_tags()
            self._update_global_list()
            
            filename = os.path.basename(self.current_image_path)
            self.file_label.config(text=f"{filename} ({index + 1}/{len(self.image_list)})")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}", parent=self.window)
    
    def _display_image(self):
        """Display image with zoom"""
        if not self.original_image:
            return
        
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            self.window.after(100, self._display_image)
            return
        
        if self.fit_to_view:
            width_ratio = canvas_width / self.original_image.width
            height_ratio = canvas_height / self.original_image.height
            self.zoom_level = min(width_ratio, height_ratio) * 0.95
        
        width = int(self.original_image.width * self.zoom_level)
        height = int(self.original_image.height * self.zoom_level)
        
        display_img = self.original_image.resize((width, height), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(display_img)
        
        self.image_label.config(image=photo)
        self.image_label.image = photo
        
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
        
        # Position image to the right side of canvas
        x_pos = max(canvas_width, width)
        self.image_canvas.coords(self.canvas_image_id, x_pos, 0)
        
        # Center the image in canvas
        self.image_canvas.coords(self.canvas_image_id, 0, 0)
        self.image_canvas.configure(scrollregion=(0, 0, width, height))
    
    def _load_tags(self):
        """Load tags for current image"""
        for widget in self.tag_container.winfo_children():
            widget.destroy()
        
        if not self.current_image_path:
            return
        
        tags = self.data_manager.get_tags(self.current_image_path)
        
        if not tags:
            return
        
        container_width = 360
        current_row = tk.Frame(self.tag_container, bg='white')
        current_row.pack(anchor=tk.W, fill=tk.X, pady=2)
        
        current_width = 0
        
        for i, tag in enumerate(tags):
            estimated_width = len(tag) * 8 + 60
            
            if current_width + estimated_width > container_width and current_width > 0:
                current_row = tk.Frame(self.tag_container, bg='white')
                current_row.pack(anchor=tk.W, fill=tk.X, pady=2)
                current_width = 0
            
            pill = self._create_tag_pill_in_row(tag, i, current_row)
            current_width += estimated_width
    
    def _create_tag_pill_in_row(self, tag, index, parent_row):
        """Create tag pill"""
        pill_frame = tk.Frame(parent_row, bg='#E3F2FD', bd=0, relief=tk.FLAT)
        pill_frame.pack(side=tk.LEFT, padx=3, pady=3)
        
        inner = tk.Frame(pill_frame, bg='#E3F2FD')
        inner.pack(padx=8, pady=4)
        
        pill_frame.config(highlightbackground='#90CAF9', highlightthickness=1)
        pill_frame.tag_name = tag
        
        # Drag handle
        drag_label = tk.Label(inner, text="⋮⋮", bg='#E3F2FD', fg='#757575', 
                            font=('Arial', 8), cursor='fleur')
        drag_label.pack(side=tk.LEFT, padx=(0, 4))
        
        for widget in [pill_frame, inner, drag_label]:
            widget.bind('<Button-1>', lambda e, t=tag, f=pill_frame: self._start_drag(e, t, f))
            widget.bind('<B1-Motion>', lambda e: self._on_drag_motion(e))
            widget.bind('<ButtonRelease-1>', lambda e, f=pill_frame: self._end_drag(e, f))
        
        tag_label = tk.Label(inner, text=tag, bg='#E3F2FD', fg='#1565C0', font=('Arial', 10))
        tag_label.pack(side=tk.LEFT, padx=2)
        tag_label.bind('<Double-Button-1>', lambda e, t=tag, f=pill_frame: self._edit_tag(t, f))
        
        remove_btn = tk.Label(inner, text="✕", bg='#E3F2FD', fg='#D32F2F',
                            font=('Arial', 10, 'bold'), cursor='hand2')
        remove_btn.pack(side=tk.LEFT, padx=(4, 0))
        remove_btn.bind('<Button-1>', lambda e, t=tag: self._remove_tag(t))
        
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
    
    def _start_drag(self, event, tag, frame):
        """Start dragging"""
        self.dragged_tag = tag
        self.dragged_frame = frame
        
        self.drag_ghost = tk.Toplevel(self.window)
        self.drag_ghost.wm_overrideredirect(True)
        self.drag_ghost.wm_attributes('-alpha', 0.7)
        self.drag_ghost.wm_attributes('-topmost', True)
        
        ghost_label = tk.Label(self.drag_ghost, text=tag, bg='#FFF59D', fg='#1565C0',
                            font=('Arial', 10, 'bold'), padx=15, pady=6, relief=tk.RAISED, bd=2)
        ghost_label.pack()
        
        self.drag_ghost.geometry(f'+{event.x_root + 10}+{event.y_root + 10}')
        self.drop_indicator = tk.Frame(self.tag_container, bg='#4CAF50', height=3)
        
        frame.config(bg='#E0E0E0', highlightbackground='#BDBDBD')
        for child in frame.winfo_children():
            child.config(bg='#E0E0E0')
            for subchild in child.winfo_children():
                if isinstance(subchild, tk.Label):
                    subchild.config(bg='#E0E0E0')
    
    def _on_drag_motion(self, event):
        """Handle drag motion"""
        if not self.drag_ghost:
            return
        
        self.drag_ghost.geometry(f'+{event.x_root + 10}+{event.y_root + 10}')
        
        x, y = event.x_root, event.y_root
        target = self.window.winfo_containing(x, y)
        
        target_frame = None
        temp = target
        for _ in range(10):
            if temp and hasattr(temp, 'tag_name') and temp != self.dragged_frame:
                target_frame = temp
                break
            temp = temp.master if hasattr(temp, 'master') else None
        
        if target_frame and self.drop_indicator:
            self.drop_indicator.pack_forget()
            
            target_x = target_frame.winfo_rootx()
            target_width = target_frame.winfo_width()
            
            if event.x_root < target_x + target_width / 2:
                self.drop_indicator.place(in_=target_frame, relx=0, rely=0, relheight=1, width=3, x=-5)
            else:
                self.drop_indicator.place(in_=target_frame, relx=1, rely=0, relheight=1, width=3, x=2)
        else:
            if self.drop_indicator:
                self.drop_indicator.place_forget()
    
    def _end_drag(self, event, source_frame):
        """End drag"""
        if self.drag_ghost:
            self.drag_ghost.destroy()
            self.drag_ghost = None
        
        if self.drop_indicator:
            self.drop_indicator.place_forget()
        
        if not self.dragged_tag or not self.current_image_path:
            self._reset_drag_visual()
            return
        
        x, y = event.x_root, event.y_root
        target = self.window.winfo_containing(x, y)
        
        target_frame = None
        temp = target
        for _ in range(10):
            if temp and hasattr(temp, 'tag_name') and temp != source_frame:
                target_frame = temp
                break
            temp = temp.master if hasattr(temp, 'master') else None
        
        if target_frame:
            target_tag = target_frame.tag_name
            
            tags = self.data_manager.get_tags(self.current_image_path)
            if self.dragged_tag in tags and target_tag in tags:
                old_idx = tags.index(self.dragged_tag)
                new_idx = tags.index(target_tag)
                
                target_x = target_frame.winfo_rootx()
                target_width = target_frame.winfo_width()
                
                if event.x_root >= target_x + target_width / 2:
                    if new_idx > old_idx:
                        new_idx = new_idx
                    else:
                        new_idx = new_idx + 1
                
                tags.pop(old_idx)
                tags.insert(new_idx, self.dragged_tag)
                
                self.data_manager.save_tags(self.current_image_path, tags)
                self._load_tags()
        
        self._reset_drag_visual()
    
    def _reset_drag_visual(self):
        """Reset drag visuals"""
        if self.drag_ghost:
            self.drag_ghost.destroy()
            self.drag_ghost = None
        
        if self.drop_indicator:
            try:
                self.drop_indicator.place_forget()
            except tk.TclError:
                pass
        
        if hasattr(self, 'dragged_frame') and self.dragged_frame:
            try:
                self.dragged_frame.config(bg='#E3F2FD', highlightbackground='#90CAF9', highlightthickness=1)
                for child in self.dragged_frame.winfo_children():
                    child.config(bg='#E3F2FD')
                    for subchild in child.winfo_children():
                        if isinstance(subchild, tk.Label):
                            subchild.config(bg='#E3F2FD')
            except tk.TclError:
                pass
        
        self.dragged_tag = None
        self.dragged_frame = None
    
    def _edit_tag(self, old_tag, frame):
        """Edit tag in-place"""
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
            self._update_global_list()
        
        entry.bind('<Return>', save_edit)
        entry.bind('<Escape>', lambda e: self._load_tags())
        
        save_btn = tk.Label(inner, text="✓", bg='#FFF9C4', fg='#4CAF50',
                        font=('Arial', 12, 'bold'), cursor='hand2')
        save_btn.pack(side=tk.LEFT, padx=4)
        save_btn.bind('<Button-1>', lambda e: save_edit())
    
    def _add_tag(self):
        """Add new tag"""
        new_tag = self.new_tag_entry.get().strip()
        if not new_tag or not self.current_image_path:
            return
        
        tags = self.data_manager.get_tags(self.current_image_path)
        if new_tag not in tags:
            tags.append(new_tag)
            self.data_manager.save_tags(self.current_image_path, tags)
            self._load_tags()
            self._update_global_list()
        
        self.new_tag_entry.delete(0, tk.END)
    
    def _remove_tag(self, tag):
        """Remove tag"""
        if not self.current_image_path:
            return
        
        tags = self.data_manager.get_tags(self.current_image_path)
        if tag in tags:
            tags.remove(tag)
            self.data_manager.save_tags(self.current_image_path, tags)
            self._load_tags()
            self._update_global_list()
    
    def _update_global_list(self, filter_text=''):
        """Update global tag list from selected images only"""
        self.global_listbox.delete(0, tk.END)
        
        # Count tags only from the selected subset
        tag_counts = {}
        for img_path in self.image_list:
            tags = self.data_manager.get_tags(img_path)
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort by frequency
        sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
        
        for tag, count in sorted_tags:
            if not filter_text or filter_text.lower() in tag.lower():
                self.global_listbox.insert(tk.END, f"{tag} ({count})")
    
    def _add_from_global(self, event):
        """Add tag from global list"""
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
    
    def _add_from_global_btn(self):
        """Add from button click"""
        selection = self.global_listbox.curselection()
        if selection:
            self._add_from_global(None)
    
    def _on_filter_change(self, event):
        """Handle filter change"""
        filter_text = self.filter_entry.get()
        self._update_global_list(filter_text)
    
    def _zoom_in(self):
        """Zoom in"""
        self.fit_to_view = False
        self.zoom_level = min(self.zoom_level + 0.25, 5.0)
        self._display_image()
    
    def _zoom_out(self):
        """Zoom out"""
        self.fit_to_view = False
        self.zoom_level = max(self.zoom_level - 0.25, 0.25)
        self._display_image()
    
    def _zoom_reset(self):
        """Reset zoom"""
        self.fit_to_view = True
        self._display_image()
    
    def _next_image(self):
        """Next image"""
        if self.current_index < len(self.image_list) - 1:
            self._load_image(self.current_index + 1)
    
    def _previous_image(self):
        """Previous image"""
        if self.current_index > 0:
            self._load_image(self.current_index - 1)
    
    def _save_current(self):
        """Save current"""
        if self.current_image_path:
            tags = self.data_manager.get_tags(self.current_image_path)
            self.data_manager.save_tags(self.current_image_path, tags)
            self.status_bar.config(text="Saved successfully")
            self.window.after(3000, lambda: self.status_bar.config(text="Ready"))
    
    def _save_and_next(self):
        """Save and next"""
        self._save_current()
        self._next_image()
    
    def _close_editor(self):
        """Close and return to bulk editor"""
        # Notify bulk editor to refresh
        self.bulk_editor.refresh_from_editor()
        self.window.destroy()