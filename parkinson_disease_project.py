#%%
# Import libraries
#
import os
from papers.entrez import Entrez
from papers.converter import XMLConverter, HTMLConverter
from papers.files import Files

#%%
# Define parameters
#
date_start = "2010/01/01"
date_end   = "2024/12/31"
search_term = [{"search_term": "parkinson's disease", "location": ["Title", "Abstract"]},
               {"search_term": "parkinson disease", "location": ["Title", "Abstract"]},
               {"search_term": "parkinson", "location": ["Title", "Abstract"]}]
base_data_dir = "/mnt/c/Users/Prasad.Bandodkar/Biotechne/Data/entrez"
project_name = "parkinson_disease_project"
filetype     = "txt"
db           = "pmc"

#%%
# Search and fetch all papers in the date range
#
e = Entrez(config_file="config/nih.txt", base_data_dir = base_data_dir)
e.search(search_terms = search_term, db=db, condition="OR", date_range=(date_start, date_end), retmax=100)
print(e.search_results_file)


#%%
# Fetch papers
#
e.fetch(db=db, retmode="xml", rettype="xml", retry_failed=False)


#%%
# Process papers
#
xml_dir        = os.path.join(base_data_dir, db, "xml")
paper_dir      = os.path.join(base_data_dir, db, "txt")
author_dir     = os.path.join(base_data_dir, db, "authors")
references_dir = os.path.join(base_data_dir, db, "references")
converter = XMLConverter(xml_dir, paper_dir, author_dir, references_dir, filetype)
converter.convert_all(doc_type="paper_without_metadata", remove_existing = False)
converter.convert_all(doc_type="author", remove_existing = False)
converter.convert_all(doc_type="references", remove_existing = False)


#%%
# Copy processed docs
#
project_base_dir = os.path.join(base_data_dir, project_name)
txt_source_dir   = os.path.join(base_data_dir, db, "txt")
xml_source_dir   = os.path.join(base_data_dir, db, "xml")

#%%
# Create yearly directories and organize files by publication year using specific search results
#
from papers.doc import XmlToDoc
from pathlib import Path
import shutil

# Find the search results file
search_results_file = e.search_results_file
if not os.path.exists(search_results_file):
    raise FileNotFoundError(f"Could not find search results file: {search_results_file}")
else:
    ids_file_path = search_results_file
print(f"Using search results from: {ids_file_path}")

# Read the IDs from the file
with open(ids_file_path, "r") as f:
    target_ids = set(f.read().splitlines())
print(f"Found {len(target_ids)} IDs to process")


# Initialize yearly counters
yearly_counts = {}
total_processed = 0
total_copied = 0
errors = 0
not_found_xml = 0
not_found_txt = 0
year_start = int(date_start.split("/")[0])
year_end   = int(date_end.split("/")[0])

print("Organizing papers by publication year using specified IDs...")

