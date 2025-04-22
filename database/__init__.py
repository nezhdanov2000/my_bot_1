from .database import (
    get_connection,
    init_database,
    add_client,
    create_appointment,
    get_free_slots,
    get_client_appointments
)

__all__ = [
    'get_connection',
    'init_database',
    'add_client',
    'create_appointment', 
    'get_free_slots',
    'get_client_appointments'
]