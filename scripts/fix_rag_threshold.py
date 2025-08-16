#!/usr/bin/env python3
"""
RAG System Quick Fix Script

This script implements the immediate fix for document retrieval issues by:
1. Modifying the score_threshold in the query processor
2. Creating a patch file with the changes

Usage:
    python scripts/fix_rag_threshold.py
"""

import os
import sys
import logging
import re
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

def create_processor_patch():
    """Create a patch for the query processor to fix the threshold."""
    
    query_processor_path = Path("backend/enhanced_query_processor.py")
    
    if not query_processor_path.exists():
        logger.error(f"File not found: {query_processor_path}")
        return False
    
    # Read the current file
    content = query_processor_path.read_text(encoding="utf-8")
    
    # Find the search threshold
    search_pattern = r"(score_threshold=)(0\.\d+)"
    match = re.search(search_pattern, content)
    
    if not match:
        logger.error("Could not find score_threshold parameter in the file")
        return False
    
    current_threshold = match.group(2)
    logger.info(f"Found current threshold: {current_threshold}")
    
    # Create backup file
    backup_path = query_processor_path.with_suffix(".py.bak")
    logger.info(f"Creating backup at {backup_path}")
    backup_path.write_text(content, encoding="utf-8")
    
    # Replace the threshold
    new_threshold = "0.3"
    new_content = content.replace(
        f"score_threshold={current_threshold}",
        f"score_threshold={new_threshold}"
    )
    
    # Write the modified file
    query_processor_path.write_text(new_content, encoding="utf-8")
    logger.info(f"Updated score_threshold from {current_threshold} to {new_threshold}")
    
    # Create patch content
    patch_content = f"""
# RAG System Quick Fix - Applied on {Path(__file__).stat().st_mtime}

## Issue
The RAG system was not returning document results for queries. The diagnostic tests 
showed that the similarity threshold was too high, resulting in no documents being 
returned even though 995 documents exist in the vector database.

## Changes Made
1. Lowered the score_threshold in enhanced_query_processor.py:
   - Before: score_threshold={current_threshold}
   - After: score_threshold={new_threshold}

## How to Test
1. Ensure you're not using FAKE_SERVICES mode when testing:
   ```
   cd C:\\Users\\elabi\\Rag-project-test\\rag-project 
   .\\venv\\Scripts\\Activate.ps1
   uvicorn backend.main:app --reload --port 8000
   ```

2. Use curl to test if the system returns results:
   ```
   curl -X POST "http://localhost:8000/ask" -H "Content-Type: application/json" -d '{{"question": "What are the energy requirements?", "session_id": "test-session"}}'
   ```

3. Check the frontend response at: http://localhost:8502

## Additional Recommendations
1. Review document chunking strategy in ingest_data.py
2. Consider re-indexing documents to ensure proper processing:
   ```
   python scripts/ingest_data.py --rescan
   ```
3. Verify that embeddings model parameters match between indexing and querying
"""
    
    # Write patch notes
    patch_path = Path("scripts/RAG_SYSTEM_FIX.md")
    patch_path.write_text(patch_content, encoding="utf-8")
    logger.info(f"Patch notes saved to {patch_path}")
    
    return True

def main():
    """Main function to apply the quick fix."""
    logger.info("🔧 Applying RAG system quick fix...")
    
    success = create_processor_patch()
    
    if success:
        print("\n✅ RAG System Fix Applied Successfully!")
        print("\nThe score_threshold has been lowered in the query processor.")
        print("This should allow documents to be retrieved during search.")
        
        print("\n⚠️ IMPORTANT: Do not use FAKE_SERVICES mode when testing this fix.")
        print("Run the server without the fake services environment variable:")
        print("cd C:\\Users\\elabi\\Rag-project-test\\rag-project && .\\venv\\Scripts\\Activate.ps1 && uvicorn backend.main:app --reload --port 8000")
        
        print("\nDetailed information has been saved to scripts/RAG_SYSTEM_FIX.md")
    else:
        print("\n❌ Failed to apply the fix. See log for details.")

if __name__ == "__main__":
    main()