# Process only XML files that match our target IDs
for pmc_id in target_ids:
    total_processed += 1
    
    try:
        # Construct XML file path
        xml_file_path = os.path.join(xml_source_dir, f"{db}_{pmc_id}.xml")
        
        if not os.path.exists(xml_file_path):
            not_found_xml += 1
            print(f"Warning: XML file not found for ID {pmc_id}")
            continue
        
        # Parse XML to get publication year
        doc = XmlToDoc(xml_file_path)
        pub_date = doc.get_publication_date()
        
        # Extract year from publication date
        if pub_date and "-" in pub_date:
            year = pub_date.split("-")[0]
        elif pub_date and len(pub_date) >= 4:
            year = pub_date[:4]
        else:
            print(f"Warning: Could not extract year from publication date '{pub_date}' for {pmc_id}")
            continue
            
        # Validate year is in our range
        try:
            year_int = int(year)
            if year_int < year_start or year_int > year_end:
                print(f"Skipping paper {pmc_id} - year {year} outside range {year_start}-{year_end}")
                continue
        except ValueError:
            print(f"Warning: Invalid year format '{year}' for {pmc_id}")
            continue
        
        # Create year directory if it doesn't exist
        year_dir = os.path.join(project_base_dir, year)
        os.makedirs(year_dir, exist_ok=True)
        
        # Check if corresponding txt file exists
        txt_file = os.path.join(txt_source_dir, f"{db}_{pmc_id}.txt")
        if os.path.exists(txt_file):
            # Copy txt file to year directory
            dest_file = os.path.join(year_dir, f"{db}_{pmc_id}.txt")
            shutil.copy2(txt_file, dest_file)
            
            # Update counters
            yearly_counts[year] = yearly_counts.get(year, 0) + 1
            total_copied += 1
            
            if total_processed % 100 == 0:
                print(f"Processed {total_processed}/{len(target_ids)} IDs, copied {total_copied} papers")
        else:
            not_found_txt += 1
            if total_processed <= 10:  # Only show first 10 warnings
                print(f"Warning: TXT file not found for {pmc_id}")
            
    except Exception as e:
        errors += 1
        print(f"Error processing ID {pmc_id}: {str(e)}")

# Print summary statistics
print("\n" + "="*60)
print("SUMMARY - Papers organized by publication year")
print("="*60)
print(f"Target IDs from search file: {len(target_ids)}")
print(f"IDs processed: {total_processed}")
print(f"Papers successfully copied: {total_copied}")
print(f"XML files not found: {not_found_xml}")
print(f"TXT files not found: {not_found_txt}")
print(f"Errors encountered: {errors}")
print("\nPapers per year:")
for year in sorted(yearly_counts.keys()):
    print(f"  {year}: {yearly_counts[year]} papers")
print(f"\nFiles organized in: {project_base_dir}")

# Use Files class to verify the copy operation
print("\nVerifying copied files using Files class...")
for year in sorted(yearly_counts.keys()):
    year_dir = os.path.join(project_base_dir, year)
    copied_files = len([f for f in os.listdir(year_dir) if f.endswith('.txt')])
    print(f"  {year}: {copied_files} files in directory")
    
    
    
# %%
# Classify papers of 2024 in monthly directories

