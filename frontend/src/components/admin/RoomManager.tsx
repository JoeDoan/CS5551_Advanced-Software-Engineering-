import React, { useEffect, useState } from 'react'
import { Plus, Trash2, Search } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Select, Badge, Modal } from '../ui'
import { Toast } from '../common/Toast'
import { roomService } from '../../services/roomService'
import { Room } from '../../types/api'

export const RoomManager: React.FC = () => {
  const [rooms, setRooms] = useState<Room[]>([])
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('ALL')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const [roomNumber, setRoomNumber] = useState('')
  const [capacity, setCapacity] = useState('40')
  const [roomType, setRoomType] = useState('lecture')
  const [buildingName, setBuildingName] = useState('Flarsheim Hall')

  useEffect(() => {
    roomService.getRooms().then(setRooms)
  }, [])

  const handleAddRoom = async () => {
    if (!roomNumber.trim()) {
      setToast({ type: 'error', message: 'Room number is required.' })
      return
    }
    const created = await roomService.createRoom({
      room_number: roomNumber.trim(),
      capacity: Number(capacity) || 35,
      room_type: roomType,
      building_id: 2,
      building_name: buildingName,
    })
    setRooms((prev) => [...prev, created])
    setRoomNumber('')
    setIsModalOpen(false)
    setToast({ type: 'success', message: `Added room ${created.room_number}` })
  }

  const handleDeleteRoom = async (room: Room) => {
    await roomService.deleteRoom(room.id)
    setRooms((prev) => prev.filter((r) => r.id !== room.id))
    setToast({ type: 'success', message: `Removed room ${room.room_number}` })
  }

  const filtered = rooms.filter((r) => {
    const matchesType = typeFilter === 'ALL' || r.room_type.toLowerCase() === typeFilter.toLowerCase()
    const q = search.toLowerCase()
    const matchesSearch =
      !q ||
      r.room_number.toLowerCase().includes(q) ||
      (r.building_name && r.building_name.toLowerCase().includes(q))
    return matchesType && matchesSearch
  })

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Classroom & Lab Inventory</CardTitle>
          <p className="text-xs text-slate-500 mt-0.5">Manage room capacities and facility types</p>
        </div>
        <Button
          size="sm"
          variant="primary"
          leftIcon={<Plus className="w-4 h-4" />}
          onClick={() => setIsModalOpen(true)}
          data-testid="add-room-btn"
        >
          Add Room
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Input
              placeholder="Search room number or building..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              leftIcon={<Search className="w-4 h-4" />}
              data-testid="room-search-input"
            />
          </div>
          <div className="w-full sm:w-48">
            <Select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              options={[
                { value: 'ALL', label: 'All Types' },
                { value: 'lecture', label: 'Lecture' },
                { value: 'lab', label: 'Lab' },
                { value: 'auditorium', label: 'Auditorium' },
                { value: 'seminar', label: 'Seminar' },
              ]}
              data-testid="room-type-filter"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase">
                <th className="py-2.5 px-3">Room</th>
                <th className="py-2.5 px-3">Building</th>
                <th className="py-2.5 px-3">Capacity</th>
                <th className="py-2.5 px-3">Type</th>
                <th className="py-2.5 px-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((room) => (
                <tr key={room.id} className="hover:bg-slate-50">
                  <td className="py-2.5 px-3 font-semibold text-slate-800">{room.room_number}</td>
                  <td className="py-2.5 px-3 text-slate-600">{room.building_name || 'UMKC Campus'}</td>
                  <td className="py-2.5 px-3 text-slate-600">{room.capacity} seats</td>
                  <td className="py-2.5 px-3">
                    <Badge variant={room.room_type === 'lab' ? 'warning' : 'success'}>
                      {room.room_type}
                    </Badge>
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteRoom(room)}
                      data-testid={`delete-room-${room.id}`}
                    >
                      <Trash2 className="w-3.5 h-3.5 text-red-600" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Add Classroom or Lab"
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleAddRoom} data-testid="save-room-btn">
              Save Room
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Input
            label="Room Number"
            value={roomNumber}
            onChange={(e) => setRoomNumber(e.target.value)}
            placeholder="e.g. FH 302"
            data-testid="modal-room-number"
          />
          <Input
            label="Building Name"
            value={buildingName}
            onChange={(e) => setBuildingName(e.target.value)}
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Capacity"
              type="number"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              data-testid="modal-room-capacity"
            />
            <Select
              label="Room Type"
              value={roomType}
              onChange={(e) => setRoomType(e.target.value)}
              options={[
                { value: 'lecture', label: 'Lecture' },
                { value: 'lab', label: 'Lab' },
                { value: 'auditorium', label: 'Auditorium' },
                { value: 'seminar', label: 'Seminar' },
              ]}
            />
          </div>
        </div>
      </Modal>

      {toast && <Toast type={toast.type} message={toast.message} onClose={() => setToast(null)} />}
    </Card>
  )
}

export default RoomManager
