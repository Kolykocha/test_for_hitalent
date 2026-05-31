
from typing import  Optional, Annotated, List
from datetime import  datetime

from models.employee import CommonEmployee
from models.department import CommonDepartment

from pydantic import BaseModel, StringConstraints, Field


    
class DepartmentCreate(BaseModel):
    
    name: Annotated[str,StringConstraints(max_length=200)] = Field(..., title="Название подразделения", description='Название подразделения')
    parent_id: Optional[int]= Field(None, title="Название родительского подразделения", description='Название родительского подразделения если есть (поле может быть Null)')
        


class DepartmentReturn(DepartmentCreate):  

    id: int = Field(..., title="Индификатор подразделения", description='Индификатор подразделения')
    created_at: datetime = Field(..., title="Дата создания", description='Дата создания')




class DepartmentTree(BaseModel):
    department : CommonDepartment
    employees : List[CommonEmployee] = []
    children: List[DepartmentTree] = []
