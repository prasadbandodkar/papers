'''
Class to use Entrez API to search and get data from PubMed / PMC etc.
'''

from math import inf
import re
import requests
import xml.etree.ElementTree as ET
import os, time, hashlib
from papers.functions import Functions
from typing import List, Tuple, Dict, Union

class Entrez:
    def __init__(self, config_file: str = None, base_data_dir: str = None):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.base_data_dir = base_data_dir
        self.api_key = None
        if config_file is not None:
            with open(config_file, "r") as f:
                line = f.readline().strip()
                self.api_key = line.split('=')[1]
        
        self.search_term            = None
        self.sanitized_search_term  = None
        self.search_results_file    = None
        self.ids                    = None
        
        
    def entrez(self, util, db="pmc", **kwargs):
        """
        Use Entrez API to search and get data from PubMed / PMC etc.
        """
        params = {
            "db": db,
            "api_key": self.api_key,
            **kwargs
        }
        response = requests.get(f"{self.base_url}{util}.fcgi", params=params)
        response.raise_for_status()
        return response.text


    def chunk_list(self, lst, chunk_size):
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
    
    
    def get_ids_from_search_file(self, filepath, restart=False):
        all_ids = []
        if os.path.exists(filepath):
            if not restart:
                try:
                    with open(filepath, "r") as f:
                        all_ids = f.read().splitlines()
                        retstart = len(all_ids)
                        print(f"Search: Found {retstart} existing IDs")
                except Exception as e:
                    print(f"Warning: Could not read existing IDs file: {str(e)}")
                    print("Starting search from beginning")
                    all_ids  = []
                    retstart = 0
            else:
                os.remove(filepath)
                print("Removed existing IDs file")
        return all_ids
    
    
    def _build_search_term(self, search_terms: List[Dict[str, Union[str, List[str]]]] = [], condition: str = "AND", date_range: Tuple[str, str] = None):
        """
        Build a search term from a list of dictionaries with search_term and location.
        Each dictionary should have format {"search_term": "term", "location": ["field1", "field2"]}.
        Example: [{"search_term": "Parkinson", "location": ["Title", "Abstract"]}]
        Terms are combined with the specified condition.
        """
        formatted_terms = []
        for term_dict in search_terms:
            search_term = term_dict.get("search_term", "")
            locations = term_dict.get("location", [])
            
            # Handle locations as a list
            if search_term and locations:
                if isinstance(locations, str):
                    locations = [locations]  # Convert single string to list
                
                location_terms = []
                for location in locations:
                    location_terms.append(f"{search_term}[{location.upper()}]")
                
                # Join multiple locations with OR
                if len(location_terms) > 1:
                    formatted_terms.append(f"({' OR '.join(location_terms)})")
                elif len(location_terms) == 1:
                    formatted_terms.append(location_terms[0])
        
        # Join the formatted terms with the condition
        if len(formatted_terms) > 1:
            term = f"({formatted_terms[0]}"
            for i in range(1, len(formatted_terms)):
                term += f" {condition} {formatted_terms[i]}"
            term += ")"
        elif len(formatted_terms) == 1:
            term = formatted_terms[0]
        else:
            term = ""
            
        # Add date range if provided
        if date_range and term:
            term = f"{term} AND {date_range[0]}:{date_range[1]}[pdat]"
        
        return term
    
    
    def search(self, search_terms: List[Dict[str, Union[str, List[str]]]] = [], db="pmc", condition: str = "AND", search_dir = None, retmax=1000, date_range=None, restart=False, max_retries=3, timeout=30, **kwargs):
        """
        Search PubMed/PMC database and retrieve article IDs matching the search criteria.

        Args:
            term (str): Search query string.
            retmax (int, optional): Maximum number of results to retrieve per request. Defaults to 100.
            date_range (tuple, optional): Tuple of (start_date, end_date) in format 'YYYY/MM/DD'. 
                                        Example: ('2020/01/01', '2023/12/31'). Defaults to None.
            restart (bool, optional): If True, starts a new search. If False, continues from last ID. Defaults to False.
            max_retries (int, optional): Maximum number of retries for failed requests. Defaults to 3.
            timeout (int, optional): Timeout for requests in seconds. Defaults to 30.
            **kwargs: Additional keywords arguments to pass to the Entrez API.

        Returns:
            list: List of PubMed/PMC article IDs matching the search criteria.

        Raises:
            ValueError: If date_range format is invalid.
            ConnectionError: If unable to connect to NCBI servers after max_retries.
        """
        all_ids        = []
        retstart       = 0
        
        # Modify term to include date range if provided
        term = self._build_search_term(search_terms, condition, date_range)
        print(f"Search: Term = {term}")
        self.search_term = term
        self.sanitized_search_term = Functions.get_sanitized_filename(term)
        
        # Ensure search directory exists
        if search_dir is None:
            search_dir = os.path.join(self.base_data_dir, "search")
        os.makedirs(search_dir, exist_ok=True)
        
        # Create path with sanitized filename
        filepath = os.path.join(search_dir, f"{self.sanitized_search_term}_ids.txt")
        print(f"Search: Filepath = {filepath}") 
        
        # Get any existing IDs from the search file
        all_ids = self.get_ids_from_search_file(filepath, restart)
        retstart = len(all_ids)
        print(f"Search: Retstart = {retstart}")
        
        # Get total count of results
        count_elem = None
        total_papers = 0
        try:
            initial_search = self.entrez("esearch", db=db, term=term, retstart=0, retmax=1, **kwargs)
            root = ET.fromstring(initial_search)
            count_elem = root.find("Count")
            total_papers = int(count_elem.text) if count_elem is not None else 0
            print(f"Search: Total papers from NCBI = {total_papers}")
        except Exception as e:
            print(f"Error retrieving total count: {str(e)}")
            return all_ids
        
        # Exit if there are no results
        if total_papers == 0:
            print("Search: No results found")
            return all_ids
        
                # Initialize variables
        web_env = None
        query_key = None
        chunk_size = 5000
        consecutive_failures = 0
        max_failures = 3

        # Main search loop with proper exit conditions
        while retstart < total_papers:
            try:
                # Calculate effective position for this request
                effective_position = retstart
                
                # If we're resuming from a large offset, use direct retrieval instead of skipping
                if retstart >= 10000:
                    # Skip the WebEnv approach for large offsets and use direct retrieval
                    print(f"Direct retrieval at position {retstart}")
                    search_results = self.entrez("esearch", db=db, term=term, retstart=retstart, 
                                               retmax=chunk_size, **kwargs)
                    root = ET.fromstring(search_results)
                else:
                    # Use WebEnv approach for smaller offsets
                    if web_env is None:
                        print(f"Starting new search session at position {retstart}")
                        search_results = self.entrez("esearch", db=db, term=term, retstart=retstart, 
                                                   retmax=chunk_size, usehistory="y", **kwargs)
                        root = ET.fromstring(search_results)
                        
                        web_env_elem = root.find("WebEnv")
                        query_key_elem = root.find("QueryKey")
                        
                        if web_env_elem is not None and query_key_elem is not None:
                            web_env = web_env_elem.text
                            query_key = query_key_elem.text
                        else:
                            # Fall back to regular search if WebEnv not available
                            search_results = self.entrez("esearch", db=db, term=term, retstart=retstart, 
                                                      retmax=chunk_size, **kwargs)
                            root = ET.fromstring(search_results)
                    else:
                        # Use WebEnv for subsequent requests
                        search_results = self.entrez("esearch", db=db, term=term, retstart=retstart, 
                                                   retmax=chunk_size, usehistory="y", 
                                                   WebEnv=web_env, query_key=query_key, **kwargs)
                        root = ET.fromstring(search_results)
                
                # Extract IDs
                ids = [id.text for id in root.iter("Id")]
                
                # Check if we got valid results
                if not ids:
                    consecutive_failures += 1
                    print(f"Warning: No IDs retrieved at position {retstart}. Attempt {consecutive_failures}/{max_failures}.")
                    
                    if consecutive_failures >= max_failures:
                        print(f"Changing strategy after {consecutive_failures} consecutive failures")
                        web_env = None  # Reset WebEnv to try different approach
                        
                        # If we were using WebEnv and failed, switch to direct retrieval
                        if retstart < 10000:
                            print("Switching to direct retrieval strategy")
                            retstart = effective_position  # Make sure we're at the right position
                        else:
                            # If direct retrieval is also failing, try a smaller chunk size
                            chunk_size = max(100, chunk_size // 2)
                            print(f"Reducing chunk size to {chunk_size}")
                        
                        consecutive_failures = 0
                    
                    time.sleep(3)  # Wait longer before retrying
                    continue
                
                consecutive_failures = 0  # Reset failure counter on success
                all_ids.extend(ids)
                
                # Write the resulting IDs to a text file
                with open(filepath, "a") as f:
                    for id in ids:
                        f.write(f"{id}\n")
                
                # Update retstart for next iteration and print progress
                retstart += len(ids)  # Use actual number of IDs retrieved
                print(f"Search: Retrieved {len(all_ids)}/{total_papers} papers")
                
                # Respect NCBI's rate limits
                time.sleep(1.1)
                
            except Exception as e:
                print(f"Error during search: {str(e)}")
                consecutive_failures += 1
                
                if consecutive_failures >= max_failures:
                    print("Changing strategy after exception")
                    web_env = None
                    consecutive_failures = 0
                    
                    # Try with a smaller chunk size
                    chunk_size = max(100, chunk_size // 2)
                    print(f"Reducing chunk size to {chunk_size}")
                
                time.sleep(5)  # Simple retry delay
    
        # Store the results
        self.ids                 = all_ids
        self.search_results_file = filepath
        
        print(f"\nSearch complete: Retrieved {len(all_ids)} IDs")
        return self.ids
    
    
    def fetch(self, fetch_dir = None, ids = [], db="pubmed", retry_failed=False, retmode="xml", **kwargs):
        """
        Fetch papers from PubMed/PMC database and save them to the data directory.
        """
        # Get IDs to fetch
        #
        if len(ids) == 0:
            if self.search_results_file is None:
                raise ValueError("No search results file or ids provided. Please run a search first.")
            else:
                with open(self.search_results_file, "r") as f:
                    ids = f.read().splitlines()
        total_papers = len(ids)
        if total_papers == 0:
            raise ValueError("No papers to fetch. Please run a search first.")
        
        
        # Get fetch directory
        #
        if fetch_dir is None:
            fetch_dir = os.path.join(self.base_data_dir, db, retmode)
        os.makedirs(fetch_dir, exist_ok=True)
        
        
        # Failed IDs
        #
        if self.sanitized_search_term is None:
            name = "_".join(ids[:10])
        else: 
            name = self.sanitized_search_term
        failed_ids_file = Functions.get_tempfile(f"{name}_failed_ids")
        if os.path.exists(failed_ids_file):
            with open(failed_ids_file, "r") as f:
                failed_ids = set(f.read().splitlines())
        else:
            failed_ids = set()
        print(f"Fetch: Failed IDs file = {failed_ids_file}")
        
        
        # Determine which IDs to fetch
        #
        downloaded_files = set(os.listdir(fetch_dir))
        downloaded_ids = {file.split('.')[0].replace(f'{db}_', '') for file in downloaded_files if file.endswith(f'.{retmode}')}
        if retry_failed:
            ids_to_fetch = [id for id in ids if (id in failed_ids and id not in downloaded_ids)]
        else:
            ids_to_fetch = [id for id in ids if id not in downloaded_ids and id not in failed_ids]
            
        # Process in batches
        #
        batch_size = 100
        batched_ids = self.chunk_list(ids_to_fetch, batch_size)
        start_time = time.time()
        papers_processed = 0
        total_to_fetch = len(ids_to_fetch)
        

        # Run the loop
        #
        bar_length = 30  # Length of the progress bar
        print(f"Fetching {total_to_fetch} papers from {db}...")
        for batch in batched_ids:
            for id in batch:
                try:
                    fetch_results = self.entrez("efetch", db=db, id=id, retmode=retmode, **kwargs)
                    
                    # Save the result
                    filepath = os.path.join(fetch_dir, f"{db}_{id}.{retmode}")
                    with open(filepath, "wb") as f:
                        f.write(fetch_results.encode())
                    
                    # If retrying and successful, remove from failed_ids
                    if retry_failed and id in failed_ids:
                        failed_ids.remove(id)
                    
                except Exception as e:
                    failed_ids.add(id)
                    continue
                
                papers_processed += 1
                
                # Update progress bar for each paper
                if total_to_fetch > 0: 
                    progress     = papers_processed / total_to_fetch
                    current_time = time.time()
                    elapsed      = current_time - start_time
                    if progress > 0:
                        eta = elapsed / progress - elapsed
                        eta_str = f"{int(eta // 60)}m {int(eta % 60)}s"
                    else:
                        eta_str = "calculating..."
                
                    # Create the progress text with elapsed time and ETA
                    elapsed_str   = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
                    arrow         = '=' * int(round(progress * bar_length) - 1) + '>'
                    spaces        = ' ' * (bar_length - len(arrow))
                    progress_text = f"[{arrow}{spaces}] {papers_processed}/{total_to_fetch} ({progress:.1%}) | Time: {elapsed_str} | ETA: {eta_str}"
                    
                    # Print the progress bar (overwrite the same line)
                    print(f"\r{progress_text}", end='', flush=True)
                
                # Respect the API rate limit (10 requests per second)
                if papers_processed % 10 == 0:
                    time.sleep(1.1)  # Slightly more than 1 second to be safe
            
            # Update the failed IDs file after each batch for persistence
            if failed_ids:
                with open(failed_ids_file, "w") as f:
                    for failed_id in failed_ids:
                        f.write(f"{failed_id}\n")
        
        # Final newline after progress bar
        print()
        
        # Print summary and list of failed IDs
        print(f"\nFetch completed: {papers_processed}/{total_to_fetch} papers downloaded")
        
        if failed_ids:
            print(f"\n{len(failed_ids)} papers failed to download:")
            for failed_id in sorted(failed_ids):
                print(f"- {failed_id}")
        else:
            print("\nAll papers downloaded successfully!")
        
        return papers_processed


def main():
    e = Entrez(base_data_dir="C:\\Users\\Prasad.Bandodkar\\Biotechne\\Data\\entrez")
    search_term = "(Parkinson's disease[Title] OR Parkinson's disease[Abstract]"
    search_term += " OR Parkinson disease[Title] OR Parkinson disease[Abstract]"
    search_term += " OR Parkinson[Title] OR Parkinson[Abstract])"
    e.search(search_term, db="pmc", retmax=1000, date_range=("2010/01/01", "2020/12/31"), restart=False)
    # e.search(search_term, db="pmc", retmax=1000, date_range=("2021/01/01", "2024/12/31"), restart=False)
    print(e.search_results_file)
    e.fetch(db="pmc", retmode="xml", rettype="xml", retry_failed=True)
    

def hypothesis_gen_project():
    e = Entrez()
    search_term = "MicroRNA MIR21 (miR-21) and PTGS2 Expression in Colorectal Cancer and Patient Survival "
    e.search(search_term, db="pmc", retmax=1000, restart=False)
    # e.search(search_term, db="pmc", retmax=1000, date_range=("2021/01/01", "2024/12/31"), restart=False)
    print(e.search_results_file)
    e.fetch(db="pmc", retmode="xml", rettype="xml", retry_failed=False)

if __name__ == "__main__":
    hypothesis_gen_project()