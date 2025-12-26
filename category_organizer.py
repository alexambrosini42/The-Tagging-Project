import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path
import json
import hashlib
import re
from collections import Counter

class CategoryOrganizer:
    def __init__(self, parent, data_manager, image_list, bulk_editor):
        self.parent = parent
        self.data_manager = data_manager
        self.image_list = sorted(image_list, key=lambda x: Path(x).name.lower())
        self.bulk_editor = bulk_editor
        
        self.window = tk.Toplevel(parent)
        self.window.title(f"Category Organizer - {len(image_list)} images")
        
        try:
            self.window.state('zoomed')
        except:
            try:
                self.window.attributes('-zoomed', True)
            except:
                w = self.window.winfo_screenwidth()
                h = self.window.winfo_screenheight()
                self.window.geometry(f"{w}x{h}+0+0")
        
        self.categories = []
        self.uncategorized_tags = {}
        self.tag_renames = {}
        self.undo_stack = []
        self.redo_stack = []
        
        self.dragged_tag = None
        self.drag_source_category = None
        self.drag_ghost = None
        self.drop_indicator = None

        self.drop_position_indicator = None


        
        self._load_category_config()
        self._load_project_groups()
        self._populate_uncategorized()
        
        self._setup_ui()

    def _load_category_config(self):
        config_path = Path(__file__).parent / '.lora_tagger_categories.json'
        
        if not config_path.exists():
            messagebox.showerror("Error", "Category configuration file not found!", parent=self.window)
            self.window.destroy()
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            for cat in config['categories']:
                self.categories.append({
                    'name': cat['name'],
                    'description': cat['description'],
                    'auto_keywords': cat['auto_keywords'],
                    'tags': []
                })
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load category config: {e}", parent=self.window)
            self.window.destroy()
    
    def _get_project_hash(self):
        folder_path = str(self.data_manager.folder_path.absolute())
        return hashlib.md5(folder_path.encode()).hexdigest()[:8]
    
    def _get_groups_file_path(self):
        project_hash = self._get_project_hash()
        return self.data_manager.folder_path / f'.lora_tagger_groups_{project_hash}.json'
    
    def _load_project_groups(self):
        groups_file = self._get_groups_file_path()
        
        if not groups_file.exists():
            return
        
        try:
            with open(groups_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            images_data = data.get('images', {})
            
            tag_to_categories = {}
            
            for img_path in self.image_list:
                img_name = Path(img_path).name
                
                if img_name in images_data:
                    for cat_name, tags in images_data[img_name].items():
                        for tag in tags:
                            if tag not in tag_to_categories:
                                tag_to_categories[tag] = cat_name
            
            for tag, cat_name in tag_to_categories.items():
                for category in self.categories:
                    if category['name'] == cat_name:
                        if tag not in category['tags']:
                            category['tags'].append(tag)
                        break
        except Exception as e:
            print(f"Error loading project groups: {e}")
    
    def _populate_uncategorized(self):
        all_tags = Counter()
        
        for img_path in self.image_list:
            tags = self.data_manager.get_tags(img_path)
            all_tags.update(tags)
        
        categorized_tags = set()
        for category in self.categories:
            categorized_tags.update(category['tags'])
        
        self.uncategorized_tags = {tag: count for tag, count in all_tags.items() 
                                   if tag not in categorized_tags}
    
    def _setup_ui(self):
        toolbar = tk.Frame(self.window, bg='#f0f0f0', height=60)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)
        
        tk.Label(toolbar, text=f"Category Organizer - {len(self.image_list)} images selected", 
                bg='#f0f0f0', font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=20)
        
        tk.Button(toolbar, text="Save", command=self._save_categories,
                bg='#4CAF50', fg='white', font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        
        tk.Button(toolbar, text="Undo", command=self._undo,
                bg='#FF9800', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(toolbar, text="Redo", command=self._redo,
                bg='#FF9800', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(toolbar, text="Auto-Categorize", command=self._auto_categorize,
                bg='#2196F3', fg='white', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Button(toolbar, text="Close", command=self._close_window,
                bg='#666', fg='white', font=('Arial', 10)).pack(side=tk.RIGHT, padx=20)
        
        main_container = tk.PanedWindow(self.window, orient=tk.HORIZONTAL, sashwidth=5)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        self._create_uncategorized_panel(main_container)
        self._create_categories_panel(main_container)
    
    def _create_uncategorized_panel(self, parent):
        panel = tk.Frame(parent, bg='white')
        parent.add(panel, width=self.data_manager.config.UNCATEGORIZED_PANEL_WIDTH)

        
        tk.Label(panel, text="UNCATEGORIZED TAGS", bg='white', 
                font=('Arial', 12, 'bold')).pack(pady=10)
        
        filter_frame = tk.Frame(panel, bg='white')
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(filter_frame, text="Filter:", bg='white').pack(side=tk.LEFT)
        self.uncat_filter_entry = tk.Entry(filter_frame, width=15)
        self.uncat_filter_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.uncat_filter_entry.bind('<KeyRelease>', lambda e: self._update_uncategorized_list())
        
        tk.Button(filter_frame, text="X", command=lambda: [self.uncat_filter_entry.delete(0, tk.END), 
                self._update_uncategorized_list()], bg='#666', fg='white').pack(side=tk.LEFT)
        
        list_frame = tk.Frame(panel, bg='white')
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        scroll = tk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.uncat_canvas = tk.Canvas(list_frame, bg='white', highlightthickness=0, 
                                      yscrollcommand=scroll.set)
        self.uncat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.uncat_canvas.yview)

        def _on_mousewheel_uncat(event):
            self.uncat_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        self.uncat_canvas.bind_all("<MouseWheel>", _on_mousewheel_uncat)
        self.uncat_canvas.bind_all("<Button-4>", lambda e: self.uncat_canvas.yview_scroll(-1, "units"))
        self.uncat_canvas.bind_all("<Button-5>", lambda e: self.uncat_canvas.yview_scroll(1, "units"))

        self.uncat_container = tk.Frame(self.uncat_canvas, bg='white')
        self.uncat_canvas_window = self.uncat_canvas.create_window((0, 0), 
                                    window=self.uncat_container, anchor=tk.NW)
        
        self.uncat_container.bind('<Configure>', 
            lambda e: self.uncat_canvas.configure(scrollregion=self.uncat_canvas.bbox('all')))
        
        self.uncat_canvas.bind('<Configure>', 
            lambda e: self.uncat_canvas.itemconfig(self.uncat_canvas_window, width=e.width-5))
        
        self._update_uncategorized_list()
    
    def _create_categories_panel(self, parent):
        panel = tk.Frame(parent, bg='#f5f5f5')
        parent.add(panel)
        
        canvas = tk.Canvas(panel, bg='#f5f5f5', highlightthickness=0)
        scrollbar = tk.Scrollbar(panel, orient=tk.VERTICAL, command=canvas.yview)
        
        self.categories_container = tk.Frame(canvas, bg='#f5f5f5')
        self.categories_canvas = canvas

        def _on_mousewheel_cat(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel_cat)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        canvas.create_window((0, 0), window=self.categories_container, anchor=tk.NW)
        
        self.categories_container.bind('<Configure>', 
            lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        self._render_categories()

    def _update_single_category(self, category_name):
        scroll_pos = self._get_scroll_position()
        
        for widget in self.categories_container.winfo_children():
            if isinstance(widget, tk.LabelFrame) and widget.cget('text') == category_name:
                for child in widget.winfo_children():
                    child.destroy()
                
                for category in self.categories:
                    if category['name'] == category_name:
                        if category['description']:
                            desc = tk.Label(widget, text=category['description'], bg='white', 
                                          fg='#666', font=('Arial', 9), wraplength=600, justify=tk.LEFT)
                            desc.pack(anchor=tk.W, pady=(0, 5))
                        
                        dropzone = tk.Frame(widget, bg='#E8F5E9', bd=2, relief=tk.SOLID, height=100)
                        dropzone.pack(fill=tk.BOTH, expand=True, pady=5)
                        dropzone.category_name = category['name']
                        
                        dropzone.bind('<Enter>', lambda e, dz=dropzone: self._on_dropzone_enter(e, dz))
                        dropzone.bind('<Leave>', lambda e, dz=dropzone: self._on_dropzone_leave(e, dz))
                        
                        tags_container = tk.Frame(dropzone, bg='#E8F5E9')
                        tags_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                        
                        if category['tags']:
                            self._render_category_tags(category, tags_container)
                        else:
                            placeholder = tk.Label(tags_container, text="Drop tags here...", 
                                                  bg='#E8F5E9', fg='#999', font=('Arial', 10, 'italic'))
                            placeholder.pack(expand=True)
                        
                        btn_frame = tk.Frame(widget, bg='white')
                        btn_frame.pack(fill=tk.X, pady=(5, 0))
                        
                        tk.Button(btn_frame, text="+ Add Tag to Category", 
                                command=lambda c=category['name']: self._add_tag_to_category(c),
                                bg='#2196F3', fg='white', font=('Arial', 9)).pack(side=tk.LEFT)
                        break
                break
        
        self.window.after(10, lambda: self._restore_scroll_position(scroll_pos))

    def _render_categories(self):
        scroll_pos = self._get_scroll_position()
        
        for widget in self.categories_container.winfo_children():
            widget.destroy()
        
        for category in self.categories:
            self._create_category_widget(category)
        
        self.window.after(50, lambda: self._restore_scroll_position(scroll_pos))
    
    def _get_scroll_position(self):
        try:
            return self.categories_canvas.yview()[0]
        except:
            return 0
    
    def _restore_scroll_position(self, pos):
        try:
            self.categories_canvas.yview_moveto(pos)
        except:
            pass
    
    def _create_category_widget(self, category):
        frame = tk.LabelFrame(self.categories_container, text=category['name'], 
                            bg='white', font=('Arial', 11, 'bold'), padx=10, pady=10)
        frame.pack(fill=tk.X, padx=10, pady=10)
        
        if category['description']:
            desc = tk.Label(frame, text=category['description'], bg='white', 
                          fg='#666', font=('Arial', 9), wraplength=600, justify=tk.LEFT)
            desc.pack(anchor=tk.W, pady=(0, 5))
        
        dropzone = tk.Frame(frame, bg='#E8F5E9', bd=2, relief=tk.SOLID, height=100)
        dropzone.pack(fill=tk.BOTH, expand=True, pady=5)
        dropzone.category_name = category['name']
        
        dropzone.bind('<Enter>', lambda e, dz=dropzone: self._on_dropzone_enter(e, dz))
        dropzone.bind('<Leave>', lambda e, dz=dropzone: self._on_dropzone_leave(e, dz))
        
        tags_container = tk.Frame(dropzone, bg='#E8F5E9')
        tags_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        if category['tags']:
            self._render_category_tags(category, tags_container)
        else:
            placeholder = tk.Label(tags_container, text="Drop tags here...", 
                                  bg='#E8F5E9', fg='#999', font=('Arial', 10, 'italic'))
            placeholder.pack(expand=True)
        
        btn_frame = tk.Frame(frame, bg='white')
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        tk.Button(btn_frame, text="+ Add Tag to Category", 
                command=lambda c=category['name']: self._add_tag_to_category(c),
                bg='#2196F3', fg='white', font=('Arial', 9)).pack(side=tk.LEFT)
    
    def _render_category_tags(self, category, parent):
        container_width = 600
        current_row = tk.Frame(parent, bg='#E8F5E9')
        current_row.pack(anchor=tk.W, fill=tk.X, pady=2)
        
        current_width = 0
        
        for tag in category['tags']:
            display_tag = self.tag_renames.get(tag, tag)
            estimated_width = len(display_tag) * 8 + 60
            
            if current_width + estimated_width > container_width and current_width > 0:
                current_row = tk.Frame(parent, bg='#E8F5E9')
                current_row.pack(anchor=tk.W, fill=tk.X, pady=2)
                current_width = 0
            
            self._create_category_tag_pill(tag, display_tag, category['name'], current_row)
            current_width += estimated_width

    def _create_category_tag_pill(self, original_tag, display_tag, category_name, parent_row):
        is_renamed = original_tag in self.tag_renames
        bg_color = '#FFF59D' if is_renamed else '#E3F2FD'
        
        pill_frame = tk.Frame(parent_row, bg=bg_color, bd=0, relief=tk.FLAT)
        pill_frame.pack(side=tk.LEFT, padx=self.data_manager.config.TAG_PILL_MARGIN, 
                       pady=self.data_manager.config.TAG_PILL_MARGIN)
        
        inner = tk.Frame(pill_frame, bg=bg_color)
        inner.pack(padx=self.data_manager.config.TAG_PILL_PADDING_X, 
                  pady=self.data_manager.config.TAG_PILL_PADDING_Y)
        
        pill_frame.config(highlightbackground='#90CAF9', highlightthickness=1)
        pill_frame.original_tag = original_tag
        pill_frame.category_name = category_name
        
        drag_label = tk.Label(inner, text="⋮⋮", bg=bg_color, fg='#757575', 
                            font=('Arial', 8), cursor='fleur')
        drag_label.pack(side=tk.LEFT, padx=(0, 4))
        
        for widget in [pill_frame, inner, drag_label]:
            widget.bind('<Button-1>', lambda e, t=original_tag, c=category_name, f=pill_frame: 
                       self._start_drag_category(e, t, c, f))
            widget.bind('<B1-Motion>', lambda e: self._on_drag_motion_category(e))
            widget.bind('<ButtonRelease-1>', lambda e, f=pill_frame: self._end_drag_category(e, f))
        
        tag_label = tk.Label(inner, text=display_tag, bg=bg_color, fg='#1565C0',
                        font=('Arial', self.data_manager.config.TAG_PILL_FONT_SIZE))
        tag_label.pack(side=tk.LEFT, padx=2)
        tag_label.bind('<Double-Button-1>', lambda e, t=original_tag: self._rename_tag_inline(t))
        
        remove_btn = tk.Label(inner, text="✕", bg=bg_color, fg='#D32F2F',
                            font=('Arial', self.data_manager.config.TAG_PILL_FONT_SIZE, 'bold'), 
                            cursor='hand2')
        remove_btn.pack(side=tk.LEFT, padx=(4, 0))
        remove_btn.bind('<Button-1>', lambda e, t=original_tag, c=category_name: 
                       self._remove_from_category(t, c))
        
        def on_enter(e):
            new_bg = '#FFF9C4' if is_renamed else '#BBDEFB'
            pill_frame.config(bg=new_bg, highlightbackground='#64B5F6')
            inner.config(bg=new_bg)
            drag_label.config(bg=new_bg)
            tag_label.config(bg=new_bg)
            remove_btn.config(bg=new_bg)
        
        def on_leave(e):
            if not hasattr(self, 'dragged_frame') or self.dragged_frame != pill_frame:
                pill_frame.config(bg=bg_color, highlightbackground='#90CAF9')
                inner.config(bg=bg_color)
                drag_label.config(bg=bg_color)
                tag_label.config(bg=bg_color)
                remove_btn.config(bg=bg_color)
        
        pill_frame.bind('<Enter>', on_enter)
        pill_frame.bind('<Leave>', on_leave)
    
    def _create_uncategorized_tag_pill(self, tag, count, parent_row):
        pill_frame = tk.Frame(parent_row, bg='#EEEEEE', bd=0, relief=tk.FLAT)
        pill_frame.pack(side=tk.LEFT, padx=self.data_manager.config.TAG_PILL_MARGIN, 
                       pady=self.data_manager.config.TAG_PILL_MARGIN)
        
        inner = tk.Frame(pill_frame, bg='#EEEEEE')
        inner.pack(padx=self.data_manager.config.TAG_PILL_PADDING_X, 
                  pady=self.data_manager.config.TAG_PILL_PADDING_Y)
        
        pill_frame.config(highlightbackground='#BDBDBD', highlightthickness=1)
        pill_frame.tag_name = tag
        pill_frame.is_uncategorized = True
        
        drag_label = tk.Label(inner, text="⋮⋮", bg='#EEEEEE', fg='#757575', 
                            font=('Arial', 8), cursor='fleur')
        drag_label.pack(side=tk.LEFT, padx=(0, 4))
        
        for widget in [pill_frame, inner, drag_label]:
            widget.bind('<Button-1>', lambda e, t=tag, f=pill_frame: 
                       self._start_drag_uncategorized(e, t, f))
            widget.bind('<B1-Motion>', lambda e: self._on_drag_motion_category(e))
            widget.bind('<ButtonRelease-1>', lambda e, f=pill_frame: self._end_drag_category(e, f))
        
        tag_label = tk.Label(inner, text=f"{tag} ({count}/{len(self.image_list)})", 
                           bg='#EEEEEE', fg='#424242',
                           font=('Arial', self.data_manager.config.TAG_PILL_FONT_SIZE))
        tag_label.pack(side=tk.LEFT, padx=2)
        
        def on_enter(e):
            pill_frame.config(bg='#E0E0E0', highlightbackground='#9E9E9E')
            inner.config(bg='#E0E0E0')
            drag_label.config(bg='#E0E0E0')
            tag_label.config(bg='#E0E0E0')
        
        def on_leave(e):
            if not hasattr(self, 'dragged_frame') or self.dragged_frame != pill_frame:
                pill_frame.config(bg='#EEEEEE', highlightbackground='#BDBDBD')
                inner.config(bg='#EEEEEE')
                drag_label.config(bg='#EEEEEE')
                tag_label.config(bg='#EEEEEE')
        
        pill_frame.bind('<Enter>', on_enter)
        pill_frame.bind('<Leave>', on_leave)
    
    def _update_uncategorized_list(self):
        for widget in self.uncat_container.winfo_children():
            widget.destroy()
        
        filter_text = self.uncat_filter_entry.get().strip().lower()
        
        sorted_tags = sorted(self.uncategorized_tags.items(), key=lambda x: (-x[1], x[0].lower()))
        
        container_width = self.data_manager.config.UNCATEGORIZED_PANEL_WIDTH - 20

        current_row = tk.Frame(self.uncat_container, bg='white')
        current_row.pack(anchor=tk.W, fill=tk.X, pady=2)
        current_width = 0
        
        for tag, count in sorted_tags:
            if filter_text and filter_text not in tag.lower():
                continue
            
            estimated_width = len(tag) * 8 + 80
            
            if current_width + estimated_width > container_width and current_width > 0:
                current_row = tk.Frame(self.uncat_container, bg='white')
                current_row.pack(anchor=tk.W, fill=tk.X, pady=2)
                current_width = 0
            
            self._create_uncategorized_tag_pill(tag, count, current_row)
            current_width += estimated_width
    
    def _start_drag_uncategorized(self, event, tag, frame):
        self.dragged_tag = tag
        self.drag_source_category = None
        self.dragged_frame = frame
        
        self.drag_ghost = tk.Toplevel(self.window)
        self.drag_ghost.wm_overrideredirect(True)
        self.drag_ghost.wm_attributes('-alpha', 0.7)
        self.drag_ghost.wm_attributes('-topmost', True)
        
        ghost_label = tk.Label(self.drag_ghost, text=tag, bg='#FFF59D', fg='#1565C0',
                            font=('Arial', 10, 'bold'), padx=15, pady=6, relief=tk.RAISED, bd=2)
        ghost_label.pack()
        
        self.drag_ghost.geometry(f'+{event.x_root + 10}+{event.y_root + 10}')

        self.drop_position_indicator = tk.Frame(self.window, bg='#4CAF50', height=3, width=100)
        
        frame.config(bg='#E0E0E0', highlightbackground='#BDBDBD')
        for child in frame.winfo_children():
            child.config(bg='#E0E0E0')
            for subchild in child.winfo_children():
                if isinstance(subchild, tk.Label):
                    subchild.config(bg='#E0E0E0')
    
    def _start_drag_category(self, event, tag, category_name, frame):
        self.dragged_tag = tag
        self.drag_source_category = category_name
        self.dragged_frame = frame
        
        self.drag_ghost = tk.Toplevel(self.window)
        self.drag_ghost.wm_overrideredirect(True)
        self.drag_ghost.wm_attributes('-alpha', 0.7)
        self.drag_ghost.wm_attributes('-topmost', True)
        
        display_tag = self.tag_renames.get(tag, tag)
        ghost_label = tk.Label(self.drag_ghost, text=display_tag, bg='#FFF59D', fg='#1565C0',
                            font=('Arial', 10, 'bold'), padx=15, pady=6, relief=tk.RAISED, bd=2)
        ghost_label.pack()
        
        self.drag_ghost.geometry(f'+{event.x_root + 10}+{event.y_root + 10}')
        self.drop_position_indicator = tk.Frame(self.window, bg='#4CAF50', height=3, width=100)

        frame.config(bg='#E0E0E0', highlightbackground='#BDBDBD')
        for child in frame.winfo_children():
            child.config(bg='#E0E0E0')
            for subchild in child.winfo_children():
                if isinstance(subchild, tk.Label):
                    subchild.config(bg='#E0E0E0')
    
    def _on_drag_motion_category(self, event):
            if not self.drag_ghost:
                return
            
            self.drag_ghost.geometry(f'+{event.x_root + 10}+{event.y_root + 10}')
            
            x, y = event.x_root, event.y_root
            target = self.window.winfo_containing(x, y)
            
            target_pill = None
            temp = target
            for _ in range(15):
                if temp and hasattr(temp, 'original_tag') and hasattr(temp, 'category_name'):
                    target_pill = temp
                    break
                temp = temp.master if hasattr(temp, 'master') else None
            
            if target_pill and self.drop_position_indicator:
                try:
                    pill_x = target_pill.winfo_rootx()
                    pill_y = target_pill.winfo_rooty()
                    pill_width = target_pill.winfo_width()
                    pill_height = target_pill.winfo_height()
                    
                    if event.x_root < pill_x + pill_width / 2:
                        self.drop_position_indicator.place(x=pill_x - 2, y=pill_y - (pill_height/2) - 10, height=pill_height, width=3)
                    else:
                        self.drop_position_indicator.place(x=pill_x + pill_width - 1, y=pill_y - (pill_height/2) - 10, height=pill_height, width=3)
                    
                    self.drop_position_indicator.lift()
                except:
                    pass
            else:
                if self.drop_position_indicator:
                    self.drop_position_indicator.place_forget()
    
    def _on_dropzone_enter(self, event, dropzone):
        if self.dragged_tag:
            dropzone.config(bg='#C8E6C9', relief=tk.RAISED)
    
    def _on_dropzone_leave(self, event, dropzone):
        if self.dragged_tag:
            dropzone.config(bg='#E8F5E9', relief=tk.SOLID)
    
    def _end_drag_category(self, event, source_frame):
        if self.drag_ghost:
            self.drag_ghost.destroy()
            self.drag_ghost = None
        
        if self.drop_position_indicator:
            self.drop_position_indicator.place_forget()
        
        if not self.dragged_tag:
            self._reset_drag_visual()
            return
        
        x, y = event.x_root, event.y_root
        target = self.window.winfo_containing(x, y)
        
        target_pill = None
        target_dropzone = None
        temp = target
        
        for _ in range(15):
            if temp and hasattr(temp, 'original_tag') and hasattr(temp, 'category_name'):
                target_pill = temp
                break
            if temp and hasattr(temp, 'category_name') and not hasattr(temp, 'original_tag'):
                target_dropzone = temp
                break
            temp = temp.master if hasattr(temp, 'master') else None
        
        if target_pill:
            target_category_name = target_pill.category_name
            target_tag = target_pill.original_tag
            
            self._push_to_undo()
            
            if self.drag_source_category:
                for category in self.categories:
                    if category['name'] == self.drag_source_category:
                        if self.dragged_tag in category['tags']:
                            category['tags'].remove(self.dragged_tag)
                        break
            else:
                if self.dragged_tag in self.uncategorized_tags:
                    del self.uncategorized_tags[self.dragged_tag]
            
            for category in self.categories:
                if category['name'] == target_category_name:
                    target_idx = category['tags'].index(target_tag) if target_tag in category['tags'] else len(category['tags'])
                    
                    pill_x = target_pill.winfo_rootx()
                    pill_width = target_pill.winfo_width()
                    
                    if event.x_root >= pill_x + pill_width / 2:
                        target_idx += 1
                    
                    if self.dragged_tag not in category['tags']:
                        category['tags'].insert(target_idx, self.dragged_tag)
                    break
            
            if target_pill:
                self._update_single_category(target_category_name)
                if self.drag_source_category and self.drag_source_category != target_category_name:
                    self._update_single_category(self.drag_source_category)
            elif target_dropzone:
                self._update_single_category(target_category_name)
                if self.drag_source_category and self.drag_source_category != target_category_name:
                    self._update_single_category(self.drag_source_category)

            self._update_uncategorized_list()
            
        elif target_dropzone:
            target_category_name = target_dropzone.category_name
            
            self._push_to_undo()
            
            if self.drag_source_category:
                for category in self.categories:
                    if category['name'] == self.drag_source_category:
                        if self.dragged_tag in category['tags']:
                            category['tags'].remove(self.dragged_tag)
                        break
            else:
                if self.dragged_tag in self.uncategorized_tags:
                    del self.uncategorized_tags[self.dragged_tag]
            
            for category in self.categories:
                if category['name'] == target_category_name:
                    if self.dragged_tag not in category['tags']:
                        category['tags'].append(self.dragged_tag)
                    break
            
            self._render_categories()
            self._update_uncategorized_list()
        
        self._reset_drag_visual()
    
    def _reset_drag_visual(self):
        if self.drag_ghost:
            self.drag_ghost.destroy()
            self.drag_ghost = None
        
        self.dragged_tag = None
        self.drag_source_category = None
        self.dragged_frame = None

    def _auto_categorize(self):
        self._push_to_undo()
        
        tags_to_categorize = list(self.uncategorized_tags.keys())
        categorized_count = 0
        
        for tag in tags_to_categorize:
            for category in self.categories:
                matched = False
                
                for keyword in category['auto_keywords']:
                    if self._match_pattern(tag, keyword):
                        if tag not in category['tags']:
                            category['tags'].append(tag)
                        del self.uncategorized_tags[tag]
                        categorized_count += 1
                        matched = True
                        break
                
                if matched:
                    break
        
        self._render_categories()
        self._update_uncategorized_list()
        
        messagebox.showinfo("Auto-Categorize", 
                          f"Categorized {categorized_count} tags automatically", 
                          parent=self.window)
    
    def _match_pattern(self, tag, pattern):
        tag_lower = tag.lower()
        pattern_lower = pattern.lower()
        
        if '*' not in pattern_lower:
            return tag_lower == pattern_lower
        
        if pattern_lower.startswith('*') and pattern_lower.endswith('*'):
            search_term = pattern_lower[1:-1]
            return search_term in tag_lower
        elif pattern_lower.startswith('*'):
            search_term = pattern_lower[1:]
            return tag_lower.endswith(search_term)
        elif pattern_lower.endswith('*'):
            search_term = pattern_lower[:-1]
            return tag_lower.startswith(search_term)
        
        return False
    
    def _rename_tag_inline(self, original_tag):
        found_category = None
        for category in self.categories:
            if original_tag in category['tags']:
                found_category = category['name']
                break
        
        new_name = simpledialog.askstring("Rename Tag", 
                                         f"Rename '{original_tag}' to:",
                                         initialvalue=self.tag_renames.get(original_tag, original_tag),
                                         parent=self.window)
        
        if new_name and new_name.strip() and new_name != original_tag:
            self._push_to_undo()
            self.tag_renames[original_tag] = new_name.strip()
            if found_category:
                self._update_single_category(found_category)
    
    def _remove_from_category(self, tag, category_name):
        self._push_to_undo()
        
        for category in self.categories:
            if category['name'] == category_name:
                if tag in category['tags']:
                    category['tags'].remove(tag)
                break
        
        if tag not in self.uncategorized_tags:
            count = 0
            for img_path in self.image_list:
                tags = self.data_manager.get_tags(img_path)
                actual_tag = tag
                for orig, renamed in self.tag_renames.items():
                    if orig == tag:
                        actual_tag = orig
                        break
                
                if actual_tag in tags or tag in tags:
                    count += 1
            
            self.uncategorized_tags[tag] = count
        
        self._update_single_category(category_name)
        self._update_uncategorized_list()
    
    def _add_tag_to_category(self, category_name):
        new_tag = simpledialog.askstring("Add Tag to Category",
                                        f"Enter tag to add to '{category_name}':",
                                        parent=self.window)
        
        if not new_tag or not new_tag.strip():
            return
        
        new_tag = new_tag.strip()
        
        self._push_to_undo()
        
        for category in self.categories:
            if category['name'] == category_name:
                if new_tag not in category['tags']:
                    category['tags'].append(new_tag)
                break
        
        if new_tag in self.uncategorized_tags:
            del self.uncategorized_tags[new_tag]
        
        self._render_categories()
        self._update_uncategorized_list()

    def _save_categories(self):
        self._push_to_undo()
        
        for img_path in self.image_list:
            current_tags = self.data_manager.get_tags(img_path)
            current_tags_set = set(current_tags)
            
            new_order = []
            used_tags = set()
            
            for category in self.categories:
                for tag in category['tags']:
                    final_tag = self.tag_renames.get(tag, tag)
                    
                    if tag in current_tags_set:
                        new_order.append(final_tag)
                        used_tags.add(tag)
                    elif final_tag in current_tags_set:
                        new_order.append(final_tag)
                        used_tags.add(final_tag)
            
            for tag in current_tags:
                if tag not in used_tags:
                    renamed_from = None
                    for orig, renamed in self.tag_renames.items():
                        if renamed == tag:
                            renamed_from = orig
                            break
                    
                    if renamed_from and renamed_from not in used_tags:
                        new_order.append(tag)
                    elif not renamed_from:
                        new_order.append(tag)
            
            self.data_manager.save_tags(img_path, new_order)
        
        self._save_project_groups()
        
        messagebox.showinfo("Success", 
                          f"Categories saved to {len(self.image_list)} images", 
                          parent=self.window)
    
    def _save_project_groups(self):
        groups_file = self._get_groups_file_path()
        
        project_name = self.data_manager.folder_path.name
        
        images_data = {}
        
        for img_path in self.image_list:
            img_name = Path(img_path).name
            img_categories = {}
            
            current_tags = self.data_manager.get_tags(img_path)
            current_tags_set = set(current_tags)
            
            has_categorized = False
            
            for category in self.categories:
                cat_tags = []
                for tag in category['tags']:
                    final_tag = self.tag_renames.get(tag, tag)
                    
                    if tag in current_tags_set or final_tag in current_tags_set:
                        cat_tags.append(final_tag)
                
                if cat_tags:
                    img_categories[category['name']] = cat_tags
                    has_categorized = True
            
            if has_categorized:
                images_data[img_name] = img_categories
        
        data = {
            'project_name': project_name,
            'images': images_data
        }
        
        try:
            with open(groups_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save groups file: {e}", 
                               parent=self.window)
    
    def _push_to_undo(self):
        state = {
            'categories': json.loads(json.dumps([{
                'name': c['name'],
                'description': c['description'],
                'auto_keywords': c['auto_keywords'],
                'tags': c['tags'].copy()
            } for c in self.categories])),
            'uncategorized_tags': self.uncategorized_tags.copy(),
            'tag_renames': self.tag_renames.copy()
        }
        
        self.undo_stack.append(state)
        self.redo_stack.clear()
    
    def _undo(self):
        if not self.undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo", parent=self.window)
            return
        
        current_state = {
            'categories': json.loads(json.dumps([{
                'name': c['name'],
                'description': c['description'],
                'auto_keywords': c['auto_keywords'],
                'tags': c['tags'].copy()
            } for c in self.categories])),
            'uncategorized_tags': self.uncategorized_tags.copy(),
            'tag_renames': self.tag_renames.copy()
        }
        self.redo_stack.append(current_state)
        
        previous_state = self.undo_stack.pop()
        
        self.categories = json.loads(json.dumps(previous_state['categories']))
        self.uncategorized_tags = previous_state['uncategorized_tags'].copy()
        self.tag_renames = previous_state['tag_renames'].copy()
        
        self._render_categories()
        self._update_uncategorized_list()
    
    def _redo(self):
        if not self.redo_stack:
            messagebox.showinfo("Redo", "Nothing to redo", parent=self.window)
            return
        
        current_state = {
            'categories': json.loads(json.dumps([{
                'name': c['name'],
                'description': c['description'],
                'auto_keywords': c['auto_keywords'],
                'tags': c['tags'].copy()
            } for c in self.categories])),
            'uncategorized_tags': self.uncategorized_tags.copy(),
            'tag_renames': self.tag_renames.copy()
        }
        self.undo_stack.append(current_state)
        
        next_state = self.redo_stack.pop()
        
        self.categories = json.loads(json.dumps(next_state['categories']))
        self.uncategorized_tags = next_state['uncategorized_tags'].copy()
        self.tag_renames = next_state['tag_renames'].copy()
        
        self._render_categories()
        self._update_uncategorized_list()
    
    def _close_window(self):
        self.bulk_editor.refresh_from_editor()
        self.window.destroy()