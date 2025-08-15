"""
Indexing Cache Manager for RAG Project

This module provides caching functionality to track which files have been indexed
and their modification times, allowing for incremental indexing.
"""

import os
import json
import logging
from pathlib import Path
from typing import Set, Tuple, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class IndexingCacheManager:
    """
    Manages a cache of indexed files to enable incremental indexing.
    Tracks file paths and their last modification times.
    """
    
    def __init__(self, cache_file: str = "scripts/.indexing_cache.json"):
        self.cache_file = cache_file
        self.cache_data = self._load_cache()
        
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache data from file."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"files": {}, "last_updated": None}
        except Exception as e:
            logger.warning(f"Failed to load cache file {self.cache_file}: {e}")
            return {"files": {}, "last_updated": None}
    
    def _save_cache(self):
        """Save cache data to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            self.cache_data["last_updated"] = datetime.now().isoformat()
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save cache file {self.cache_file}: {e}")
    
    def get_files_to_process(self, current_files: Set[str]) -> Tuple[Set[str], Set[str]]:
        """
        Determine which files need to be processed based on cache.
        
        Args:
            current_files: Set of file paths currently found in filesystem
            
        Returns:
            Tuple of (files_to_index, files_to_delete)
        """
        files_to_index = set()
        files_to_delete = set()
        
        cached_files = set(self.cache_data["files"].keys())
        
        # Check for new or modified files
        for file_path in current_files:
            try:
                current_mtime = os.path.getmtime(file_path)
                cached_mtime = self.cache_data["files"].get(file_path)
                
                if cached_mtime is None or current_mtime > cached_mtime:
                    files_to_index.add(file_path)
                    
            except OSError as e:
                logger.warning(f"Could not get modification time for {file_path}: {e}")
                files_to_index.add(file_path)  # Process it anyway
        
        # Check for deleted files
        files_to_delete = cached_files - current_files
        
        return files_to_index, files_to_delete
    
    def update_cache(self, processed_files: Set[str], deleted_files: Set[str]):
        """
        Update cache with newly processed and deleted files.
        
        Args:
            processed_files: Files that were successfully processed
            deleted_files: Files that were deleted from the index
        """
        # Update processed files with their current modification times
        for file_path in processed_files:
            try:
                if os.path.exists(file_path):
                    self.cache_data["files"][file_path] = os.path.getmtime(file_path)
            except OSError as e:
                logger.warning(f"Could not get modification time for {file_path}: {e}")
        
        # Remove deleted files from cache
        for file_path in deleted_files:
            self.cache_data["files"].pop(file_path, None)
        
        self._save_cache()
    
    def clear_cache(self):
        """Clear all cache data."""
        self.cache_data = {"files": {}, "last_updated": None}
        self._save_cache()
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        return {
            "total_files": len(self.cache_data["files"]),
            "last_updated": self.cache_data.get("last_updated"),
            "cache_file": self.cache_file
        }
    
    def get_cached_files(self) -> Set[str]:
        """Get the set of all files currently in cache."""
        return set(self.cache_data["files"].keys())
