from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.core.database import get_session
from app.models.entities import Room, Building, Schedule
from app.schemas.api_schemas import RoomCreate, RoomUpdate, RoomResponse

router = APIRouter()


@router.get("", response_model=List[RoomResponse])
def list_rooms(
    min_capacity: Optional[int] = Query(default=None, ge=1, description="Minimum room capacity"),
    room_type: Optional[str] = Query(default=None, description="lecture, lab, seminar, auditorium"),
    building_id: Optional[int] = Query(default=None, description="Filter by building ID"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
):
    """Retrieve classrooms and labs with building name and optional filters."""
    stmt = select(Room, Building.name).join(
        Building, Building.id == Room.building_id, isouter=True
    )
    if min_capacity is not None:
        stmt = stmt.where(Room.capacity >= min_capacity)
    if room_type:
        stmt = stmt.where(Room.room_type == room_type.lower())
    if building_id is not None:
        stmt = stmt.where(Room.building_id == building_id)

    rows = session.exec(stmt.offset(offset).limit(limit)).all()
    return [
        RoomResponse(**room.model_dump(), building_name=building_name)
        for room, building_name in rows
    ]


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: RoomCreate,
    session: Session = Depends(get_session),
):
    """Add a classroom or lab with foreign key and unique constraint validation."""
    building = session.get(Building, payload.building_id)
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Building ID {payload.building_id} not found",
        )

    existing = session.exec(
        select(Room).where(
            Room.building_id == payload.building_id,
            Room.room_number == payload.room_number,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Room '{payload.room_number}' already exists in building {payload.building_id}",
        )

    room = Room(
        building_id=payload.building_id,
        room_number=payload.room_number,
        capacity=payload.capacity,
        room_type=payload.room_type.value if hasattr(payload.room_type, "value") else str(payload.room_type),
    )
    try:
        session.add(room)
        session.commit()
        session.refresh(room)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room conflict in building",
        )
    return RoomResponse(**room.model_dump(), building_name=building.name)


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(
    room_id: int,
    session: Session = Depends(get_session),
):
    """Retrieve a single room by its unique ID."""
    row = session.exec(
        select(Room, Building.name)
        .join(Building, Building.id == Room.building_id, isouter=True)
        .where(Room.id == room_id)
    ).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )
    room, building_name = row
    return RoomResponse(**room.model_dump(), building_name=building_name)


@router.put("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    payload: RoomUpdate,
    session: Session = Depends(get_session),
):
    """Update room attributes."""
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    target_bldg_id = payload.building_id or room.building_id
    target_room_num = payload.room_number or room.room_number

    if payload.building_id is not None:
        building = session.get(Building, payload.building_id)
        if not building:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building ID {payload.building_id} not found",
            )
        room.building_id = payload.building_id

    if payload.room_number is not None:
        duplicate = session.exec(
            select(Room).where(
                Room.building_id == target_bldg_id,
                Room.room_number == target_room_num,
                Room.id != room_id,
            )
        ).first()
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Room '{target_room_num}' already exists in building {target_bldg_id}",
            )
        room.room_number = payload.room_number

    if payload.capacity is not None:
        room.capacity = payload.capacity
    if payload.room_type is not None:
        room.room_type = payload.room_type.value if hasattr(payload.room_type, "value") else str(payload.room_type)

    try:
        session.add(room)
        session.commit()
        session.refresh(room)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Database integrity error updating room",
        )

    bldg_name = session.exec(select(Building.name).where(Building.id == room.building_id)).first()
    return RoomResponse(**room.model_dump(), building_name=bldg_name)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    session: Session = Depends(get_session),
):
    """Delete a room with active schedule protection."""
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found",
        )

    # Delete guard: check if used in active schedule
    used = session.exec(select(Schedule.id).where(Schedule.room_id == room_id)).first()
    if used:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room is used by a schedule",
        )

    session.delete(room)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
