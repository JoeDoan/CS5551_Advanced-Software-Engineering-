# Sprint 1 Individual Implementation Plan: Tina Nguyen (Updated)

**Name:** Tina Nguyen  
**Role:** Frontend Engineer (Interactive Preferences Portal, Schedule Filters & Export, Toast System)  
**Assigned User Stories:** US-6 (Instructor Preference Portal), US-8 (Schedule Multi-Filters), US-9 (Schedule Export)  
**Assigned Acceptance Criteria:** AC 6.1, AC 6.2, AC 6.3, AC 8.1, AC 8.2, AC 9.2  
**Target LOC:** 550+ Lines of Code (Production + Automated Vitest Tests)  
**Branch:** `feature/tina-preference-schedule-ui`  

---

## 1. Mục Tiêu & Trách Nhiệm Cốt Lõi (Domain Ownership)

Sau khi Sal đã hoàn thành bộ UI Components cơ bản và tầng gọi API Services (`origin/client_api`), nhiệm vụ chính của Tina trong Sprint 1 là **hoàn thiện các tương tác động còn thiếu để phục vụ trực tiếp cho buổi Demo (Phân đoạn 3 & Phân đoạn 4)**:
1. **Hoàn thiện Trang Nguyện Vọng Giảng Viên (`PreferencesPage.tsx`)**:
   - Biến các ô khung giờ tĩnh thành **bộ chọn khung giờ tương tác linh hoạt** (click để chọn/bỏ chọn, lấy danh mục từ `GET /api/v1/time-slots`).
   - Gắn sự kiện cho nút **"Save Preferences"** gọi thẳng API `POST /api/v1/preferences` thông qua `preferenceService.submitPreference`.
   - Bổ sung kiểm tra hợp lệ phía client (bắt buộc chọn ít nhất 1 ngày và 1 khung giờ).
2. **Xây dựng Hệ thống Thông báo nổi (`Toast.tsx`)**:
   - Cung cấp component popup thông báo nổi (xanh khi thành công, đỏ khi gặp lỗi) tự động ẩn sau 4 giây.
3. **Hoàn thiện Bộ Lọc Lịch Học (`ScheduleFilters.tsx`) trên `SchedulePage.tsx`**:
   - Cho phép người dùng lọc lịch học theo **Khoa (Department: CS, ECE, MATH)** và **Giảng viên** trực tiếp trên FullCalendar mà không reload trang (Phục vụ Phân đoạn 4 của Demo).
4. **Xây dựng Tiện ích Xuất Lịch Học (`exportSchedule.ts`)**:
   - Thêm nút **"Export CSV"** trên `SchedulePage` để tải file lịch học `.csv` về máy tính với đầy đủ cột thông tin: Mã môn, Tên môn, Giảng viên, Phòng, Thứ, Giờ bắt đầu, Giờ kết thúc.
5. **Viết Bộ Kiểm Thử Tự Động Vitest**:
   - Đảm bảo viết đầy đủ unit test cho `PreferencesPage.test.tsx` và `ScheduleFilters.test.tsx` để đạt chỉ tiêu **> 400 LOC** trên Git.

---

## 2. Danh Sách Nhiệm Vụ Cụ Thể (Task Checklist)

```
[ ] Step 1: Tạo Git branch 'feature/tina-preference-schedule-ui' từ 'main' mới nhất
[ ] Step 2: Viết Component Toast thông báo ('frontend/src/components/common/Toast.tsx')
[ ] Step 3: Nâng cấp tương tác chọn Time Slots & gọi API thật trong 'frontend/src/pages/PreferencesPage.tsx'
[ ] Step 4: Viết tiện ích xuất thời khóa biểu ra CSV ('frontend/src/utils/exportSchedule.ts')
[ ] Step 5: Xây dựng thanh công cụ lọc lịch ('frontend/src/components/schedule/ScheduleFilters.tsx')
[ ] Step 6: Tích hợp ScheduleFilters và nút Export vào 'frontend/src/pages/SchedulePage.tsx'
[ ] Step 7: Viết bộ unit test Vitest ('PreferencesPage.test.tsx' và 'ScheduleFilters.test.tsx')
[ ] Step 8: Chạy kiểm thử tự động đạt 100% pass rate: 'npm test'
[ ] Step 9: Push branch lên GitHub và tạo Pull Request vào 'main'
[ ] Step 10: Tập dượt Phân đoạn 3 (1:45 - 2:45) cho video Demo 5 phút
```

---

## 3. Hướng Dẫn Kỹ Thuật Chi Tiết (Technical Guidance)

### Task 1: Reusable Toast Notification (`frontend/src/components/common/Toast.tsx`)
* **Vị trí file:** `frontend/src/components/common/Toast.tsx` (~80 LOC)
* **Chức năng:** Hiển thị popup góc màn hình khi người dùng lưu preferences hoặc thực hiện thao tác.
* **Props interface:**
  ```typescript
  export interface ToastProps {
    type: 'success' | 'error' | 'warning' | 'info';
    message: string;
    onClose: () => void;
  }
  ```

