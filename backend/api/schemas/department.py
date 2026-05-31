
from typing import  Optional, Annotated, List
from datetime import  datetime

from schemas.employee import Employee

from pydantic import BaseModel, StringConstraints, Field


class Department(BaseModel):
    id: int = Field(..., title="Индификатор подразделения", description='Индификатор подразделения')
    created_at: datetime = Field(..., title="Дата создания", description='Дата создания')
    name: Annotated[str,StringConstraints(max_length=200)] = Field(..., title="Название подразделения", description='Название подразделения')
    parent_id: Optional[int]= Field(None, title="Название родительского подразделения", description='Название родительского подразделения если есть (поле может быть Null)')
    
class DepartmentCreate(BaseModel):
    
    name: Annotated[str,StringConstraints(max_length=200)] = Field(..., title="Название подразделения", description='Название подразделения')
    parent_id: Optional[int]= Field(None, title="Название родительского подразделения", description='Название родительского подразделения если есть (поле может быть Null)')
        


class DepartmentReturn(Department):  

    id: int = Field(..., title="Индификатор подразделения", description='Индификатор подразделения')
    created_at: datetime = Field(..., title="Дата создания", description='Дата создания')




class DepartmentTree(BaseModel):
    department : Department
    employees : List[Employee] = []
    children: List[Department] = []
