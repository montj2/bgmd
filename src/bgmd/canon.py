import csv
import importlib.resources
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path

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
        try:
            # Use modern importlib.resources to load the data file
            # This works correctly when installed as a package
            traversable = importlib.resources.files("bgmd.books").joinpath(f"{self.name}.csv")
            with traversable.open('r', encoding='utf-8') as f:
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
        except (FileNotFoundError, ModuleNotFoundError, ImportError):
            # Fallback for local development or if resources fail
            local_path = Path(__file__).parent / "books" / f"{self.name}.csv"
            if local_path.exists():
                with open(local_path, 'r', encoding='utf-8') as f:
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
            else:
                raise ValueError(f"Canon '{self.name}' not found.")

    def get_book(self, identifier: str) -> Optional[Book]:
        orig = identifier
        identifier = identifier.lower().replace(" ", "")
        # Normalize Psalm/Psalms
        if identifier == "psalm":
            identifier = "psalms"
        # Try slug first
        if identifier in self._slug_map:
            return self._slug_map[identifier]
        # Try display name (normalized)
        for name, book in self._name_map.items():
            if name.replace(" ", "") == identifier:
                return book
        # print(f"DEBUG: Book not found for '{orig}' (normalized: '{identifier}') in canon '{self.name}'")
        # print(f"DEBUG: Slugs: {list(self._slug_map.keys())[:5]}...")
        return None
