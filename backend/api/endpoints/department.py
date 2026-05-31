from datetime import date, datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Path, Request, status, Query,Response 
from sqlalchemy.orm import Session
from typing import  List, Optional

from models.department import CommonDepartment as Department
from models.employee import CommonEmployee as Employee

from schemas.department import Department,DepartmentCreate, DepartmentReturn, DepartmentTree
from schemas.employee import Employee,EmployeeCreate, EmployeeReturn


from db_error_handler import db_error_handler
from db import get_db

router = APIRouter(prefix='/departments', route_class='')

async def get_children_tree(
    db: Session,
    parent_id: int,
    max_depth: int,
    include_employees: bool,
    current_depth: int
) -> List[DepartmentTree]:

    if max_depth is not None and current_depth >= max_depth:
        return []
    
    # Получаем детей текущего подразделения
    children_depts = db.query(Department).filter(Department.parent_id == parent_id).all()
    
    result = []
    for child_dept in children_depts:
        employees = []
        if include_employees:
            employees = db.query(Employee).filter(Employee.department_id == child_dept.id).all()
        
        grandchildren = await get_children_tree(
            db, 
            child_dept.id, 
            max_depth, 
            include_employees, 
            current_depth + 1
        )
        
        result.append(DepartmentTree(
            department=child_dept,
            employees=employees,
            children=grandchildren
        ))
    
    return result

async def cascade_delete(db: Session, department_id: int):
    """Каскадное удаление подразделения, всех сотрудников и дочерних подразделений"""
    
    children = db.query(Department).filter(Department.parent_id == department_id).all()
    for child in children:
        await cascade_delete(db, child.id)
    
    db.query(Employee).filter(Employee.department_id == department_id).delete()

    db.query(Department).filter(Department.id == department_id).delete()
    
    db.commit()


async def reassign_delete(db: Session, department_id: int, target_department_id: int):
    """Удаление подразделения с перемещением сотрудников в другое подразделение"""
    
    db.query(Employee).filter(Employee.department_id == department_id).update(
        {Employee.department_id: target_department_id}
    )
    
    children = db.query(Department).filter(Department.parent_id == department_id).all()
    for child in children:
        await reassign_delete(db, child.id,target_department_id)
    
    db.query(Department).filter(Department.id == department_id).delete()
    
    db.commit()

@router.post('/', response_model=DepartmentReturn, status_code=status.HTTP_201_CREATED)
@db_error_handler()
async def create_department(department: DepartmentCreate, db: Session = Depends(get_db)):

    today = datetime.today()

    if department.parent_id != None:
        department_copy = db.query(Department).filter(Department.parent_id == department.parent_id, 
                                                      Department.name == (department.name).strip).first()

        if department_copy:
            raise HTTPException(status_code=400, detail="Department name is exists") 

    new_departnemt = Department(
        name = (department.name).strip(),
        parent_id=department.parent_id,
        created_at=today
    )

    db.add(new_departnemt)
    db.commit()
    db.refresh(new_departnemt) 
    return new_departnemt


@router.post('/{id}/employees/', response_model=EmployeeReturn, status_code=status.HTTP_201_CREATED)
@db_error_handler()
async def create_employee(id:int, employee: EmployeeCreate, db: Session = Depends(get_db)):
    today = datetime.today()
    department = db.query(Department).filter(Department.id == id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    new_employee = Employee(
        department_id = id,
        full_name = employee.full_name,
        position = employee.position,
        hired_at = employee.hired_at,
        created_at = today
    )

    db.add(new_employee)
    db.commit()
    db.refresh(new_employee) 
    return new_employee

@router.get('/{id}', response_model=DepartmentTree, status_code=status.HTTP_200_OK)
@db_error_handler()
async def get_deparments(id:int,
                         depth:int = Query(1, ge=1, le=5, description="Глубина вложенности подразделений (1-5)"),
                         include_employees:bool = Query(True, description="Включить сотрудников в ответ"), 
                         db: Session = Depends(get_db)):

    department = db.query(Department).filter(Department.id == id).first()

    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    employees = []

    if include_employees:
        employees = db.query(Employee).filter(Employee.department_id == id).order_by(Employee.created_at).all()

    children = await get_children_tree(db, id, depth, include_employees, current_depth=1)
    
    return  DepartmentTree(
        department=department,
        employees=employees,
        children=children
    )


@router.patch('/{id}', response_model=DepartmentReturn, status_code=status.HTTP_200_OK)
@db_error_handler()
async def patch_deparments(id:int,
                            department: DepartmentCreate,
                           db: Session = Depends(get_db)):
    
    department_update = db.query(Department).filter(Department.id == id).first()

    if not department_update:
        raise HTTPException(status_code=404, detail="Department not found")
    
    
    if department.name:
        department_update.name = (department.name).strip()
    if department.parent_id:
        
        if department.parent_id == department_update.parent_id:
            raise HTTPException(status_code=400, detail="Department cant be a parent to himself")
        
        deportament_parent = db.query(Department).filter(Department.id == department.parent_id).first()

        if deportament_parent.parent_id == department_update.parent_id:
            raise HTTPException(status_code=409, detail="Department cannot be its own parent")
        
        department_update.parent_id = department.parent_id

    db.commit()
    db.refresh(department_update) 
    
    return department_update

@router.delete('/{id}', status_code=status.HTTP_204_NO_CONTENT)
@db_error_handler()
async def delete_deparments(id:int,
                            mode: str = Query(...,descriptio= 'cascade — удалить подразделение, всех сотрудников и все дочерние подразделения reassign — удалить подразделение, а сотрудников перевести в reassign_to_department_id'),
                            reassign_to_department_id: Optional[int] = Query(None, description="ID подразделения для перемещения сотрудников (обязателен при mode=reassign)"),
                            db: Session = Depends(get_db)):


    if mode == 'reassign' and reassign_to_department_id == None:
        raise HTTPException(status_code=400, detail="reassign_to_department_id is None")
    
    department = db.query(Department).filter(Department.id == id).first()


    target_department = db.query(Department).filter(Department.id == reassign_to_department_id).first()
    if not target_department:
            raise HTTPException(
                status_code=404,
                detail=f"Target department with id {reassign_to_department_id} not found"
            )
    
    if reassign_to_department_id == id:
            raise HTTPException(
                status_code=409,
                detail="Cannot reassign employees to the same department being deleted"
            )


    if mode == 'cascade': 
        await cascade_delete(db, id)
    elif mode == 'reassign': 
        await reassign_delete(db, id, reassign_to_department_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)