### Task 2: Cập Nhật Trang Nguyện Vọng (`frontend/src/pages/PreferencesPage.tsx`)
* **Vị trí file:** `frontend/src/pages/PreferencesPage.tsx` (~160 LOC)
* **Logic cần thêm:**
  1. **State quản lý:**
     ```typescript
     const [selectedDays, setSelectedDays] = useState<string[]>(['MWF']);
     const [selectedSlots, setSelectedSlots] = useState<string[]>([]);
     const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
     const [isSubmitting, setIsSubmitting] = useState(false);
     ```
  2. **Tương tác chọn khung giờ (Toggle Time Slot):**
     - Biến các card khung giờ thành nút bấm có trạng thái `selected`.
     - Khi click, thêm hoặc bớt khung giờ khỏi mảng `selectedSlots`.
     - Đổi màu sắc: khi được chọn có viền `border-blue-600 bg-blue-50 text-blue-700 font-semibold`.
  3. **Hàm xử lý khi bấm "Save Preferences":**
     ```typescript
     const handleSavePreferences = async () => {
       if (selectedDays.length === 0 || selectedSlots.length === 0) {
         setToast({ type: 'error', message: 'Vui lòng chọn ít nhất 1 ngày và 1 khung giờ!' });
         return;
       }
       try {
         setIsSubmitting(true);
         await preferenceService.submitPreference({
           user_id: Number(selectedInstructor),
           semester_id: 1,
           preferred_days: selectedDays,
           preferred_slots: selectedSlots,
           preferred_rooms: [],
         });
         setToast({ type: 'success', message: 'Lưu nguyện vọng giảng dạy thành công!' });
       } catch (err) {
         setToast({ type: 'error', message: 'Có lỗi xảy ra khi lưu nguyện vọng.' });
       } finally {
         setIsSubmitting(false);
       }
     };
     ```

### Task 3: Bộ Lọc Đa Chiều Lịch Học (`frontend/src/components/schedule/ScheduleFilters.tsx`)
* **Vị trí file:** `frontend/src/components/schedule/ScheduleFilters.tsx` (~110 LOC)
* **Chức năng:**
  - Dropdown lọc theo Khoa: `All Departments`, `CS`, `ECE`, `MATH`.
  - Input tìm kiếm theo tên Giảng viên hoặc Phòng học.
  - Nút bấm `Reset Filters`.
  - Callback `onFilterChange(filters)` truyền ngược lên `SchedulePage`.

### Task 4: Tiện Ích Xuất Thời Khóa Biểu (`frontend/src/utils/exportSchedule.ts`)
* **Vị trí file:** `frontend/src/utils/exportSchedule.ts` (~80 LOC)
* **Chức năng:** Chuyển đổi mảng `ScheduleEvent[]` thành định dạng CSV và kích hoạt tải file về máy.
  ```typescript
  export function exportScheduleToCSV(events: ScheduleEvent[], semesterName: string): void {
    const headers = ['Course Code', 'Course Name', 'Instructor', 'Room', 'Day Pattern', 'Start Time', 'End Time', 'Status'];
    const rows = events.map(e => [
      e.course_code,
      `"${e.course_name}"`,
      `"${e.instructor_name}"`,
      e.room_number,
      e.day_pattern,
      e.start_time,
      e.end_time,
      e.status
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `UMKC_Schedule_${semesterName.replace(/\s+/g, '_')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
  ```

### Task 5: Viết Bộ Unit Test Vitest Cho Tina
* **File 1:** `frontend/src/pages/__tests__/PreferencesPage.test.tsx` (~120 LOC)
  - Test chọn và bỏ chọn ngày dạy.
  - Test chọn và bỏ chọn khung giờ (time slots).
  - Test chặn gửi form khi chưa chọn ngày/giờ.
  - Test gọi API `submitPreference` thành công và hiện thông báo.
* **File 2:** `frontend/src/components/schedule/__tests__/ScheduleFilters.test.tsx` (~80 LOC)
  - Test thay đổi bộ lọc khoa (Department).
  - Test nút reset bộ lọc.

---

## 4. Bảng Kế Hoạch Đóng Góp Dòng Code (LOC) Của Tina

| Tên File | Loại | Mô tả công việc | LOC Dự Kiến |
| :--- | :--- | :--- | :---: |
| `frontend/src/components/common/Toast.tsx` | Production | Component popup thông báo thành công/lỗi | ~80 LOC |
| `frontend/src/pages/PreferencesPage.tsx` | Production | Tương tác chọn time-slot động & gọi API thật | ~160 LOC |
| `frontend/src/components/schedule/ScheduleFilters.tsx` | Production | Thanh lọc lịch theo Khoa và Giảng viên | ~110 LOC |
| `frontend/src/utils/exportSchedule.ts` | Production | Hàm xuất thời khóa biểu ra file CSV | ~80 LOC |
| `frontend/src/pages/SchedulePage.tsx` | Production | Gắn ScheduleFilters và nút Export vào trang | ~50 LOC |
| `frontend/src/pages/__tests__/PreferencesPage.test.tsx` | Test | Unit test cho trang Preferences | ~120 LOC |
| `frontend/src/components/schedule/__tests__/ScheduleFilters.test.tsx` | Test | Unit test cho bộ lọc ScheduleFilters | ~80 LOC |
| **TỔNG CỘNG** | | | **~680 LOC** |

👉 **Kết quả đạt được:** Tina sẽ có **~680 LOC** do chính mình commit trên Git, vượt xa ngưỡng tối thiểu 400 LOC và an toàn 100% khi giáo viên chấm điểm.

---

## 5. Phân Đoạn Demo Của Tina Trong Video 5 Phút

* **Thời lượng:** **Phân đoạn 3** (từ `1:45` đến `2:45` — đúng 60 giây).
* **Nội dung demo trực tiếp:**
  1. Mở trang `/preferences` trên trình duyệt.
  2. Chọn giảng viên (Dr. Yugyung Lee).
  3. Bấm chọn ngày `MWF` và click chọn 2 khung giờ `09:30 - 10:45` và `11:00 - 12:15`.
  4. Bấm nút **"Save Preferences"** $\rightarrow$ Chiếu rõ popup Toast màu xanh báo *"Lưu nguyện vọng thành công"*.
  5. Mở tab Network trên DevTools để chứng minh đã gửi request `POST /api/v1/preferences` với status code `200/201`.
