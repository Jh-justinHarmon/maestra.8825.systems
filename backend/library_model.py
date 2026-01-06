"""
Library Model - Three-Library Architecture
Implements Personal, Role, and Company library boundaries with device-based access control.
"""

from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel


class LibraryType(str, Enum):
    """Three library types with strict boundaries."""
    PERSONAL = "personal"
    ROLE_OPERATOR = "role_operator"
    COMPANY = "company"


class DeviceType(str, Enum):
    """Device types that determine library access."""
    IPHONE = "iphone"
    PERSONAL_PC = "personal_pc"
    WORK_PC = "work_pc"
    UNKNOWN = "unknown"


class CaptureType(str, Enum):
    """Four capture types with explicit library routing."""
    PATTERN = "pattern"        # → Personal
    DECISION = "decision"      # → Role Operator
    EXPERIMENT = "experiment"  # → Role Operator + Change Log
    LESSON = "lesson"          # → Personal + Role (optional)


class Library(BaseModel):
    """A library instance with ownership and access rules."""
    id: str
    type: LibraryType
    owner_id: str  # user_id for personal, org_id for role/company
    org_id: Optional[str] = None  # e.g., "RAL", "HCSS", "8825"
    name: str
    created_at: datetime
    
    class Config:
        use_enum_values = True


class Device(BaseModel):
    """A registered device with library access permissions."""
    id: str
    user_id: str
    type: DeviceType
    name: str  # e.g., "Josie's iPhone", "Josie Work PC"
    registered_at: datetime
    last_seen: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class LibraryAccess(BaseModel):
    """Access control mapping: device → allowed libraries."""
    user_id: str
    device_id: str
    device_type: DeviceType
    allowed_library_types: List[LibraryType]
    
    class Config:
        use_enum_values = True


class BoundaryViolation(Exception):
    """Raised when a device attempts cross-boundary access."""
    def __init__(self, message: str, user_id: str, device_id: str, library_type: LibraryType, action: str):
        super().__init__(message)
        self.user_id = user_id
        self.device_id = device_id
        self.library_type = library_type
        self.action = action
        self.timestamp = datetime.utcnow()


# Device-to-Library Access Rules
DEVICE_LIBRARY_MAP: Dict[DeviceType, List[LibraryType]] = {
    DeviceType.IPHONE: [LibraryType.PERSONAL],
    DeviceType.PERSONAL_PC: [LibraryType.PERSONAL, LibraryType.ROLE_OPERATOR],
    DeviceType.WORK_PC: [LibraryType.ROLE_OPERATOR, LibraryType.COMPANY],
    DeviceType.UNKNOWN: []  # No access until device type determined
}


# Capture-to-Library Routing Rules
CAPTURE_LIBRARY_MAP: Dict[CaptureType, List[LibraryType]] = {
    CaptureType.PATTERN: [LibraryType.PERSONAL],
    CaptureType.DECISION: [LibraryType.ROLE_OPERATOR],
    CaptureType.EXPERIMENT: [LibraryType.ROLE_OPERATOR],  # + change log
    CaptureType.LESSON: [LibraryType.PERSONAL, LibraryType.ROLE_OPERATOR]  # both
}


def get_allowed_libraries_for_device(device_type: DeviceType) -> List[LibraryType]:
    """
    Get list of library types a device can access.
    
    Args:
        device_type: Type of device (iPhone, Personal PC, Work PC)
        
    Returns:
        List of allowed library types
        
    Examples:
        >>> get_allowed_libraries_for_device(DeviceType.IPHONE)
        [LibraryType.PERSONAL]
        
        >>> get_allowed_libraries_for_device(DeviceType.PERSONAL_PC)
        [LibraryType.PERSONAL, LibraryType.ROLE_OPERATOR]
    """
    return DEVICE_LIBRARY_MAP.get(device_type, [])


def get_target_libraries_for_capture(capture_type: CaptureType) -> List[LibraryType]:
    """
    Get list of library types where a capture should be stored.
    
    Args:
        capture_type: Type of capture (Pattern, Decision, Experiment, Lesson)
        
    Returns:
        List of target library types
        
    Examples:
        >>> get_target_libraries_for_capture(CaptureType.PATTERN)
        [LibraryType.PERSONAL]
        
        >>> get_target_libraries_for_capture(CaptureType.LESSON)
        [LibraryType.PERSONAL, LibraryType.ROLE_OPERATOR]
    """
    return CAPTURE_LIBRARY_MAP.get(capture_type, [])


