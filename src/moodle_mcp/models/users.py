"""
Pydantic models for Moodle users.
"""

from pydantic import Field

from .base import MoodleBaseModel

class User(MoodleBaseModel):
    """Represents a Moodle user."""
    id: int = Field(description="User ID")
    username: str | None = Field(None, description="Username")
    firstname: str | None = Field(None, description="First name")
    lastname: str | None = Field(None, description="Last name")
    fullname: str | None = Field(None, description="Full name")
    email: str | None = Field(None, description="Email address")

    # Profile
    department: str | None = Field(None, description="Department")
    institution: str | None = Field(None, description="Institution")
    idnumber: str | None = Field(None, description="ID number")
    phone1: str | None = Field(None, description="Phone number 1")
    phone2: str | None = Field(None, description="Phone number 2")
    address: str | None = Field(None, description="Address")
    city: str | None = Field(None, description="City")
    country: str | None = Field(None, description="Country code")

    # Images
    profileimageurl: str | None = Field(None, description="Profile image URL")
    profileimageurlsmall: str | None = Field(None, description="Small profile image URL")

    # Timestamps
    firstaccess: int | None = Field(None, description="First access (Unix timestamp)")
    lastaccess: int | None = Field(None, description="Last access (Unix timestamp)")

    # Additional
    description: str | None = Field(None, description="User description")
    descriptionformat: int | None = Field(None, description="Description format")
    lang: str | None = Field(None, description="Preferred language")
    theme: str | None = Field(None, description="Preferred theme")
    timezone: str | None = Field(None, description="Timezone")
    mailformat: int | None = Field(None, description="Mail format (0=plain, 1=HTML)")
