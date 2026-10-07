from pydantic import BaseModel, Field


class ProjectWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    project_number: str = Field(default="", max_length=100)
    principal_investigator: str = Field(default="", max_length=200)
    funding_agency: str = Field(default="", max_length=200)
    program_name: str = Field(default="", max_length=200)
    research_title: str = Field(default="", max_length=200)


class MemberWrite(BaseModel):
    user_id: int
    role: str = Field(default="", max_length=100)


class MemberUpdate(BaseModel):
    user_id: int | None = None
    role: str | None = Field(default=None, max_length=100)


class MemberOut(BaseModel):
    id: int
    user_id: int
    username: str
    name: str
    role: str


class CardWrite(BaseModel):
    label: str = Field(default="", max_length=80)
    number: str = Field(min_length=1, max_length=40)


class CardOut(BaseModel):
    id: int
    label: str
    number: str


class ProjectOut(BaseModel):
    id: int
    name: str
    project_number: str
    principal_investigator: str
    funding_agency: str
    program_name: str
    research_title: str
    members: list[MemberOut]
    cards: list[CardOut]


class ExternalWrite(BaseModel):
    affiliation: str = Field(min_length=1, max_length=100)
    position: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)


class ExternalOut(BaseModel):
    id: int
    affiliation: str
    position: str
    name: str


class AttendeeOptions(BaseModel):
    members: list[MemberOut]
    externals: list[ExternalOut]
