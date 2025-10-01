import os
from pathlib import Path
from papers.doc import XmlToDoc, Html2Doc
from typing import List, Set
import time

class XMLConverter:
    """Convert all PMC XML files in a directory to text or JSON format."""
    
    def __init__(self, 
                 xml_dir: str, 
                 paper_dir: str = None, 
                 author_dir: str = None, 
                 references_dir: str = None, 
                 format: str = "txt"):
        """
        Initialize with source and destination directories.
        
        Args:
            xml_dir: Path to directory containing XML files
            txt_dir: Path to directory where text files will be saved
            author_dir: Path to directory where author files will be saved
            references_dir: Path to directory where references files will be saved
            format: format of the output files
        """
        self.xml_dir        = Path(xml_dir)
        self.paper_dir      = Path(paper_dir)
        self.author_dir     = Path(author_dir)
        self.references_dir = Path(references_dir)
        self.format         = format
        
        # Create output directories if they don't exist
        self.paper_dir.mkdir(parents=True, exist_ok=True)
        self.author_dir.mkdir(parents=True, exist_ok=True)
        self.references_dir.mkdir(parents=True, exist_ok=True)
    
    
    def _get_pending_files(self, remove_existing: bool = False, doc_type: str = "paper") -> List[Path]:
        """Get list of XML files that need to be converted."""
        xml_files = list(self.xml_dir.glob("*.xml"))
        if doc_type == "paper":
            output_dir = self.paper_dir
        elif doc_type == "author":
            output_dir = self.author_dir
        elif doc_type == "references":
            output_dir = self.references_dir
        
        if remove_existing:
            # Delete all files with matching format in output directory
            file_pattern = f"*.{self.format}"
            for file in output_dir.glob(file_pattern):
                file.unlink()
            return xml_files
        
        # OPTIMIZATION 1: Build a set of existing output filenames (without extension)
        # This changes O(n²) lookups to O(n) lookups
        existing_stems: Set[str] = {
            f.stem for f in output_dir.glob(f"*.{self.format}")
        }
        
        # OPTIMIZATION 2: Use list comprehension instead of loop + append
        pending_files = [
            xml_file for xml_file in xml_files 
            if xml_file.stem not in existing_stems
        ]
        
        # print how many files are converted out of total
        print(f"Already converted {len(xml_files) - len(pending_files)}/{len(xml_files)} files")
            
        return pending_files
    
    
    def convert_all(self, verbose: bool = True, doc_type: str = "paper_without_metadata", remove_existing: bool = False):
        """Convert all pending XML files to text format."""
        if doc_type == "paper_with_metadata" or doc_type == "paper_without_metadata" or doc_type == "paper":
            doc_type_check = "paper"
        else:
            doc_type_check = doc_type
        
        pending_files = self._get_pending_files(remove_existing=remove_existing, doc_type=doc_type_check)
        total_files = len(pending_files)
        
        if verbose:
            print(f"Found {total_files} files to convert")
        
        start_time = time.time()
        
        for i, xml_file in enumerate(pending_files, 1):
            if verbose:
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                # Calculate progress metrics
                progress = i / total_files
                if progress > 0:
                    eta = elapsed_time / progress - elapsed_time
                    eta_str = f"{int(eta // 60)}m {int(eta % 60)}s"
                else:
                    eta_str = "calculating..."
                
                # Format elapsed time string
                elapsed_str = f"{int(elapsed_time // 60)}m {int(elapsed_time % 60)}s"
                
                # Create progress bar
                bar_length = 30
                arrow = '=' * int(round(progress * bar_length) - 1) + '>'
                spaces = ' ' * (bar_length - len(arrow))
                progress_text = f"\r[{arrow}{spaces}] {i}/{total_files} ({progress:.1%}) | Time: {elapsed_str} | ETA: {eta_str}"
                
                # Print progress bar (overwrite same line)
                print(progress_text, end='', flush=True)
            
            try:
                # Convert file
                xml_converter = XmlToDoc(str(xml_file))
                if doc_type == "paper" or doc_type == "paper_with_metadata" or doc_type == "paper_without_metadata":
                    filename = self.paper_dir / f"{xml_file.stem}.{self.format}"
                elif doc_type == "author":
                    filename = self.author_dir / f"{xml_file.stem}.{self.format}"
                elif doc_type == "references":  
                    filename = self.references_dir / f"{xml_file.stem}.{self.format}"
                xml_converter.save_to_file(str(filename), doc_type=doc_type, format=self.format)
                
            except Exception as e:
                print(f"\nError converting {xml_file.name}: {str(e)}")
        
        # Print final newline after progress bar
        if verbose:
            print()
            
        total_time = time.time() - start_time
        
        if verbose:
            print(f"\nConversion complete!")
            print(f"Total time: {total_time:.1f} seconds")
            print(f"Average time per file: {total_time/(total_files + 1):.1f} seconds")
            


class HTMLConverter:
    """Convert all HTML files in a directory to text or JSON format."""
    
    def __init__(self, html_dir: str, txt_dir: str, format: str = "txt"):
        self.html_dir = Path(html_dir)
        self.txt_dir = Path(txt_dir)
        self.format = format
    
    def convert(self):
        pass


def main():
    # Example usage
    xml_dir = "C:\\Users\\Prasad.Bandodkar\\Biotechne\\Data\\entrez\\pmc\\xml"
    paper_dir = "C:\\Users\\Prasad.Bandodkar\\Biotechne\\Data\\entrez\\pmc\\txt"
    author_dir = "C:\\Users\\Prasad.Bandodkar\\Biotechne\\Data\\entrez\\pmc\\authors"
    references_dir = "C:\\Users\\Prasad.Bandodkar\\Biotechne\\Data\\entrez\\pmc\\references"

    converter = XMLConverter(xml_dir=xml_dir, paper_dir=paper_dir, author_dir=author_dir, references_dir=references_dir, format="txt")
    converter.convert_all(verbose=True, doc_type="paper_without_metadata", remove_existing=False)
    converter.convert_all(verbose=True, doc_type="author", remove_existing=False)
    converter.convert_all(verbose=True, doc_type="references", remove_existing=False)
    

if __name__ == "__main__":
    main()