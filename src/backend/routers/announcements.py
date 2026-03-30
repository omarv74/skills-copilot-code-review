"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from datetime import datetime
from bson.objectid import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """
    Get all active announcements (visible to all users).
    Returns announcements that have expired expiration dates are excluded.
    """
    now = datetime.utcnow().isoformat()
    
    # Find announcements where:
    # - start_date is None or before now
    # - expiration_date is after now
    query = {
        "$or": [
            {"start_date": None},
            {"start_date": {"$lte": now}}
        ],
        "expiration_date": {"$gt": now}
    }
    
    announcements = []
    for announcement in announcements_collection.find(query):
        announcement["_id"] = str(announcement["_id"])
        announcements.append(announcement)
    
    return announcements


@router.get("/manage/all", response_model=List[Dict[str, Any]])
def get_all_announcements(teacher_username: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """
    Get all announcements for management (admin/teacher only).
    Requires teacher authentication.
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")

    # Get all announcements
    announcements = []
    for announcement in announcements_collection.find({}):
        announcement["_id"] = str(announcement["_id"])
        announcements.append(announcement)
    
    return announcements


@router.post("/create", response_model=Dict[str, Any])
def create_announcement(
    title: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Create a new announcement (admin/teacher only).
    Requires teacher authentication.
    
    - title: Announcement title
    - message: Announcement message/content
    - expiration_date: ISO format datetime when announcement expires
    - start_date: Optional ISO format datetime when announcement becomes active
    - teacher_username: Required for authentication
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")

    # Validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date)
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

    # Create announcement
    announcement = {
        "title": title,
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": teacher_username
    }

    result = announcements_collection.insert_one(announcement)

    announcement["_id"] = str(result.inserted_id)
    return announcement


@router.put("/update/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    title: Optional[str] = None,
    message: Optional[str] = None,
    expiration_date: Optional[str] = None,
    start_date: Optional[str] = None,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Update an announcement (admin/teacher only).
    Requires teacher authentication.
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")

    # Find announcement
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    announcement = announcements_collection.find_one({"_id": obj_id})
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Prepare update data
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if message is not None:
        update_data["message"] = message
    if expiration_date is not None:
        try:
            datetime.fromisoformat(expiration_date)
            update_data["expiration_date"] = expiration_date
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use ISO format")
    if start_date is not None:
        try:
            if start_date:  # Allow empty string to clear start_date
                datetime.fromisoformat(start_date)
            update_data["start_date"] = start_date
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid date format. Use ISO format")

    update_data["updated_at"] = datetime.utcnow().isoformat()

    # Update announcement
    result = announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=500, detail="Failed to update announcement")

    # Return updated announcement
    updated = announcements_collection.find_one({"_id": obj_id})
    updated["_id"] = str(updated["_id"])
    return updated


@router.delete("/delete/{announcement_id}", response_model=Dict[str, str])
def delete_announcement(
    announcement_id: str,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """
    Delete an announcement (admin/teacher only).
    Requires teacher authentication.
    """
    # Check teacher authentication
    if not teacher_username:
        raise HTTPException(
            status_code=401, detail="Authentication required for this action")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(
            status_code=401, detail="Invalid teacher credentials")

    # Find and delete announcement
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")

    result = announcements_collection.delete_one({"_id": obj_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted successfully"}
