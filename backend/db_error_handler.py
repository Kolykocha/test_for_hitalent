from functools import wraps
import inspect
from typing import Callable

from application.exceptions import AppError
from fastapi import HTTPException
from sqlalchemy.orm import Session
from loguru import logger
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    ProgrammingError,
    DataError,
    DBAPIError,
    TimeoutError,
    NoResultFound,
    MultipleResultsFound,
)
from sqlalchemy.orm.exc import StaleDataError, UnmappedInstanceError
from psycopg2.errors import (
    CheckViolation,
    ForeignKeyViolation,
    NotNullViolation,
    UniqueViolation,
)


def _parse_integrity_error(exc: IntegrityError) -> str:
    orig = exc.orig
    pgcode = getattr(orig, "pgcode", None)
    diag = getattr(orig, "diag", None)
    detail = getattr(diag, "message_detail", "") if diag else ""
    error_msg = f"{orig} {detail}".lower()

    if (
        isinstance(orig, UniqueViolation)
        or pgcode == '23505'
        or 'unique constraint' in error_msg
        or 'duplicate key value' in error_msg
    ):
        return "Дубликат данных: запись уже существует!"

    if (
        isinstance(orig, ForeignKeyViolation)
        or pgcode == '23503'
        or 'foreign key constraint' in error_msg
    ):
        if (
            'is still referenced' in error_msg
            or 'still referenced from table' in error_msg
            or 'update or delete on table' in error_msg
        ):
            return "Нельзя удалить или изменить запись: она используется в связанных данных!"
        if 'is not present in table' in error_msg or 'insert or update on table' in error_msg:
            return "Связанная запись не найдена!"
        return "Ошибка связанной записи"

    if isinstance(orig, CheckViolation) or pgcode == '23514' or 'check constraint' in error_msg:
        return "Недопустимое значение поля!"

    if (
        isinstance(orig, NotNullViolation)
        or pgcode == '23502'
        or 'not null' in error_msg
        or 'not-null' in error_msg
    ):
        return "Обязательное поле не заполнено!"

    return "Ошибка целостности данных"


def _error_message(exc: Exception) -> str:
    """Возвращает сообщение SQLAlchemy-ошибки безопасно для логирования."""
    return str(getattr(exc, "orig", exc))


def db_error_handler():
    """
    Декоратор для обработки ошибок, связанных с базой данных при использовании SQLAlchemy.

    Этот декоратор перехватывает типичные исключения SQLAlchemy, автоматически вызывает `rollback()`
    при необходимости, логирует ошибки и возвращает соответствующие HTTP-исключения для FastAPI.

    Поддерживаемые ошибки:
        - IntegrityError: Ошибки уникальности, ограничения и т.п.
        - OperationalError: Проблемы подключения к БД
        - ProgrammingError, DataError: Ошибки в SQL-запросах
        - TimeoutError: Таймаут при выполнении запроса
        - NoResultFound: Не найдены записи
        - MultipleResultsFound: Найдено больше одной записи, когда ожидалась одна
        - StaleDataError, UnmappedInstanceError: Конфликты ORM или устаревшие данные
        - DBAPIError: Ошибки низкоуровневого драйвера
        - HTTPException: Пробрасываются после отката транзакции
        - Другие исключения: Пробрасываются после отката транзакции

    Поиск `db` происходит через именованный аргумент (`db=...`) или по первому аргументу, 
    имеющему метод `.rollback()` (обычно объект сессии SQLAlchemy).

    Returns:
        Callable: Декоратор для асинхронных функций с аргументами, содержащими сессию SQLAlchemy.
    
    Usage:
        @db_error_handler()
        async def your_function(db: Session):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async def _rollback(db_session) -> None:
                if db_session is None:
                    return
                try:
                    result = db_session.rollback()
                    if inspect.isawaitable(result):
                        await result
                except Exception:
                    pass

            # Пытаемся найти объект сессии SQLAlchemy
            db = kwargs.get("db") or next((arg for arg in args if hasattr(arg, "rollback")), None)
            try:
                return await func(*args, **kwargs)
            except IntegrityError as e:
                await _rollback(db)
                error_detail = _parse_integrity_error(e)
                logger.warning(f"Integrity Error: {_error_message(e)}")
                raise HTTPException(status_code=400, detail=error_detail)
            except OperationalError as e:
                await _rollback(db)
                logger.error(f"Database Connection Error: {_error_message(e)}")
                raise HTTPException(status_code=503, detail="Ошибка подключения к базе данных. Попробуйте позже.")
            except (ProgrammingError, DataError) as e:
                await _rollback(db)
                logger.error(f"Query Error: {_error_message(e)}")
                raise HTTPException(status_code=400, detail="Некорректный запрос к базе данных")
            except TimeoutError as e:
                await _rollback(db)
                logger.error(f"Query Timeout: {_error_message(e)}")
                raise HTTPException(status_code=504, detail="Превышено время выполнения запроса")
            except NoResultFound as e:
                await _rollback(db)
                logger.warning(f"No Results Found: {str(e)}")
                raise HTTPException(status_code=404, detail="Запрошенные данные не найдены")
            except MultipleResultsFound as e:
                await _rollback(db)
                logger.error(f"Multiple Results Found: {str(e)}")
                raise HTTPException(status_code=500, detail="Найдено несколько неоднозначных результатов")
            except (StaleDataError, UnmappedInstanceError) as e:
                await _rollback(db)
                logger.error(f"ORM Error: {str(e)}")
                raise HTTPException(status_code=409, detail="Конфликт версий данных. Обновите данные и повторите.")
            except DBAPIError as e:
                await _rollback(db)
                logger.error(f"Low-level DB Error: {_error_message(e)}")
                raise HTTPException(status_code=500, detail="Ошибка драйвера базы данных")
            
            except AppError as e:
                await _rollback(db)
                raise e

            #HTTPException мы вызываем сами, поэтому пропускаем на обработку FastAPI, тут только откатываем
            except HTTPException as e:
                await _rollback(db)
                raise e
            
            #Всё остальное обрабатывается через HTTPException на уровне роутера, тут только откатываем
            except Exception as e:
                await _rollback(db)
                raise e
        return wrapper
    return decorator