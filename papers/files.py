"""
A class to search for a specific term in a text file and copy the matching files to a destination directory.
Also contains other related functions.
"""

import shutil
from pathlib import Path
import re
from typing import List

class Files:
    def __init__(self, source_dir: str, dest_dir: str, db: str = "pmc"):
        self.source_dir   = source_dir
        self.dest_dir     = dest_dir
        self.db           = db



    def search_and_copy_files(self, search_terms: List[str] = [], doc_type: str = "txt"):
        """
        Search through text files for a specific term and copy matching files to destination.
    
        Args:
            source_dir: Directory containing text files to search
            dest_dir: Directory to copy matching files to
            search_term: Term to search for (case insensitive)
            doc_type: Type of document to search for (txt, xml, etc.). Only txt files are supported currently.
        """
        # Create destination directory if it doesn't exist
        Path(self.dest_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize counters
        total_files = 0
        matching_files = 0
        total_matches = 0
        
        # Compile regex pattern for case-insensitive search
        patterns = [re.compile(term, re.IGNORECASE) for term in search_terms]
        
        # Process all .txt files
        for txt_file in Path(self.source_dir).glob(f"*.{doc_type}"):
            total_files += 1
            try:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = [pattern.findall(content) for pattern in patterns]
                    
                    # Check if any of the pattern lists contain matches
                    has_matches = any(len(match_list) > 0 for match_list in matches)
                    
                    if has_matches:
                        # Copy file to destination
                        shutil.copy2(txt_file, self.dest_dir)
                        matching_files += 1
                        total_matches += len(matches)
                        print(f"Found {len(matches)} matches in: {txt_file.name}")
                        
            except Exception as e:
                print(f"Error processing {txt_file}: {str(e)}")
        
        # Print statistics
        print("\nSearch Results:")
        print("=" * 50)
        print(f"Total files processed: {total_files}")
        print(f"Files containing matches: {matching_files}")
        print(f"Total occurrences found: {total_matches}")
        print(f"Matching files copied to: {self.dest_dir}")


    def copy_files(self, ids: list = [], doc_type: str = "txt"):
        """
        Copy all files from source directory to destination directory.
        Note that the files are named as {db}_{id}.{doc_type} ex: pmc_32792685.txt
        
        Args:
            ids: List of PMC IDs to copy
        """
        for id in ids:
            file = Path(self.source_dir) / f"{self.db}_{id}.{doc_type}"
            if not file.exists():
                print(f"File {file.name} does not exist")
                ids.remove(id)
                continue
            shutil.copy2(file, self.dest_dir)

