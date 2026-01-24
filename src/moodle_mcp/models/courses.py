"""
Pydantic models for Moodle courses.
"""

from pydantic import Field, field_validator

from .base import MoodleBaseModel

class Course(MoodleBaseModel):
    """Represents a Moodle course."""
    id: int = Field(description="Unique course ID")
    fullname: str = Field(description="Full course name")
    shortname: str = Field(description="Short course identifier")
    categoryid: int | None = Field(None, description="Course category ID")
    categoryname: str | None = Field(None, description="Category name")

    # Timestamps
    startdate: int | None = Field(None, description="Course start date (Unix timestamp)")
    enddate: int | None = Field(None, description="Course end date (Unix timestamp)")

    # Visibility and status
    visible: bool | None = Field(True, description="Course visibility")
    hiddenbycron: int | None = Field(None, description="Hidden by cron")

    # Optional metadata
    summary: str | None = Field(None, description="Course description")
    summaryformat: int | None = Field(None, description="Summary format")
    format: str | None = Field(None, description="Course format (topics, weeks, etc.)")
    showgrades: bool | None = Field(None, description="Show grades to students")
    newsitems: int | None = Field(None, description="Number of news items")
    numsections: int | None = Field(None, description="Number of sections")
    maxbytes: int | None = Field(None, description="Maximum upload size")
    showreports: int | None = Field(None, description="Show activity reports")
    groupmode: int | None = Field(None, description="Group mode (0=none, 1=separate, 2=visible)")
    groupmodeforce: int | None = Field(None, description="Force group mode")
    defaultgroupingid: int | None = Field(None, description="Default grouping ID")

class CourseCategory(MoodleBaseModel):
    """Represents a course category."""
    id: int = Field(description="Category ID")
    name: str = Field(description="Category name")
    idnumber: str | None = Field(None, description="ID number")
    description: str | None = Field(None, description="Category description")
    descriptionformat: int | None = Field(None, description="Description format")
    parent: int | None = Field(None, description="Parent category ID")
    sortorder: int | None = Field(None, description="Sort order")
    coursecount: int | None = Field(None, description="Number of courses in category")
    depth: int | None = Field(None, description="Category depth")
    path: str | None = Field(None, description="Category path")

class CourseModule(MoodleBaseModel):
    """Represents a course module (activity)."""
    id: int = Field(description="Module ID")
    name: str = Field(description="Module name")
    modname: str = Field(description="Module type (assign, quiz, forum, etc.)")
    modicon: str | None = Field(None, description="Module icon URL")
    url: str | None = Field(None, description="Module URL")
    visible: int | None = Field(None, description="Visibility")
    uservisible: bool | None = Field(None, description="Visible to user")
    availabilityinfo: str | None = Field(None, description="Availability info")
    indent: int | None = Field(None, description="Indentation level")
    completion: int | None = Field(None, description="Completion tracking")

class CourseSection(MoodleBaseModel):
    """Represents a course section."""
    id: int = Field(description="Section ID")
    name: str | None = Field(None, description="Section name")
    section: int = Field(description="Section number")
    summary: str | None = Field(None, description="Section summary")
    summaryformat: int | None = Field(None, description="Summary format")
    visible: int | None = Field(None, description="Visibility")
    modules: list[CourseModule] = Field(default_factory=list, description="Modules in section")

