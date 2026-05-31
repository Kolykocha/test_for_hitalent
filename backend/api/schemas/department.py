
from typing import  Optional, Annotated
from datetime import  datetime


from pydantic import BaseModel, StringConstraints, Field


class Department(BaseModel):

    name: Annotated[str,StringConstraints(max_length=200)] = Field(..., title="Название подразделения", description='Название подразделения')
    parent_id: Optional[int]= Field(None, title="Название родительского подразделения", description='Название родительского подразделения если есть (поле может быть Null)')
    


class DepartmentReturn(Department):  

    id: int = Field(..., title="Индификатор подразделения", description='Индификатор подразделения')
    created_at: datetime = Field(..., title="Дата создания", description='Дата создания')