def classify_papers_by_month(year_dir, xml_source_dir, db="pmc", copy_files=True):
    """
    Classify papers from a year directory into monthly subdirectories.
    
    Args:
        year_dir (str): Path to the year directory containing papers
        xml_source_dir (str): Path to the XML source directory
        db (str): Database name (default: "pmc")
        copy_files (bool): If True, copy files; if False, move files
    
    Returns:
        dict: Monthly counts of papers organized
    """
    from papers.doc import XmlToDoc
    import os
    import shutil
    from collections import defaultdict
    
    if not os.path.exists(year_dir):
        raise FileNotFoundError(f"Year directory not found: {year_dir}")
    
    # Initialize counters
    monthly_counts = defaultdict(int)
    total_processed = 0
    total_organized = 0
    errors = 0
    no_xml_found = 0
    no_date_found = 0
    
    # Get all txt files in the year directory
    txt_files = [f for f in os.listdir(year_dir) if f.endswith('.txt')]
    
    if not txt_files:
        print(f"No txt files found in {year_dir}")
        return {}
    
    print(f"Processing {len(txt_files)} papers from {os.path.basename(year_dir)}...")
    
    for txt_file in txt_files:
        total_processed += 1
        
        try:
            # Extract PMC ID from filename
            pmc_id = txt_file.replace(f"{db}_", "").replace(".txt", "")
            
            # Construct XML file path
            xml_file_path = os.path.join(xml_source_dir, f"{db}_{pmc_id}.xml")
            
            if not os.path.exists(xml_file_path):
                no_xml_found += 1
                print(f"Warning: XML file not found for {pmc_id}")
                continue
            
            # Parse XML to get publication date
            doc = XmlToDoc(xml_file_path)
            pub_date = doc.get_publication_date()
            
            if not pub_date:
                no_date_found += 1
                print(f"Warning: No publication date found for {pmc_id}")
                continue
            
            # Extract month from publication date
            month = None
            if "-" in pub_date and len(pub_date.split("-")) >= 2:
                # Format: YYYY-MM-DD or YYYY-MM
                month = pub_date.split("-")[1]
            elif len(pub_date) >= 6:
                # Format: YYYYMM or similar
                month = pub_date[4:6]
            
            if not month or not month.isdigit() or int(month) < 1 or int(month) > 12:
                no_date_found += 1
                print(f"Warning: Could not extract valid month from date '{pub_date}' for {pmc_id}")
                continue
            
            # Create month directory
            month_name = f"{month.zfill(2)}"  # Ensure 2-digit format (01, 02, etc.)
            month_dir = os.path.join(year_dir, month_name)
            os.makedirs(month_dir, exist_ok=True)
            
            # Move or copy the txt file to month directory
            source_file = os.path.join(year_dir, txt_file)
            dest_file = os.path.join(month_dir, txt_file)
            
            if copy_files:
                shutil.copy2(source_file, dest_file)
            else:
                shutil.move(source_file, dest_file)
            
            # Update counters
            monthly_counts[month_name] += 1
            total_organized += 1
            
            if total_processed % 50 == 0:
                print(f"Processed {total_processed}/{len(txt_files)} papers, organized {total_organized}")
                
        except Exception as e:
            errors += 1
            print(f"Error processing {txt_file}: {str(e)}")
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"SUMMARY - Papers organized by month in {os.path.basename(year_dir)}")
    print(f"{'='*50}")
    print(f"Total papers processed: {total_processed}")
    print(f"Papers successfully organized: {total_organized}")
    print(f"XML files not found: {no_xml_found}")
    print(f"Publication dates not found: {no_date_found}")
    print(f"Errors encountered: {errors}")
    
    if monthly_counts:
        print(f"\nPapers per month:")
        for month in sorted(monthly_counts.keys()):
            month_name = {
                "01": "January", "02": "February", "03": "March", "04": "April",
                "05": "May", "06": "June", "07": "July", "08": "August",
                "09": "September", "10": "October", "11": "November", "12": "December"
            }
            print(f"  {month} ({month_name.get(month, 'Unknown')}): {monthly_counts[month]} papers")
    
    return dict(monthly_counts)

# Example usage for 2024 papers:
def organize_2024_papers_by_month():
    """
    Organize 2024 papers into monthly directories.
    """
    year_2024_dir = os.path.join(project_base_dir, "2024")
    
    if os.path.exists(year_2024_dir):
        monthly_counts = classify_papers_by_month(
            year_dir=year_2024_dir,
            xml_source_dir=xml_source_dir,
            db=db,
            copy_files=False  # Set to True if you want to copy instead of move
        )
        return monthly_counts
    else:
        print(f"2024 directory not found: {year_2024_dir}")
        return {}

# You can also create a function to organize all years by month:
def organize_all_years_by_month():
    """
    Organize papers from all years into monthly directories.
    """
    all_results = {}
    
    # Get all year directories
    if os.path.exists(project_base_dir):
        year_dirs = [d for d in os.listdir(project_base_dir) 
                    if os.path.isdir(os.path.join(project_base_dir, d)) and d.isdigit()]
        
        for year in sorted(year_dirs):
            year_dir = os.path.join(project_base_dir, year)
            print(f"\nProcessing year {year}...")
            
            monthly_counts = classify_papers_by_month(
                year_dir=year_dir,
                xml_source_dir=xml_source_dir,
                db=db,
                copy_files=False
            )
            
            all_results[year] = monthly_counts
    
    return all_results

# Classify 2024 into respectve monthly directories
#
organize_2024_papers_by_month()

# %%