def enforce_boundary(
    user_id: str,
    device_id: str,
    device_type: DeviceType,
    library_type: LibraryType,
    action: str  # "read" | "write"
) -> bool:
    """
    Enforce boundary: check if device can perform action on library.
    
    Args:
        user_id: User attempting access
        device_id: Device attempting access
        device_type: Type of device
        library_type: Type of library being accessed
        action: "read" or "write"
        
    Returns:
        True if allowed
        
    Raises:
        BoundaryViolation: If access denied
        
    Examples:
        >>> enforce_boundary("josie", "iphone_1", DeviceType.IPHONE, LibraryType.PERSONAL, "read")
        True
        
        >>> enforce_boundary("josie", "iphone_1", DeviceType.IPHONE, LibraryType.COMPANY, "read")
        BoundaryViolation: Device iphone_1 cannot read company library
    """
    allowed = get_allowed_libraries_for_device(device_type)
    
    if library_type not in allowed:
        raise BoundaryViolation(
            f"Device {device_id} (type={device_type.value}) cannot {action} {library_type.value} library",
            user_id=user_id,
            device_id=device_id,
            library_type=library_type,
            action=action
        )
    
    return True


def validate_capture_on_device(
    device_type: DeviceType,
    capture_type: CaptureType
) -> tuple[bool, Optional[str]]:
    """
    Check if a capture type can be created on a device.
    
    Args:
        device_type: Type of device
        capture_type: Type of capture being created
        
    Returns:
        (is_valid, error_message)
        
    Examples:
        >>> validate_capture_on_device(DeviceType.IPHONE, CaptureType.PATTERN)
        (True, None)
        
        >>> validate_capture_on_device(DeviceType.IPHONE, CaptureType.DECISION)
        (False, "Decision captures require Role Operator library (not available on iPhone)")
    """
    device_libraries = get_allowed_libraries_for_device(device_type)
    target_libraries = get_target_libraries_for_capture(capture_type)
    
    # Check if device can access ALL target libraries
    for target in target_libraries:
        if target not in device_libraries:
            return (
                False,
                f"{capture_type.value.title()} captures require {target.value} library "
                f"(not available on {device_type.value})"
            )
    
    return (True, None)


def log_boundary_violation(violation: BoundaryViolation) -> None:
    """
    Log boundary violation for audit trail.
    
    Args:
        violation: BoundaryViolation exception instance
        
    Side Effects:
        Writes to boundary_violations.log
        Alerts architect if pattern detected
    """
    # TODO: Implement logging to file/database
    # TODO: Implement alert mechanism for repeated violations
    print(f"[BOUNDARY VIOLATION] {violation.timestamp.isoformat()}")
    print(f"  User: {violation.user_id}")
    print(f"  Device: {violation.device_id}")
    print(f"  Library: {violation.library_type.value}")
    print(f"  Action: {violation.action}")
    print(f"  Message: {str(violation)}")


# Example usage for Josie's three devices
def get_josie_device_config() -> Dict[str, Dict]:
    """
    Example configuration for Josie's three devices.
    
    Returns:
        Device configuration mapping
    """
    return {
        "josie_iphone": {
            "device_type": DeviceType.IPHONE,
            "allowed_libraries": [LibraryType.PERSONAL],
            "can_capture": [CaptureType.PATTERN, CaptureType.LESSON]
        },
        "josie_personal_pc": {
            "device_type": DeviceType.PERSONAL_PC,
            "allowed_libraries": [LibraryType.PERSONAL, LibraryType.ROLE_OPERATOR],
            "can_capture": [CaptureType.PATTERN, CaptureType.DECISION, CaptureType.EXPERIMENT, CaptureType.LESSON]
        },
        "josie_work_pc": {
            "device_type": DeviceType.WORK_PC,
            "allowed_libraries": [LibraryType.ROLE_OPERATOR, LibraryType.COMPANY],
            "can_capture": [CaptureType.DECISION, CaptureType.EXPERIMENT]  # No personal captures on work PC
        }
    }
