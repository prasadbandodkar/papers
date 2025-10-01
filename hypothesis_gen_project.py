# Code to fetch papers from pubmed central and convert them to txt format for 
# hypothesis generation project
#

import papers.entrez as entrez
import papers.converter as converter
import papers.files as files
def fetch_papers():
    ids = ["32792685",
           "4970894",
           "3913061",
           "34140290",
           "8230752"]
    
    e = entrez.Entrez()
    e.fetch(ids=ids, db="pmc", retmode="xml", rettype="xml", retry_failed=False)

def convert_papers():
    converter = converter.Converter()
    converter.convert(doc_type="paper", format="txt")

    

if __name__ == "__main__":
    pass
