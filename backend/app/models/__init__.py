#used to control how models are exposed when the package is imported.
from .user import User
from .clinic import Clinic
from .patient import Patient
from .document import Document
from .extraction import Extraction

#all public models
__all__ = ["User", "Clinic", "Patient", "Document", "Extraction"]


#collects all model classes into a single public interface, making them easy and safe to import throughout the application while controlling what the package exposes.