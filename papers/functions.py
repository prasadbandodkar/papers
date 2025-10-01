import os
import hashlib
import tempfile

class Functions:
    def __init__(self):
        pass
    
    @staticmethod
    def get_sanitized_filename(filename):
        """
        Get a sanitized filename from a given filename.
        """
        
        # Create a safe filename by replacing unsafe characters with underscores
        unsafe_chars = {
            "'": "", '"': "", " ": "_", ":": "_", "[": "_", "]": "_",
            "/": "_", "\\": "_", "?": "_", "*": "_", "<": "_", ">": "_", "|": "_",
            "+": "_", "=": "_", ",": "_", ";": "_", ".": "_", "&": "_", "%": "_",
            "$": "_", "#": "_", "@": "_", "!": "_", "^": "_", "(": "_", ")": "_",
            "{": "_", "}": "_", "~": "_", "`": "_"
        }
        
        # First sanitize the term
        sanitized_term = filename
        for char, replacement in unsafe_chars.items():
            sanitized_term = sanitized_term.replace(char, replacement)
            
        # Remove "_" from the beginning and end of the filename
        sanitized_term = sanitized_term.strip("_")
        
        # Then truncate if too long (most filesystems have path limits)
        max_filename_length = 100  # Safe length for most filesystems
        if len(sanitized_term) > max_filename_length:
            sanitized_term = sanitized_term[:max_filename_length]
        
        # Finally add a hash suffix to ensure uniqueness even after truncation
        filename_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
        return f"{sanitized_term}_{filename_hash}"

    @staticmethod
    def get_tempfile(name):
        # Create a unique identifier with the first 8 characters of the hash of the name
        unique_id = hashlib.md5(name.encode()).hexdigest()[:8]
        filename = f"{name}_{unique_id}.txt"
        
        # Use the system's temp directory
        return os.path.join(tempfile.gettempdir(), filename)
