"""
LoRA Dataset Tagger - Bulk Editor Window
Multi-selection grid view for batch tag operations
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
from pathlib import Path
import math

class BulkEditor:
    """Bulk image selection and tag editing window"""
    
    def __init__(self, parent, data_manager):
        self.parent = parent
        self.data_manager = data_manager
        self.window = tk.Toplevel(parent)
        self.window.title("Bulk Tag Editor")
        
        # Make fullscreen
        try:
            self.window.state('zoomed')  # Windows
        except:
            try:
                self.window.attributes('-zoomed', True)  # Linux
            except:
                # Mac or fallback
                w = self.window.winfo_screenwidth()
                h = self.window.winfo_screenheight()
                self.window.geometry(f"{w}x{h}+0+0")
        
        # State
        self.selected_images = set()  # Set of image paths
        self.thumbnail_size = 200  # Default medium size
        self.thumbnails = {}  # Cache for PhotoImage objects
        self.image_frames = {}  # Track frame widgets for selection styling
        self.highlighted_tag = None  # Currently highlighted tag
        
        self._setup_ui()
        self._load_all_images()
        
    def _setup_ui(self):
        """Build the bulk editor UI"""
        # Top toolbar
        toolbar = tk.Frame(self.window, bg='#f0f0f0', height=60)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)
        
        # Thumbnail size slider
        tk.Label(toolbar, text="Thumbnail Size:", bg='#f0f0f0', font=('Arial', 10)).pack(side=tk.LEFT, padx=10)
        
        self.size_slider = tk.Scale(
            toolbar, from_=100, to=400, orient=tk.HORIZONTAL,
            command=self._on_size_change, bg='#f0f0f0',
            length=200, showvalue=False
        )
        self.size_slider.set(self.thumbnail_size)
        self.size_slider.pack(side=tk.LEFT, padx=5)
        
        self.size_label = tk.Label(toolbar, text=f"{self.thumbnail_size}px", bg='#f0f0f0', font=('Arial', 10), width=8)
        self.size_label.pack(side=tk.LEFT, padx=5)

        self.bg_color = '#fafafa'  # Start with light
        tk.Button(
            toolbar, text="Toggle BG", 
            command=self._toggle_background,
            font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=10)

        # Send to Tag Editor button
        tk.Button(
            toolbar, text="Edit Selected Images →", 
            command=self._open_tag_editor,
            bg='#9C27B0', fg='white', font=('Arial', 10, 'bold')
        ).pack(side=tk.LEFT, padx=20)

        tk.Button(
            toolbar, text="Category Organizer", 
            command=self._open_category_organizer,
            bg='#673AB7', fg='white', font=('Arial', 10, 'bold')
        ).pack(side=tk.LEFT, padx=10)

        # Selection info
        self.selection_label = tk.Label(
            toolbar, text="0 images selected", 
            bg='#f0f0f0', font=('Arial', 10, 'bold'), fg='#2196F3'
        )
        self.selection_label.pack(side=tk.LEFT, padx=20)
        
        # Clear selection button
        tk.Button(
            toolbar, text="Clear Selection", 
            command=self._clear_selection,
            bg='#FF9800', fg='white', font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=5)
        
        # Select All button
        tk.Button(
            toolbar, text="Select All", 
            command=self._select_all,
            bg='#4CAF50', fg='white', font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=5)
        
        # Close button
        tk.Button(
            toolbar, text="Close", 
            command=self.window.destroy,
            bg='#666', fg='white', font=('Arial', 10)
        ).pack(side=tk.RIGHT, padx=10)
        
        # Main container: Grid + Tag Panel
        main_container = tk.PanedWindow(self.window, orient=tk.HORIZONTAL, sashwidth=5)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # LEFT: Scrollable image grid
        self._create_image_grid(main_container)
        
        # RIGHT: Tag operations panel
        self._create_tag_panel(main_container)
        
    def _open_category_organizer(self):
        if not self.selected_images:
            messagebox.showwarning("No Selection", "Please select images first", parent=self.window)
            return
        
        from category_organizer import CategoryOrganizer
        CategoryOrganizer(self.window, self.data_manager, list(self.selected_images), self)

    def _create_image_grid(self, parent):
        """Create scrollable grid of images"""
        grid_frame = tk.Frame(parent, bg='white')
        parent.add(grid_frame, width=900)
        
        # Scrollable canvas
        canvas = tk.Canvas(grid_frame, bg='#fafafa', highlightthickness=0)
        v_scroll = tk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=canvas.yview)
        h_scroll = tk.Scrollbar(grid_frame, orient=tk.HORIZONTAL, command=canvas.xview)
        
        self.grid_container = tk.Frame(canvas, bg='#fafafa')
        
        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.grid_canvas_window = canvas.create_window((0, 0), window=self.grid_container, anchor=tk.NW)
        
        # Update scroll region when container changes
        self.grid_container.bind('<Configure>', 
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        
        # Update container width on canvas resize
        canvas.bind('<Configure>', self._on_canvas_configure)
        
        self.grid_canvas = canvas

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Windows
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux scroll up
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))  # Linux scroll down
        
    def _create_tag_panel(self, parent):
        """Create tag operations panel"""
        panel = tk.Frame(parent, bg='white')
        parent.add(panel, width=400)
        
        # Title
        tk.Label(
            panel, text="Selected Images Tags", 
            font=('Arial', 14, 'bold'), bg='white'
        ).pack(pady=10)
        
        # Tag list with scrollbar
        list_frame = tk.Frame(panel, bg='white')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scroll = tk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tag_listbox = tk.Listbox(
            list_frame, yscrollcommand=scroll.set, 
            font=('Arial', 11), selectmode=tk.EXTENDED
        )
        self.tag_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.tag_listbox.yview)
        
        # Bind tag click for highlighting
        self.tag_listbox.bind('<<ListboxSelect>>', self._on_tag_click)
        
        # Tag filter section (below the listbox)
        filter_frame = tk.Frame(panel, bg='white')
        filter_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(filter_frame, text="Filter tags in list:", bg='white', font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        tag_filter_input_frame = tk.Frame(filter_frame, bg='white')
        tag_filter_input_frame.pack(fill=tk.X, pady=2)
        
        self.tag_filter_entry = tk.Entry(tag_filter_input_frame, width=25)
        self.tag_filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.tag_filter_entry.bind('<KeyRelease>', lambda e: self._update_tag_list())
        
        tk.Button(
            tag_filter_input_frame, text="Clear",
            command=lambda: [self.tag_filter_entry.delete(0, tk.END), self._update_tag_list()],
            bg='#666', fg='white', font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=5)
        
        # Separator
        tk.Frame(filter_frame, bg='#e0e0e0', height=1).pack(fill=tk.X, pady=10)
        
        # Image filter section (NEW - separate from tag filter)
        tk.Label(filter_frame, text="Filter images by tag:", bg='white', font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5, 5))
        
        image_filter_input_frame = tk.Frame(filter_frame, bg='white')
        image_filter_input_frame.pack(fill=tk.X, pady=2)
        
        self.image_filter_entry = tk.Entry(image_filter_input_frame, width=25)
        self.image_filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.image_filter_entry.bind('<KeyRelease>', lambda e: self._on_image_filter_change())
        
        tk.Button(
            image_filter_input_frame, text="Clear",
            command=lambda: [self.image_filter_entry.delete(0, tk.END), self._on_image_filter_clear()],
            bg='#666', fg='white', font=('Arial', 9)
        ).pack(side=tk.LEFT, padx=5)
        
        # Operations frame
        ops_frame = tk.LabelFrame(panel, text="Bulk Operations", bg='white', font=('Arial', 11, 'bold'))
        ops_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Add tag
        add_frame = tk.Frame(ops_frame, bg='white')
        add_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(add_frame, text="Add tag:", bg='white').pack(side=tk.LEFT)
        self.add_tag_entry = tk.Entry(add_frame, width=20)
        self.add_tag_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.add_tag_entry.bind('<Return>', lambda e: self._bulk_add_tag())
        
        tk.Button(
            add_frame, text="Add to Selected", 
            command=self._bulk_add_tag,
            bg='#4CAF50', fg='white'
        ).pack(side=tk.LEFT, padx=5)
        
        # Remove tag
        tk.Button(
            ops_frame, text="Remove Selected Tags from Images", 
            command=self._bulk_remove_tag,
            bg='#F44336', fg='white'
        ).pack(fill=tk.X, padx=10, pady=5)
        
        # Rename tag
        tk.Button(
            ops_frame, text="Rename Selected Tag in Images", 
            command=self._bulk_rename_tag,
            bg='#FF9800', fg='white'
        ).pack(fill=tk.X, padx=10, pady=5)
        
        # Info text
        info = tk.Label(
            panel, 
            text="Tags show count: 'tag (5/10)' means\n5 out of 10 selected images have this tag\n\nClick a tag to highlight images with it",
            bg='white', fg='#666', font=('Arial', 9), justify=tk.LEFT
        )
        info.pack(pady=10)

    def _on_image_filter_change(self):
        """Handle image filter change - separate from tag filter"""
        filter_text = self.image_filter_entry.get().strip().lower()
        if filter_text:
            self._filter_images_by_tag(filter_text)
        else:
            # Show all images again
            self._reload_grid()


    def _on_image_filter_clear(self):
        """Clear image filter and show all images"""
        self._reload_grid()

    def _on_canvas_configure(self, event):
        """Handle canvas resize to reflow grid"""
        # Update the width of the grid container to match canvas
        self.grid_canvas.itemconfig(self.grid_canvas_window, width=event.width)
        # Trigger reflow
        self.window.after(100, self._reflow_grid)
        
    def _load_all_images(self):
        """Load all images into grid"""
        # Clear existing
        for widget in self.grid_container.winfo_children():
            widget.destroy()
        
        self.thumbnails.clear()
        self.image_frames.clear()
        
        if not self.data_manager.image_files:
            tk.Label(
                self.grid_container, 
                text="No images loaded. Open a folder first.",
                font=('Arial', 12), bg='#fafafa', fg='#999'
            ).pack(pady=50)
            return
        
        # Create grid items
        self._create_grid_items()
        
    def _create_grid_items(self):
        canvas_width = self.grid_canvas.winfo_width()
        if canvas_width <= 1:
            self.window.after(100, self._create_grid_items)
            return
        
        item_width = self.thumbnail_size + 20
        cols = max(1, canvas_width // item_width)
        
        row_frame = None
        col_count = 0
        
        sorted_images = sorted(self.data_manager.image_files, key=lambda x: Path(x).name.lower())
        
        for idx, img_path in enumerate(sorted_images):
            if col_count == 0:
                row_frame = tk.Frame(self.grid_container, bg=self.bg_color)
                row_frame.pack(side=tk.TOP, fill=tk.X)
            
            self._create_thumbnail_item(img_path, row_frame)
            
            col_count += 1
            if col_count >= cols:
                col_count = 0
                
    def _create_thumbnail_item(self, img_path, parent_row):
        """Create a single thumbnail with selection capability"""
        # Container frame
        container = tk.Frame(parent_row, bg='#fafafa', padx=10, pady=10)
        container.pack(side=tk.LEFT, anchor=tk.N)
        
        # Image frame with border (for selection highlighting)
        img_frame = tk.Frame(
            container, 
            bg='white', 
            bd=3, 
            relief=tk.SOLID,
            highlightthickness=0
        )
        img_frame.pack()
        
        self.image_frames[img_path] = img_frame
        
        # Load and display thumbnail
        try:
            img = Image.open(img_path)
            
            # Calculate aspect ratio resize
            img.thumbnail((self.thumbnail_size, self.thumbnail_size), Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            self.thumbnails[img_path] = photo
            
            label = tk.Label(img_frame, image=photo, bg='white')
            label.pack()
            
            # Click to select/deselect
            label.bind('<Button-1>', lambda e, p=img_path: self._toggle_selection(p))
            img_frame.bind('<Button-1>', lambda e, p=img_path: self._toggle_selection(p))
            
            # Filename label
            filename = Path(img_path).name
            if len(filename) > 20:
                filename = filename[:17] + "..."
            
            name_label = tk.Label(
                container, text=filename, 
                bg='#fafafa', fg='#333',
                font=('Arial', 8)
            )
            name_label.pack()
            
            # Update selection visual if already selected
            if img_path in self.selected_images:
                self._update_selection_visual(img_path, True)
                
        except Exception as e:
            print(f"Error loading thumbnail {img_path}: {e}")
            
    def _toggle_selection(self, img_path):
        """Toggle image selection"""
        if img_path in self.selected_images:
            self.selected_images.remove(img_path)
        else:
            self.selected_images.add(img_path)
        
        # Update visuals considering both selection and highlight
        if self.highlighted_tag:
            self._highlight_images_with_tag(self.highlighted_tag)
        else:
            self._update_selection_visual(img_path, img_path in self.selected_images)
        
        self._update_selection_info()
        self._update_tag_list()
        
    def _update_selection_visual(self, img_path, selected):
        """Update visual appearance of selected/deselected image"""
        if img_path not in self.image_frames:
            return
        
        frame = self.image_frames[img_path]
        
        if selected:
            frame.config(
                bg='#2196F3', 
                highlightbackground='#2196F3',
                highlightthickness=3,
                bd=0
            )
        else:
            frame.config(
                bg='white',
                highlightthickness=0,
                bd=3
            )
            
    def _clear_selection(self):
        """Clear all selections"""
        self.selected_images.clear()
        
        # Reapply highlights if active
        if self.highlighted_tag:
            self._highlight_images_with_tag(self.highlighted_tag)
        else:
            for img_path in self.image_frames:
                self._update_selection_visual(img_path, False)
        
        self._update_selection_info()
        self._update_tag_list()
        
    def _select_all(self):
        """Select all images"""
        for img_path in self.data_manager.image_files:
            self.selected_images.add(img_path)
        
        # Reapply highlights if active
        if self.highlighted_tag:
            self._highlight_images_with_tag(self.highlighted_tag)
        else:
            for img_path in self.image_frames:
                self._update_selection_visual(img_path, True)
        
        self._update_selection_info()
        self._update_tag_list()
        
    def _update_selection_info(self):
        """Update selection counter label"""
        count = len(self.selected_images)
        total = len(self.data_manager.image_files)
        self.selection_label.config(text=f"{count} of {total} images selected")
            
    def _update_tag_list(self):
        """Update tag list showing all tags from selected images with counts"""
        self.tag_listbox.delete(0, tk.END)
        
        if not self.selected_images:
            self.tag_listbox.insert(tk.END, "No images selected")
            return
        
        # Get filter text
        filter_text = self.tag_filter_entry.get().lower() if hasattr(self, 'tag_filter_entry') else ''
        
        # Count tag occurrences across selected images
        tag_counts = {}
        
        for img_path in self.selected_images:
            tags = self.data_manager.get_tags(img_path)
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort by frequency (descending), then alphabetically
        sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
        
        # Display with count, applying filter
        total_selected = len(self.selected_images)
        for tag, count in sorted_tags:
            if not filter_text or filter_text in tag.lower():
                self.tag_listbox.insert(tk.END, f"{tag} ({count}/{total_selected})")
        
        
    def _bulk_add_tag(self):
        """Add tag to all selected images"""
        if not self.selected_images:
            messagebox.showwarning("No Selection", "Please select images first", parent=self.window)
            return
        
        new_tag = self.add_tag_entry.get().strip()
        if not new_tag:
            messagebox.showwarning("Invalid Input", "Please enter a tag", parent=self.window)
            return
        
        # Add to all selected images
        count = 0
        for img_path in self.selected_images:
            tags = self.data_manager.get_tags(img_path)
            if new_tag not in tags:
                tags.append(new_tag)
                self.data_manager.save_tags(img_path, tags)
                count += 1
        
        self.add_tag_entry.delete(0, tk.END)
        self._update_tag_list()
        
        # Show success in status area instead of popup
        self.selection_label.config(text=f"✓ Added '{new_tag}' to {count} images")
        self.window.after(3000, self._update_selection_info)
        
    def _bulk_remove_tag(self):
        """Remove selected tags from all selected images"""
        if not self.selected_images:
            messagebox.showwarning("No Selection", "Please select images first", parent=self.window)
            return
        
        selection = self.tag_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Tag Selected", "Please select tag(s) to remove", parent=self.window)
            return
        
        # Extract tag names from selection
        tags_to_remove = []
        for idx in selection:
            item = self.tag_listbox.get(idx)
            tag = item.split(' (')[0]
            tags_to_remove.append(tag)
        
        if not messagebox.askyesno(
            "Confirm Removal", 
            f"Remove {len(tags_to_remove)} tag(s) from {len(self.selected_images)} images?",
            parent=self.window
        ):
            return
        
        # Remove from all selected images
        total_removals = 0
        for img_path in self.selected_images:
            tags = self.data_manager.get_tags(img_path)
            original_len = len(tags)
            tags = [t for t in tags if t not in tags_to_remove]
            
            if len(tags) < original_len:
                self.data_manager.save_tags(img_path, tags)
                total_removals += 1
        
        self._update_tag_list()
        self.selection_label.config(text=f"✓ Removed tags from {total_removals} images")
        self.window.after(3000, self._update_selection_info)
        
    def _bulk_rename_tag(self):
        if not self.selected_images:
            messagebox.showwarning("No Selection", "Please select images first", parent=self.window)
            return
        
        selection = self.tag_listbox.curselection()
        if not selection or len(selection) != 1:
            messagebox.showwarning("Invalid Selection", "Please select exactly one tag to rename", parent=self.window)
            return
        
        item = self.tag_listbox.get(selection[0])
        
        import re
        match = re.match(r'^(.+?)\s+\((\d+/\d+)\)$', item)
        if match:
            old_tag = match.group(1)
        else:
            old_tag = item
        
        dialog = tk.Toplevel(self.window)
        dialog.title("Rename Tag")
        dialog.geometry("400x150")
        dialog.transient(self.window)
        dialog.grab_set()
        
        tk.Label(dialog, text=f"Old tag:", font=('Arial', 9, 'bold')).pack(pady=(10, 2))
        tk.Label(dialog, text=old_tag, font=('Arial', 10), fg='#1565C0').pack(pady=(0, 10))
        
        tk.Label(dialog, text="New tag:", font=('Arial', 9, 'bold')).pack(pady=2)
        entry = tk.Entry(dialog, width=40, font=('Arial', 10))
        entry.insert(0, old_tag)
        entry.pack(pady=5, padx=10)
        entry.focus()
        entry.select_range(0, tk.END)
        
        result = {'value': None}
        
        def confirm():
            result['value'] = entry.get()
            dialog.destroy()
        
        def cancel():
            dialog.destroy()
        
        entry.bind('<Return>', lambda e: confirm())
        entry.bind('<Escape>', lambda e: cancel())
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="OK", command=confirm, bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
        
        new_tag = result['value']
        if not new_tag or new_tag.strip() == "" or new_tag == old_tag:
            return
        
        new_tag = new_tag.strip()
        
        count = 0
        for img_path in self.selected_images:
            tags = self.data_manager.get_tags(img_path)
            if old_tag in tags:
                idx = tags.index(old_tag)
                tags[idx] = new_tag
                self.data_manager.save_tags(img_path, tags)
                count += 1
        
        self._update_tag_list()
        self.selection_label.config(text=f"✓ Renamed to '{new_tag}' in {count} images")
        self.window.after(3000, self._update_selection_info)
        
    def _on_size_change(self, value):
        """Handle thumbnail size slider change"""
        self.thumbnail_size = int(float(value))
        self.size_label.config(text=f"{self.thumbnail_size}px")
        
        # Debounce: only reload after slider stops moving
        if hasattr(self, '_size_change_timer'):
            self.window.after_cancel(self._size_change_timer)
        
        self._size_change_timer = self.window.after(300, self._reload_grid)
        
    def _reload_grid(self):
        """Reload entire grid with new thumbnail size"""
        self._load_all_images()
        
    def _reflow_grid(self):
        """Reflow grid layout when canvas size changes"""
        # For simplicity, just reload. Could optimize later.
        if hasattr(self, '_reflow_timer'):
            self.window.after_cancel(self._reflow_timer)
        
        self._reflow_timer = self.window.after(300, self._reload_grid)

    def _toggle_background(self):
        """Toggle between black and white background"""
        if self.bg_color == '#fafafa':
            self.bg_color = '#1a1a1a'
        else:
            self.bg_color = '#fafafa'
        
        self.grid_container.config(bg=self.bg_color)
        self.grid_canvas.config(bg=self.bg_color)
        
        # Update all container frames
        for widget in self.grid_container.winfo_children():
            widget.config(bg=self.bg_color)
            for child in widget.winfo_children():
                if isinstance(child, tk.Frame) and not isinstance(child, tk.LabelFrame):
                    child.config(bg=self.bg_color)


    def _on_tag_click(self, event):
        """Handle tag selection to highlight images"""
        selection = self.tag_listbox.curselection()
        if not selection:
            # Deselect - remove highlights
            if self.highlighted_tag:
                self._clear_tag_highlights()
            return
        
        # Get selected tag
        item = self.tag_listbox.get(selection[0])
        tag = item.split(' (')[0]
        
        # Toggle if same tag
        if self.highlighted_tag == tag:
            self._clear_tag_highlights()
            self.tag_listbox.selection_clear(0, tk.END)
            return
        
        # Highlight images with this tag
        self._highlight_images_with_tag(tag)

    def _highlight_images_with_tag(self, tag):
        """Highlight images that contain the specified tag"""
        self.highlighted_tag = tag
        
        for img_path in self.data_manager.image_files:
            if img_path not in self.image_frames:
                continue
            
            frame = self.image_frames[img_path]
            tags = self.data_manager.get_tags(img_path)
            
            is_selected = img_path in self.selected_images
            has_tag = tag in tags
            
            if is_selected and has_tag:
                # BOTH selected AND has tag - purple/magenta border (mix of blue + green)
                frame.config(
                    bg='#9C27B0',
                    highlightbackground='#9C27B0',
                    highlightthickness=5,
                    bd=0
                )
            elif is_selected and not has_tag:
                # Selected but NO tag - keep blue
                frame.config(
                    bg='#2196F3',
                    highlightbackground='#2196F3',
                    highlightthickness=3,
                    bd=0
                )
            elif not is_selected and has_tag:
                # NOT selected but HAS tag - green
                frame.config(
                    bg='#4CAF50',
                    highlightbackground='#4CAF50',
                    highlightthickness=3,
                    bd=0
                )
            else:
                # Neither selected nor has tag - dim
                frame.config(
                    bg='#e0e0e0',
                    highlightthickness=1,
                    highlightbackground='#bdbdbd',
                    bd=0
                )

    def _clear_tag_highlights(self):
        """Remove tag highlighting from all images"""
        self.highlighted_tag = None
        
        for img_path in self.data_manager.image_files:
            if img_path not in self.image_frames:
                continue
            
            # Restore to selection state only
            if img_path in self.selected_images:
                self._update_selection_visual(img_path, True)
            else:
                self._update_selection_visual(img_path, False)

    def _open_tag_editor(self):
        """Open tag editor with selected images only"""
        if not self.selected_images:
            messagebox.showwarning("No Selection", "Please select images first", parent=self.window)
            return
        
        # Import here to avoid circular dependency
        from tag_editor import TagEditor
        
        # Create tag editor with selected images
        TagEditor(self.window, self.data_manager, list(self.selected_images), self)

    def refresh_from_editor(self):
        """Called by tag editor when returning - refresh display"""
        self._update_tag_list()
        # Reload grid to show any changes
        self._reload_grid()


    def _on_filter_images_toggle(self):
        """Toggle image filtering based on tag filter"""
        if self.filter_images_var.get():
            # Apply filter to images
            filter_text = self.tag_filter_entry.get().strip().lower()
            if filter_text:
                self._filter_images_by_tag(filter_text)
        else:
            # Show all images again
            self._reload_grid()

    def _filter_images_by_tag(self, search_term):
        """Filter displayed images by tag"""
        if not search_term:
            self._reload_grid()
            return
        
        # Clear grid
        for widget in self.grid_container.winfo_children():
            widget.destroy()
        
        self.thumbnails.clear()
        self.image_frames.clear()
        
        # Find images with matching tags
        matching_images = []
        for img_path in self.data_manager.image_files:
            tags = self.data_manager.get_tags(img_path)
            for tag in tags:
                if search_term in tag.lower():
                    matching_images.append(img_path)
                    break
        
        if not matching_images:
            tk.Label(
                self.grid_container,
                text=f"No images found with tag containing '{search_term}'",
                font=('Arial', 12), bg='#fafafa', fg='#999'
            ).pack(pady=50)
            return
        
        # Create grid with filtered images
        self._create_filtered_grid(matching_images)

    def _create_filtered_grid(self, image_list):
        canvas_width = self.grid_canvas.winfo_width()
        if canvas_width <= 1:
            self.window.after(100, lambda: self._create_filtered_grid(image_list))
            return
        
        item_width = self.thumbnail_size + 20
        cols = max(1, canvas_width // item_width)
        
        row_frame = None
        col_count = 0
        
        sorted_images = sorted(image_list, key=lambda x: Path(x).name.lower())
        
        for img_path in sorted_images:
            if col_count == 0:
                row_frame = tk.Frame(self.grid_container, bg=self.bg_color)
                row_frame.pack(side=tk.TOP, fill=tk.X)
            
            self._create_thumbnail_item(img_path, row_frame)
            
            col_count += 1
            if col_count >= cols:
                col_count = 0
                
    def _create_grid_items(self):
        canvas_width = self.grid_canvas.winfo_width()
        if canvas_width <= 1:
            self.window.after(100, self._create_grid_items)
            return
        
        item_width = self.thumbnail_size + 20
        cols = max(1, canvas_width // item_width)
        
        row_frame = None
        col_count = 0
        
        sorted_images = sorted(self.data_manager.image_files, key=lambda x: Path(x).name.lower())
        
        for idx, img_path in enumerate(sorted_images):
            if col_count == 0:
                row_frame = tk.Frame(self.grid_container, bg=self.bg_color)
                row_frame.pack(side=tk.TOP, fill=tk.X)
            
            self._create_thumbnail_item(img_path, row_frame)
            
            col_count += 1
            if col_count >= cols:
                col_count = 0