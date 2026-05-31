
from typing import  Optional, Annotated
from datetime import  datetime,date


from pydantic import BaseModel, StringConstraints, Field


class Employee(BaseModel):

    id: int = Field(..., title="Индификатор сотрудника", description='Индификатор сотрудника')
    department_id: int = Field(..., title="Предприятие", description='Предприятие за которым закреплен сотрудник')
    full_name : Annotated[str,StringConstraints(max_length=200)] = Field(..., title="Имя", description='Имя сотрудника')
    position : Annotated[str,StringConstraints(max_length=200)] = Field(..., title="Должность", description='Должность сотрудника')
    hired_at: Optional[date]= Field(None, title="Дата трудоустройства сотрудника", description='Дата трудоустройства сотрудника')
    created_at: datetime = Field(..., title="Дата создания", description='Дата создания')


