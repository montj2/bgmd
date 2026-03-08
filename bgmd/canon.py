import csv
import pkgutil
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class Book:
    slug: str
    display_name: str
    chapters: int
    bg_name: str
    testament: str

class Canon:
    def __init__(self, name: str = "catholic"):
        self.name = name
        self.books: List[Book] = []
        self._slug_map: Dict[str, Book] = {}
        self._name_map: Dict[str, Book] = {}
        self._load_canon()

    def _load_canon(self):
        # In a real package, we'd use importlib.resources or similar
        # For now, we'll assume the file is in the same directory structure
        try:
            # Try to load from the package directory
            data = pkgutil.get_data(__name__, f"books/{self.name}.csv")
            if data:
                decoded = data.decode('utf-8').splitlines()
                reader = csv.DictReader(decoded)
                for row in reader:
                    book = Book(
                        slug=row['slug'],
                        display_name=row['display_name'],
                        chapters=int(row['chapters']),
                        bg_name=row['bg_name'],
                        testament=row['testament']
                    )
                    self.books.append(book)
                    self._slug_map[book.slug] = book
                    self._name_map[book.display_name.lower()] = book
            else:
                # Fallback for local development if pkgutil fails
                with open(f"bgmd/books/{self.name}.csv", 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        book = Book(
                            slug=row['slug'],
                            display_name=row['display_name'],
                            chapters=int(row['chapters']),
                            bg_name=row['bg_name'],
                            testament=row['testament']
                        )
                        self.books.append(book)
                        self._slug_map[book.slug] = book
                        self._name_map[book.display_name.lower()] = book
        except FileNotFoundError:
            raise ValueError(f"Canon '{self.name}' not found.")

    def get_book(self, identifier: str) -> Optional[Book]:
        identifier = identifier.lower().replace(" ", "")
        # Try slug first
        if identifier in self._slug_map:
            return self._slug_map[identifier]
        # Try display name (normalized)
        for name, book in self._name_map.items():
            if name.replace(" ", "") == identifier:
                return book
        return None
