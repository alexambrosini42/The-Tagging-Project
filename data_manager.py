"""
LoRA Dataset Tagger - Data Manager
Handles all data manipulation, file I/O, and tag analysis
"""

import os
from pathlib import Path
from collections import Counter
from difflib import SequenceMatcher
import re

class DataManager:
    """Manages dataset loading, tag operations, and file I/O"""
    
    def __init__(self, config):
        self.config = config
        self.data = {}  # {filename: [tag1, tag2, ...]}
        self.image_files = []  # List of image file paths
        self.tag_frequency = Counter()  # Global tag frequency
        self.history_stack = []  # Undo history
        self.folder_path = None
        
    def load_data(self, folder_path):
        """Load all images and their corresponding tags from folder"""
        self.folder_path = Path(folder_path)
        self.data.clear()
        self.image_files.clear()
        
        if self.config.ENABLE_RECURSIVE_SCAN:
            image_patterns = [
                self.folder_path.rglob(f"*{ext}") 
                for ext in self.config.SUPPORTED_FORMATS
            ]
        else:
            image_patterns = [
                self.folder_path.glob(f"*{ext}") 
                for ext in self.config.SUPPORTED_FORMATS
            ]
        
        # Flatten the list of image paths
        for pattern in image_patterns:
            for img_path in pattern:
                if img_path.is_file():
                    self.image_files.append(str(img_path))
                    
                    # Load corresponding .txt file
                    txt_path = img_path.with_suffix('.txt')
                    if txt_path.exists():
                        tags = self._load_tags_from_file(txt_path)
                    else:
                        # Create empty .txt file
                        tags = []
                        txt_path.touch()
                    
                    self.data[str(img_path)] = tags
        
        self.image_files.sort()
        self.recalculate_frequency()
        return len(self.image_files)
    
    def _load_tags_from_file(self, txt_path):
        """Load and parse tags from a .txt file"""
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    return []
                
                # Split by the configured separator
                tags = [tag.strip() for tag in content.split(',')]
                tags = [tag for tag in tags if tag]  # Remove empty strings
                return tags
        except Exception as e:
            print(f"Error loading {txt_path}: {e}")
            return []
    
    def recalculate_frequency(self):
        """Rebuild global tag frequency counter"""
        self.tag_frequency.clear()
        for tags in self.data.values():
            self.tag_frequency.update(tags)
    
    def get_tags(self, filename):
        """Get tags for a specific image file"""
        return self.data.get(filename, []).copy()
    
    def save_tags(self, filename, new_tags_list):
        self._push_history(filename, self.data.get(filename, []).copy())
        
        cleaned_tags = []
        seen = set()
        for tag in new_tags_list:
            tag = tag.strip()
            if tag and tag not in seen:
                if self.config.ENFORCE_LOWERCASE:
                    tag = tag.lower()
                cleaned_tags.append(tag)
                seen.add(tag)
        
        self.data[filename] = cleaned_tags
        
        txt_path = Path(filename).with_suffix('.txt')
        content = self.config.TAG_SEPARATOR.join(cleaned_tags)
        
        try:
            with open(txt_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            self.recalculate_frequency()
            return True
        except Exception as e:
            print(f"Error saving {txt_path}: {e}")
            return False
    
    def add_tag_globally(self, tag):
        """Add a tag to all images"""
        tag = tag.strip()
        if not tag:
            return 0
        
        count = 0
        for filename in self.image_files:
            tags = self.data[filename]
            if tag not in tags:
                tags.append(tag)
                self.save_tags(filename, tags)
                count += 1
        
        return count
    
    def remove_tag_globally(self, tag):
        """Remove a tag from all images"""
        tag = tag.strip()
        if not tag:
            return 0
        
        count = 0
        for filename in self.image_files:
            tags = self.data[filename]
            if tag in tags:
                tags.remove(tag)
                self.save_tags(filename, tags)
                count += 1
        
        return count
    
    def rename_tag_globally(self, old_tag, new_tag):
        """Replace all occurrences of old_tag with new_tag (case-sensitive)"""
        old_tag = old_tag.strip()
        new_tag = new_tag.strip()
        
        if not old_tag or not new_tag or old_tag == new_tag:
            return 0
        
        count = 0
        for filename in self.image_files:
            tags = self.data[filename]
            if old_tag in tags:
                idx = tags.index(old_tag)
                tags[idx] = new_tag
                self.save_tags(filename, tags)
                count += 1
        
        return count
    
    def get_all_tags_by_frequency(self):
        """Return all unique tags sorted by frequency (descending)"""
        return self.tag_frequency.most_common()
    
    def get_local_suggestions(self, current_tags):
        """Get tags similar to current tags based on Levenshtein distance"""
        suggestions = set()
        
        for current_tag in current_tags:
            for global_tag, _ in self.tag_frequency.most_common():
                if global_tag not in current_tags:
                    distance = self._levenshtein_distance(current_tag, global_tag)
                    if distance <= self.config.SIMILARITY_THRESHOLD:
                        suggestions.add(global_tag)
        
        # Sort by frequency
        suggestions_with_freq = [
            (tag, self.tag_frequency[tag]) for tag in suggestions
        ]
        suggestions_with_freq.sort(key=lambda x: x[1], reverse=True)
        
        return suggestions_with_freq
    
    def _levenshtein_distance(self, s1, s2):
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _push_history(self, filename, tags):
        """Push current state to history stack"""
        self.history_stack.append((filename, tags))
        if len(self.history_stack) > self.config.HISTORY_MAX_DEPTH:
            self.history_stack.pop(0)
    
    def undo(self):
        """Undo last save operation"""
        if not self.history_stack:
            return None
        
        filename, old_tags = self.history_stack.pop()
        
        # Restore without adding to history
        self.data[filename] = old_tags
        txt_path = Path(filename).with_suffix('.txt')
        content = self.config.TAG_SEPARATOR.join(old_tags)
        
        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.recalculate_frequency()
            return filename
        except Exception as e:
            print(f"Error during undo: {e}")
            return None
    
    def filter_images_by_tag(self, search_term):
        """Filter image list by tags containing search term"""
        if not search_term:
            return self.image_files.copy()
        
        search_term = search_term.lower()
        filtered = []
        
        for filename in self.image_files:
            tags = self.data.get(filename, [])
            for tag in tags:
                if search_term in tag.lower():
                    filtered.append(filename)
                    break
        
        return filtered
    
    def get_png_metadata(self, filename):
        from PIL import Image
        import re
        
        if not filename.lower().endswith('.png'):
            return None
        
        try:
            img = Image.open(filename)
            
            if not hasattr(img, 'info') or 'parameters' not in img.info:
                return None
            
            parameters = img.info['parameters']
            
            if not parameters:
                return None
            
            pattern = r'(?:^|(?<=>))([^<>]*)(?=(?:<[^>]+:[^>]+>|Negative prompt:))'
            matches = re.findall(pattern, parameters, re.MULTILINE | re.DOTALL)
            
            if matches:
                positive_prompt = matches[0].strip()
                if positive_prompt:
                    for blacklist_item in self.config.POSITIVE_PROMPT_BLACKLIST:
                        positive_prompt = positive_prompt.replace(blacklist_item, '')
                    
                    positive_prompt = re.sub(r',\s*,', ',', positive_prompt)
                    positive_prompt = positive_prompt.strip(', ')
                    
                    return positive_prompt
            
            return parameters
            
        except Exception as e:
            print(f"Error reading PNG metadata: {e}")
            return None