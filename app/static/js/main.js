/**
 * SAIGON GRAND LUXURY HOTEL - CLIENT JAVASCRIPT
 * Tích hợp WebSocket thời gian thực, quản lý Modal đặt phòng, Toast thông báo.
 */

// Bảng ánh xạ trạng thái sang class CSS
const STATUS_CLASS_MAP = {
  "Trống": "badge-trong",
  "Đã giữ": "badge-da-giu",
  "Đang ở": "badge-dang-o",
  "Cần dọn dẹp": "badge-can-don",
  "Bảo trì": "badge-bao-tri",
  "Chờ xác nhận": "badge-da-giu",
  "Đã xác nhận": "badge-da-giu",
  "Đã trả phòng": "badge-can-don",
  "Đã hủy": "badge-bao-tri"
};

// Khởi tạo kết nối WebSocket Realtime
function initRealtimeWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  const liveIndicator = document.getElementById("liveIndicator");
  const liveText = document.getElementById("liveText");

  let socket;

  function connect() {
    socket = new WebSocket(wsUrl);

    socket.onopen = function () {
      if (liveIndicator) liveIndicator.style.display = "inline-flex";
      if (liveText) liveText.textContent = "Realtime Đang Bật";
    };

    socket.onclose = function () {
      if (liveText) liveText.textContent = "Mất kết nối — Thử lại...";
      setTimeout(connect, 3000);
    };

    socket.onmessage = function (event) {
      try {
        const data = JSON.parse(event.data);
        handleRealtimeEvent(data);
      } catch (err) {
        console.error("Lỗi parse WebSocket message:", err);
      }
    };
  }

  connect();
}

// Xử lý các sự kiện Realtime gửi từ Server về
function handleRealtimeEvent(data) {
  // 1. Cập nhật trạng thái phòng tức thì
  if (data.type === "room_updated") {
    const roomId = data.room_id;
    const newStatus = data.new_status;

    // Cập nhật trên thẻ phòng (Trang chủ / Danh sách phòng)
    const badgeElements = document.querySelectorAll(`[data-room-badge="${roomId}"]`);
    badgeElements.forEach((badge) => {
      badge.textContent = newStatus;
      badge.className = `status-badge ${STATUS_CLASS_MAP[newStatus] || "badge-trong"}`;
    });

    // Cập nhật nút đặt phòng nếu phòng không còn trống
    const bookBtns = document.querySelectorAll(`[data-book-btn="${roomId}"]`);
    bookBtns.forEach((btn) => {
      if (newStatus !== "Trống") {
        btn.disabled = true;
        btn.textContent = newStatus;
        btn.classList.add("btn-secondary");
        btn.classList.remove("btn-primary");
      } else {
        btn.disabled = false;
        btn.textContent = "Đặt Phòng";
        btn.classList.add("btn-primary");
        btn.classList.remove("btn-secondary");
      }
    });

    // Nếu đang ở Dashboard Lễ tân: cập nhật ma trận phòng
    const matrixCard = document.getElementById(`matrix-room-${roomId}`);
    if (matrixCard) {
      matrixCard.setAttribute("data-status", newStatus);
      const mBadge = matrixCard.querySelector(".matrix-badge");
      if (mBadge) {
        mBadge.textContent = newStatus;
        mBadge.className = `status-badge matrix-badge ${STATUS_CLASS_MAP[newStatus] || "badge-trong"}`;
      }
    }
  }

  // 2. Có khách đặt phòng mới -> Thông báo chuông cho Lễ tân
  if (data.type === "new_booking") {
    const booking = data.booking;
    showToast(`🛎️ Đơn mới: Phòng ${booking.SoPhong || booking.MaPhong} (${booking.TenKhachHang})`, "success");

    // Nếu đang ở màn hình Lễ tân, tự động chèn dòng mới vào bảng
    const bookingTbody = document.getElementById("receptionistBookingTableBody");
    if (bookingTbody) {
      const newRow = document.createElement("tr");
      newRow.id = `booking-row-${booking.MaDatPhong}`;
      newRow.innerHTML = `
        <td><strong>#${booking.MaDatPhong}</strong></td>
        <td><span class="room-number">P.${booking.SoPhong || booking.MaPhong}</span></td>
        <td>
          <strong>${booking.TenKhachHang}</strong><br>
          <small class="text-muted">${booking.SoDienThoai}</small>
        </td>
        <td>${booking.NgayNhan} ➔ ${booking.NgayTra}</td>
        <td><strong class="text-gold">${Number(booking.TongTien || 0).toLocaleString("vi-VN")} đ</strong></td>
        <td><span class="status-badge badge-da-giu">${booking.TrangThai}</span></td>
        <td>
          <button onclick="updateBooking('${booking.MaDatPhong}', 'Đang ở')" class="btn btn-sm btn-primary">Nhận phòng</button>
        </td>
      `;
      bookingTbody.prepend(newRow);
    }
  }

  // 3. Đơn đặt phòng thay đổi trạng thái
  if (data.type === "booking_status_changed") {
    const row = document.getElementById(`booking-row-${data.booking_id}`);
    if (row) {
      const badge = row.querySelector(".status-badge");
      if (badge) {
        badge.textContent = data.new_status;
        badge.className = `status-badge ${STATUS_CLASS_MAP[data.new_status] || "badge-da-giu"}`;
      }
    }
  }
}

// Hàm hiển thị Toast thông báo nổi
function showToast(message, type = "info") {
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = "toast";
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

// Modal đặt phòng cho khách hàng
function openBookingModal(roomId, roomNumber, roomType, price) {
  const modal = document.getElementById("bookingModal");
  if (!modal) return;

  document.getElementById("modalRoomId").value = roomId;
  document.getElementById("modalRoomNumber").textContent = roomNumber;
  document.getElementById("modalRoomType").textContent = roomType;
  document.getElementById("modalRoomPrice").textContent = Number(price).toLocaleString("vi-VN") + " đ/đêm";
  
  modal.classList.add("active");
}

function closeBookingModal() {
  const modal = document.getElementById("bookingModal");
  if (modal) modal.classList.remove("active");
}

// Tự động khởi chạy WebSocket khi trang tải xong
document.addEventListener("DOMContentLoaded", function () {
  initRealtimeWebSocket();
});
