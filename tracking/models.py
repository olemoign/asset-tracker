from .utilities.domain_model import CreationDateTimeMixin, Enum, Field, Model, String


class Asset(Model, CreationDateTimeMixin):
    customer = Field(String)
    site = Field(String)
    status = Field(Enum('', '', name='status'))
    notes = Field(String)
    history = Field(String)
    current_location = Field(String)
    equipments = Field(String)