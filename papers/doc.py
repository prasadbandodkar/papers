# A class to convert a pubmed central (PMC) xml document to txt format
#

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import re

class XmlToDoc:
    """A class to convert PubMed Central XML documents to text."""
    
    def __init__(self, xml_path: str):
        """Initialize with path to XML file."""
        self.tree = ET.parse(xml_path)
        self.root = self.tree.getroot()
        
    def _get_text_from_element(self, elem: Optional[ET.Element]) -> str:
        """Extract text from an element, preserving whitespace."""
        if elem is None:
            return ""
        
        # Convert element to string with proper spacing
        text = "".join(elem.itertext()).strip()
        
        # Clean up extra whitespace while preserving single spaces
        text = " ".join(text.split())
        
        return text
    
    
    
    # journal, publication date, pmc id
    #
    def get_journal_name(self) -> str:
        """Extract journal name."""
        journal_elem = self.root.find(".//journal-title")
        return journal_elem.text if journal_elem is not None else ""

    def get_publication_date(self) -> str:
        """Extract publication date."""
        pub_date = self.root.find(".//pub-date")
        if pub_date is not None:
            year = pub_date.find("year")
            month = pub_date.find("month")
            day = pub_date.find("day")
            
            date_parts = []
            if year is not None:
                date_parts.append(year.text)
            if month is not None:
                date_parts.append(month.text)
            if day is not None:
                date_parts.append(day.text)
            
            return "-".join(date_parts)
        return ""

    def get_pmc_id(self) -> str:
        """Extract PMC ID."""
        pmc_elem = self.root.find(".//article-id[@pub-id-type='pmc']")
        return pmc_elem.text if pmc_elem is not None else ""
    
    
    
    # author info
    #
    def get_author_info(self) -> List[Dict]:
        """
        Extract author information including names, affiliations, and email addresses.
        Returns a list of dictionaries containing author details.
        """
        authors = []
        
        # First get all corresponding author info from author-notes
        corresp_info = {}
        for corresp in self.root.findall(".//author-notes/corresp"):
            # Get the ID (e.g., CR1) and email
            corresp_id = corresp.get('id')
            email_elem = corresp.find(".//email")
            if corresp_id is not None and email_elem is not None:
                corresp_info[corresp_id] = email_elem.text
        
        # Find all author contributions
        for contrib in self.root.findall(".//contrib[@contrib-type='author']"):
            author_info = {}
            
            # Get name
            name_elem = contrib.find(".//name")
            if name_elem is not None:
                surname = name_elem.find("surname")
                given_names = name_elem.find("given-names")
                author_info["name"] = f"{given_names.text if given_names is not None else ''} {surname.text if surname is not None else ''}".strip()
            
            # Get affiliations
            affiliation_refs = contrib.findall(".//xref[@ref-type='aff']")
            affiliations = []
            for aff_ref in affiliation_refs:
                aff_id = aff_ref.get("rid")
                if aff_id:
                    # Find corresponding affiliation
                    aff_elem = self.root.find(f".//aff[@id='{aff_id}']")
                    if aff_elem is not None:
                        aff_text = self._get_text_from_element(aff_elem)
                        affiliations.append(aff_text)
            author_info["affiliations"] = affiliations
            
            # Check for corresponding author references
            for xref in contrib.findall(".//xref[@ref-type='corresp']"):
                ref_id = xref.get('rid')
                if ref_id in corresp_info:
                    author_info["email"] = corresp_info[ref_id]
                    author_info["is_corresponding"] = True
                    break
            else:
                # If not a corresponding author, check for direct email
                email_elem = contrib.find(".//email")
                author_info["email"] = email_elem.text if email_elem is not None else None
                author_info["is_corresponding"] = False
            
            # Get ORCID if available
            orcid_elem = contrib.find(".//contrib-id[@contrib-id-type='orcid']")
            if orcid_elem is not None:
                author_info["orcid"] = orcid_elem.text
                
            authors.append(author_info)
        
        return authors
    
    def get_authors(self) -> str:
        """Get author information as readable text."""
        authors = self.get_author_info()
        
        text_parts = []
        
        # First list all authors
        for i, author in enumerate(authors, 1):
            text_parts.append(f"Author {i}:")
            text_parts.append(f"Name: {author.get('name', 'N/A')}")
            
            if author.get('affiliations'):
                text_parts.append("Affiliations:")
                for aff in author['affiliations']:
                    text_parts.append(f"  - {aff}")
            
            if author.get('email'):
                text_parts.append(f"Email: {author['email']}")
            
            if author.get('orcid'):
                text_parts.append(f"ORCID: {author['orcid']}")
            
            if author.get('is_corresponding'):
                text_parts.append("(Corresponding Author)")
            
            text_parts.append("")
        
        return "\n".join(text_parts)
    
    def authors_to_text(self) -> str:
        """Convert author information to text format with metadata."""
        parts = []
        
        # Get PMC ID
        pmc_id = self.get_pmc_id()
        if pmc_id:
            parts.extend(["PMC ID", "=" * 6, f"PMC{pmc_id}", "\n"])
        
        # Get title
        title = self.get_title()
        if title:
            parts.extend(["TITLE", "=" * 5, title, "\n"])
        
        # Get journal name
        journal = self.get_journal_name()
        if journal:
            parts.extend(["JOURNAL", "=" * 7, journal, "\n"])
        
        # Get publication date
        pub_date = self.get_publication_date()
        if pub_date:
            parts.extend(["PUBLICATION DATE", "=" * 15, pub_date, "\n"])
        
        # Get author information
        authors = self.get_authors()
        if authors:
            parts.extend(["AUTHORS", "=" * 7, authors, "\n"])
        
        return "\n".join(parts)
    
    
    
    # main paper info
    #    
    def get_title(self) -> str:
        """Extract article title."""
        title_elem = self.root.find(".//article-title")
        return title_elem.text if title_elem is not None else ""
    
    def get_abstract(self) -> str:
        """Extract abstract text."""
        abstract_parts = []
        for abstract in self.root.findall(".//abstract"):
            for p in abstract.findall(".//p"):
                abstract_parts.append(self._get_text_from_element(p))
        return "\n".join(abstract_parts)
    
    def get_body(self) -> Dict[str, str]:
        """Extract body text organized by sections."""
        sections = {}
        
        # Find all sections in the body
        body = self.root.find(".//body")
        if body is None:
            return sections
            
        for sec in body.findall(".//sec"):
            # Get section title
            title = sec.find("title")
            section_title = self._get_text_from_element(title) if title is not None else "Untitled Section"
            
            # Get all paragraphs in this section, excluding those in nested tables
            paragraphs = []
            for p in sec.findall("p"):  # Direct paragraphs only, not those in tables
                text = self._get_text_from_element(p)
                if text.strip():
                    paragraphs.append(text.strip())
            
            # Only add sections with content
            if paragraphs:
                if section_title in sections:
                    # If section exists, append new paragraphs
                    sections[section_title] += "\n" + "\n".join(paragraphs)
                else:
                    sections[section_title] = "\n".join(paragraphs)
        
        return sections



    # references
    #
    def get_references(self) -> List[tuple]:
        """
        Extract references with their components.
        Returns list of tuples: (index, pmid, authors, title, journal, year)
        """
        references = []
        ref_list = self.root.find(".//ref-list")
        
        if ref_list is None:
            return references
            
        for index, ref in enumerate(ref_list.findall("ref")):
  
            # Get citation
            citation = ref.find(".//element-citation") or ref.find(".//mixed-citation")
            
            if citation is not None:
                # Get PMID if available
                pmid_elem = citation.find(".//pub-id[@pub-id-type='pmid']")
                pmid = pmid_elem.text if pmid_elem is not None else "N/A"
                
                # Get authors
                authors = []
                person_group = citation.find(".//person-group")
                if person_group is not None:
                    for name in person_group.findall(".//name"):
                        surname = name.find("surname")
                        given_names = name.find("given-names")
                        if surname is not None and given_names is not None:
                            authors.append(f"{surname.text} {given_names.text}")
                    if person_group.find("etal") is not None:
                        authors.append("et al")
                else:
                    for name in citation.findall("name"):
                        surname = name.find("surname")
                        given_names = name.find("given-names")
                        if surname is not None and given_names is not None:
                            authors.append(f"{surname.text} {given_names.text}")
                    # Check for et al
                    if citation.find("etal") is not None:
                        authors.append("et al.")
                author_text = ", ".join(authors)
                    
                
                # Get title
                title_elem = citation.find("article-title")
                title = self._get_text_from_element(title_elem) if title_elem is not None else ""
            
                # Get journal/source
                source_elem = citation.find("source")
                journal = source_elem.text if source_elem is not None else ""
                
                # Get year
                year_elem = citation.find("year")
                year = year_elem.text if year_elem is not None else ""
                
                
                references.append((index, pmid, author_text, title, journal, year))
        
        return references
    
    def references_to_text(self) -> str:
        """Get references as readable text."""
        parts = []
        
        references = self.get_references()
        if references:
            parts.extend(["\nREFERENCES", "=" * 10])
            for index, pmid, authors, title, journal, year in references:
                parts.append(f"[{index}] {pmid}. {authors}. {title}. {journal} ({year})")
        
        return "\n".join(parts)
    
    

    # Text conversion for: entire paper, paper with metadata, paper without metadata, authors, references
    #
    def paper_to_text(self, include_authors: bool = True, include_references: bool = True) -> str:
        """Convert entire article to text format."""
        parts = []
        
        # Title
        title = self.get_title()
        if title:
            parts.extend(["TITLE", "=" * 5, title, "\n"])
        
        # Authors
        authors = self.get_authors()
        if include_authors and authors:
            parts.extend(["AUTHORS", "=" * 7, authors, "\n"])
        
        # Abstract
        abstract = self.get_abstract()
        if abstract:
            parts.extend(["ABSTRACT", "=" * 8, abstract, "\n"])
        
        # Body
        parts.extend(["BODY", "=" * 4])
        for section_title, content in self.get_body().items():
            parts.extend([f"\n{section_title}", "-" * len(section_title), content])
        
        # References
        references = self.get_references()
        if include_references and references:
            parts.extend(["\nREFERENCES", "=" * 10])
            for index, pmid, authors, title, journal, year in references:
                parts.append(f"[{index}] {pmid}. {authors}. {title}. {journal} ({year})")
    
        
        return "\n".join(parts)
    
    def paper_to_text_with_metadata(self) -> str:
        """Convert entire article to text format with metadata."""
        return self.paper_to_text(include_authors=True, include_references=True)

    def paper_to_text_without_metadata(self) -> str:
        """Convert entire article to text format without metadata."""
        return self.paper_to_text(include_authors=False, include_references=False)
    


    # JSON conversion methods for: entire paper, paper with metadata, paper without metadata, authors, references
    #
    def paper_to_json(self, include_authors: bool = True, include_references: bool = True) -> dict:
        """Convert entire article to JSON format."""
        paper_data = {}
        
        # Add title
        paper_data["title"] = self.get_title()
        
        # Add journal info
        paper_data["journal"] = self.get_journal_name()
        paper_data["publication_date"] = self.get_publication_date()
        paper_data["pmc_id"] = self.get_pmc_id()
        
        # Add authors if requested
        if include_authors:
            paper_data["authors"] = self.get_author_info()
        
        # Add abstract
        paper_data["abstract"] = self.get_abstract()
        
        # Add body
        paper_data["body"] = self.get_body()
        
        # Add references if requested
        if include_references:
            reference_data = []
            for index, pmid, authors, title, journal, year in self.get_references():
                reference_data.append({
                    "index": index,
                    "pmid": pmid,
                    "authors": authors,
                    "title": title,
                    "journal": journal,
                    "year": year
                })
            paper_data["references"] = reference_data
        
        return paper_data
    
    def paper_to_json_with_metadata(self) -> dict:
        """Convert entire article to JSON format with metadata."""
        return self.paper_to_json(include_authors=True, include_references=True)

    def paper_to_json_without_metadata(self) -> dict:
        """Convert entire article to JSON format without metadata."""
        return self.paper_to_json(include_authors=False, include_references=False)
    
    def authors_to_json(self) -> dict:
        """Convert author information to JSON format."""
        authors_data = {
            "pmc_id": self.get_pmc_id(),
            "title": self.get_title(),
            "journal": self.get_journal_name(),
            "publication_date": self.get_publication_date(),
            "authors": self.get_author_info()
        }
        return authors_data
    
    def references_to_json(self) -> dict:
        """Get references as JSON."""
        reference_data = []
        for index, pmid, authors, title, journal, year in self.get_references():
            reference_data.append({
                "index": index,
                "pmid": pmid,
                "authors": authors,
                "title": title,
                "journal": journal,
                "year": year
            })
        return {"references": reference_data}
    
    def save_to_json_file(self, filename: str, doc_type: str = "paper") -> None:
        """Save the article to a JSON file."""
        import json
        
        data = None
        if doc_type == "paper":
            data = self.paper_to_json()
        elif doc_type == "paper_with_metadata":
            data = self.paper_to_json_with_metadata()
        elif doc_type == "paper_without_metadata":
            data = self.paper_to_json_without_metadata()
        elif doc_type == "author":
            data = self.authors_to_json()
        elif doc_type == "references":
            data = self.references_to_json()
        
        if data:
            with open(filename, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    
    
    # Main function to save to file
    #
    def save_to_file(self, filename: str, doc_type: str = "paper", format: str = "txt") -> None:
        """
        Save the article to a file.
        
        Args:
            filename: The file path to save to
            doc_type: Type of document to save (paper, paper_with_metadata, paper_without_metadata, author, references)
            format: File format to save as (txt or json)
        """   
        if format == "txt":
            if doc_type == "paper":
                with open(filename, "w", encoding='utf-8') as f:
                    f.write(self.paper_to_text())
            elif doc_type == "paper_with_metadata":
                with open(filename, "w", encoding='utf-8') as f:
                    f.write(self.paper_to_text_with_metadata())
            elif doc_type == "paper_without_metadata":
                with open(filename, "w", encoding='utf-8') as f:
                    f.write(self.paper_to_text_without_metadata())
            elif doc_type == "author":
                with open(filename, "w", encoding='utf-8') as f:
                    f.write(self.authors_to_text())
            elif doc_type == "references":
                with open(filename, "w", encoding='utf-8') as f:
                    f.write(self.references_to_text())
        elif format == "json":
            self.save_to_json_file(filename, doc_type)
    
        

#TODO: Implement the Html2Doc class
class HtmlToDoc:
    """A class to convert a html document to txt format"""
    def __init__(self, html_path: str):
        """Initialize with path to HTML file."""
        self.tree = ET.parse(html_path)
        self.root = self.tree.getroot()
    
    def get_text(self) -> str:
        """Get the text of the HTML document."""
        pass
    
        

def sample_xml_data():
    #  get all xml files in samples folder  
    import pathlib
    xml_files = list(pathlib.Path("samples").glob("*.xml"))
    for xml_file in xml_files:
        print(f"Processing {xml_file}")
        doc = XmlToDoc(xml_file)
        
        # Save as text files
        doc.save_to_file(f"samples/{xml_file.stem}_paper.txt", doc_type="paper", format="txt")
        doc.save_to_file(f"samples/{xml_file.stem}_author.txt", doc_type="author", format="txt")
        doc.save_to_file(f"samples/{xml_file.stem}_references.txt", doc_type="references", format="txt")
        
        # Save as JSON files
        doc.save_to_file(f"samples/{xml_file.stem}_paper.json", doc_type="paper", format="json")
        doc.save_to_file(f"samples/{xml_file.stem}_author.json", doc_type="author", format="json")
        doc.save_to_file(f"samples/{xml_file.stem}_references.json", doc_type="references", format="json")

if __name__ == "__main__":
    sample_xml_data()
