/**
 * Quick Maintenance Tracker - Frontend Application Controller
 * Enterprise Edition with Authentication, Role-Based Access Control & Theme Switcher
 */

// ==========================================================================
// 1. API Configuration & Auto-detection
// ==========================================================================
function resolveApiBase() {
    if (window.location.protocol === 'file:') {
        return 'http://127.0.0.1:8000/api';
    }
    if (window.location.port !== '8000') {
        return 'http://127.0.0.1:8000/api';
    }
    return '/api';
}

const API_URL = resolveApiBase();

function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    return headers;
}

// ==========================================================================
// 2. Global State
// ==========================================================================
const state = {
    token: localStorage.getItem('qmt_token') || null,
    currentUser: null,
    users: [],
    equipments: [],
    tickets: [],
    stats: null,
    activeTab: 'tickets', // 'tickets' | 'equipments' | 'users'
    filters: {
        ticketSearch: '',
        ticketStatus: 'All',
        ticketPriority: 'All',
        eqSearch: '',
        eqCategory: 'All',
        eqStatus: 'All'
    }
};

// ==========================================================================
// 3. Theme Manager (Light & Dark Mode)
// ==========================================================================
function initTheme() {
    const savedTheme = localStorage.getItem('qmt_theme') || 'light';
    applyTheme(savedTheme);

    const toggleBtn = document.getElementById('themeToggleBtn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            applyTheme(newTheme);
        });
    }
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('qmt_theme', theme);

    const toggleBtn = document.getElementById('themeToggleBtn');
    if (toggleBtn) {
        if (theme === 'dark') {
            toggleBtn.innerHTML = '<i class="fa-solid fa-sun"></i>';
            toggleBtn.title = 'เปลี่ยนเป็นธีมขาว (Light Mode)';
        } else {
            toggleBtn.innerHTML = '<i class="fa-solid fa-moon"></i>';
            toggleBtn.title = 'เปลี่ยนเป็นธีมดำ (Dark Mode)';
        }
    }
}

// ==========================================================================
// 4. Initialization & Session Check
// ==========================================================================
document.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    setupEventListeners();
    await checkAuthSession();
    fetchBoardData();
});

async function checkAuthSession() {
    if (!state.token) {
        updateAuthUI();
        return;
    }

    try {
        const res = await fetch(`${API_URL}/auth/me`, {
            headers: getAuthHeaders()
        });

        if (res.ok) {
            state.currentUser = await res.json();
        } else {
            // Token expired or invalid
            state.token = null;
            state.currentUser = null;
            localStorage.removeItem('qmt_token');
        }
    } catch (err) {
        console.error('Session check failed:', err);
    }
    updateAuthUI();
}

function updateAuthUI() {
    const guestGroup = document.getElementById('guestAuthGroup');
    const userGroup = document.getElementById('userProfileGroup');
    const userName = document.getElementById('headerUserName');
    const userRole = document.getElementById('headerUserRole');
    const userAvatar = document.getElementById('headerUserAvatar');
    const tabUsersBtn = document.getElementById('tabUsersBtn');
    const resetDemoBtn = document.getElementById('resetDemoBtn');

    if (state.currentUser) {
        if (guestGroup) guestGroup.style.display = 'none';
        if (userGroup) userGroup.style.display = 'flex';

        if (userName) userName.textContent = state.currentUser.full_name;
        if (userAvatar) userAvatar.textContent = (state.currentUser.full_name || 'U').charAt(0).toUpperCase();

        if (userRole) {
            userRole.textContent = state.currentUser.role.toUpperCase();
            userRole.className = `role-badge role-${state.currentUser.role}`;
        }

        // แท็บจัดการผู้ใช้งาน: แสดงเฉพาะเมื่อเป็น Admin
        if (tabUsersBtn) {
            tabUsersBtn.style.display = state.currentUser.role === 'admin' ? 'inline-flex' : 'none';
        }

        // ปุ่มรีเซ็ต Demo: ให้เห็นเสมอ แต่มีเงื่อนไขสิทธิ์ตอนกด
        if (resetDemoBtn) {
            resetDemoBtn.style.display = 'inline-flex';
        }
    } else {
        if (guestGroup) guestGroup.style.display = 'flex';
        if (userGroup) userGroup.style.display = 'none';
        if (tabUsersBtn) tabUsersBtn.style.display = 'none';
    }
}

// ==========================================================================
// 5. Authentication Controllers (Login, Register, Logout)
// ==========================================================================

function openLoginModal() {
    openModal('loginModal');
}

function openRegisterModal() {
    openModal('registerModal');
}

function switchToRegister() {
    closeModal('loginModal');
    openModal('registerModal');
}

function switchToLogin() {
    closeModal('registerModal');
    openModal('loginModal');
}

async function quickLogin(role) {
    const creds = {
        admin: { u: 'admin', p: 'admin123' },
        technician: { u: 'technician', p: 'tech123' },
        user: { u: 'user', p: 'user123' }
    };
    const target = creds[role] || creds.user;
    await performLogin(target.u, target.p);
}

async function submitLogin(e) {
    e.preventDefault();
    const u = document.getElementById('loginUsername').value.trim();
    const p = document.getElementById('loginPassword').value;
    await performLogin(u, p);
}

async function performLogin(username, password) {
    try {
        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'เข้าสู่ระบบไม่สำเร็จ กรุณาตรวจสอบชื่อผู้ใช้หรือรหัสผ่าน');
        }

        const data = await res.json();
        state.token = data.token;
        state.currentUser = data.user;
        localStorage.setItem('qmt_token', data.token);

        closeModal('loginModal');
        updateAuthUI();

        showToast(`ยินดีต้อนรับคุณ "${data.user.full_name}" (สิทธิ์: ${data.user.role.toUpperCase()})`, 'success');
        fetchBoardData();

        if (state.currentUser.role === 'admin' && state.activeTab === 'users') {
            fetchUsers();
        }
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function submitRegister(e) {
    e.preventDefault();
    const username = document.getElementById('regUsername').value.trim();
    const full_name = document.getElementById('regFullName').value.trim();
    const password = document.getElementById('regPassword').value;
    const role = document.getElementById('regRole').value;

    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, full_name, password, role })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'สมัครสมาชิกไม่สำเร็จ');
        }

        const data = await res.json();
        state.token = data.token;
        state.currentUser = data.user;
        localStorage.setItem('qmt_token', data.token);

        closeModal('registerModal');
        updateAuthUI();

        showToast(`สมัครสมาชิกสำเร็จ! ยินดีต้อนรับคุณ "${data.user.full_name}"`, 'success');
        fetchBoardData();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function logout() {
    state.token = null;
    state.currentUser = null;
    localStorage.removeItem('qmt_token');

    if (state.activeTab === 'users') {
        switchTab('tickets');
    }

    updateAuthUI();
    showToast('ออกจากระบบเรียบร้อยแล้ว', 'info');
}

// ==========================================================================
// 6. Data Fetching & Dashboard Render
// ==========================================================================

async function fetchBoardData() {
    try {
        const res = await fetch(`${API_URL}/board`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const data = await res.json();

        state.stats = data.stats || {};
        state.equipments = data.equipments || [];
        state.tickets = data.tickets || [];

        updateApiStatus(true);
        renderStats();
        renderTickets();
        renderEquipments();
        populateEquipmentDropdown();
        populateCategoryFilter();
        updateTabBadges();
    } catch (err) {
        console.error('Error fetching board data:', err);
        updateApiStatus(false);
        showToast('ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ Backend ได้ กรุณารัน "python main.py"', 'error', 6000);
    }
}

function updateApiStatus(isOnline) {
    const pill = document.getElementById('apiStatusPill');
    const text = document.getElementById('apiStatusText');
    if (!pill || !text) return;

    if (isOnline) {
        pill.className = 'status-pill';
        text.textContent = 'เชื่อมต่อระบบสำเร็จ';
    } else {
        pill.className = 'status-pill offline';
        text.textContent = 'เซิร์ฟเวอร์ออฟไลน์';
    }
}

function renderStats() {
    if (!state.stats) return;
    const s = state.stats;
    document.getElementById('statTotalEquipments').textContent = s.total_equipments || 0;
    document.getElementById('statUptimeDesc').textContent = `ความพร้อมใช้งาน: ${s.uptime_percentage ?? 100}%`;
    document.getElementById('statOperational').textContent = s.operational_count || 0;
    document.getElementById('statNeedsMaint').textContent = (s.needs_maintenance_count || 0) + (s.under_repair_count || 0);

    const pending = (s.open_tickets_count || 0) + (s.in_progress_tickets_count || 0);
    document.getElementById('statPendingTickets').textContent = pending;
    document.getElementById('statInProgressDesc').textContent = `กำลังซ่อม ${s.in_progress_tickets_count || 0} เคส`;
    document.getElementById('statUrgentTickets').textContent = s.urgent_tickets_count || 0;
}

function updateTabBadges() {
    const ticketBadge = document.getElementById('badgeTicketsCount');
    const eqBadge = document.getElementById('badgeEquipmentsCount');
    const userBadge = document.getElementById('badgeUsersCount');
    if (ticketBadge) ticketBadge.textContent = state.tickets.length;
    if (eqBadge) eqBadge.textContent = state.equipments.length;
    if (userBadge) userBadge.textContent = state.users.length;
}

// 6.1 Render Tickets
function renderTickets() {
    const tbody = document.getElementById('ticketTableBody');
    const emptyState = document.getElementById('ticketEmptyState');
    if (!tbody) return;

    const filtered = state.tickets.filter(tk => {
        const search = state.filters.ticketSearch.toLowerCase().trim();
        const matchesSearch = !search ||
            (tk.id && tk.id.toLowerCase().includes(search)) ||
            (tk.title && tk.title.toLowerCase().includes(search)) ||
            (tk.description && tk.description.toLowerCase().includes(search)) ||
            (tk.equipment_name && tk.equipment_name.toLowerCase().includes(search)) ||
            (tk.equipment_id && tk.equipment_id.toLowerCase().includes(search));

        const matchesStatus = state.filters.ticketStatus === 'All' || tk.status === state.filters.ticketStatus;
        const matchesPriority = state.filters.ticketPriority === 'All' || tk.priority === state.filters.ticketPriority;

        return matchesSearch && matchesStatus && matchesPriority;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';

    tbody.innerHTML = filtered.map(tk => {
        let priorityClass = 'priority-medium';
        let priorityIcon = 'fa-circle-exclamation';
        if (tk.priority === 'Urgent') { priorityClass = 'priority-urgent'; priorityIcon = 'fa-fire'; }
        else if (tk.priority === 'High') { priorityClass = 'priority-high'; priorityIcon = 'fa-triangle-exclamation'; }
        else if (tk.priority === 'Low') { priorityClass = 'priority-low'; priorityIcon = 'fa-arrow-down'; }

        let statusClass = 'badge-open';
        let statusIcon = 'fa-clock';
        if (tk.status === 'In Progress') { statusClass = 'badge-in-progress'; statusIcon = 'fa-spinner fa-spin'; }
        else if (tk.status === 'Resolved') { statusClass = 'badge-resolved'; statusIcon = 'fa-check'; }
        else if (tk.status === 'Closed') { statusClass = 'badge-closed'; statusIcon = 'fa-box-archive'; }

        const eqName = tk.equipment_name ? `${tk.equipment_name} (${tk.equipment_id})` : tk.equipment_id;
        const safeNotes = tk.notes ? `<div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;"><i class="fa-solid fa-comment-dots"></i> โน้ต: ${escapeHtml(tk.notes)}</div>` : '';

        return `
            <tr>
                <td><span class="code-badge">${tk.id}</span></td>
                <td>
                    <div style="font-weight: 600;">${escapeHtml(eqName)}</div>
                    ${tk.equipment_location ? `<div style="font-size: 0.75rem; color: var(--text-muted);"><i class="fa-solid fa-location-dot"></i> ${escapeHtml(tk.equipment_location)}</div>` : ''}
                </td>
                <td>
                    <div style="font-weight: 600; color: var(--text-primary);">${escapeHtml(tk.title)}</div>
                    <div style="font-size: 0.78rem; color: var(--text-secondary); max-width: 320px; white-space: normal; line-height: 1.35; margin-top: 2px;">
                        ${escapeHtml(tk.description || '-')}
                    </div>
                    ${tk.created_by ? `<div style="font-size: 0.73rem; color: var(--primary); margin-top: 3px;"><i class="fa-solid fa-user-pen"></i> แจ้งโดย: <b>${escapeHtml(tk.created_by)}</b></div>` : ''}
                    ${safeNotes}
                </td>
                <td>
                    <span class="badge ${priorityClass}">
                        <i class="fa-solid ${priorityIcon}"></i> ${tk.priority}
                    </span>
                </td>
                <td>
                    ${tk.assigned_to 
                        ? `<div style="display: inline-flex; align-items: center; gap: 6px; font-weight: 500;"><i class="fa-solid fa-user-gear" style="color: var(--primary);"></i> ${escapeHtml(tk.assigned_to)}</div>` 
                        : '<span style="color: var(--text-muted); font-size: 0.8rem;">- ยังไม่ระบุ -</span>'}
                </td>
                <td>
                    <span class="badge ${statusClass}">
                        <i class="fa-solid ${statusIcon}"></i> ${tk.status}
                    </span>
                </td>
                <td style="font-size: 0.8rem; color: var(--text-secondary); white-space: nowrap;">
                    ${tk.created_at || '-'}
                </td>
                <td style="text-align: right;">
                    <div class="action-cell" style="justify-content: flex-end;">
                        <button class="btn btn-secondary btn-sm" onclick="openUpdateTicketModal('${tk.id}')" title="อัปเดตสถานะ / มอบหมายช่าง">
                            <i class="fa-solid fa-pen-to-square"></i>
                            <span>จัดการ</span>
                        </button>
                        <button class="btn-icon btn-icon-danger" onclick="deleteTicketConfirm('${tk.id}')" title="ลบใบแจ้งซ่อมนี้">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// 6.2 Render Equipments
function renderEquipments() {
    const tbody = document.getElementById('equipmentTableBody');
    const emptyState = document.getElementById('eqEmptyState');
    if (!tbody) return;

    const filtered = state.equipments.filter(eq => {
        const search = state.filters.eqSearch.toLowerCase().trim();
        const matchesSearch = !search ||
            (eq.id && eq.id.toLowerCase().includes(search)) ||
            (eq.name && eq.name.toLowerCase().includes(search)) ||
            (eq.location && eq.location.toLowerCase().includes(search));

        const matchesCategory = state.filters.eqCategory === 'All' || eq.category === state.filters.eqCategory;
        const matchesStatus = state.filters.eqStatus === 'All' || eq.status === state.filters.eqStatus;

        return matchesSearch && matchesCategory && matchesStatus;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';

    tbody.innerHTML = filtered.map(eq => {
        let statusBadge = 'badge-operational';
        let statusIcon = 'fa-circle-check';
        if (eq.status === 'Needs Maintenance') { statusBadge = 'badge-maintenance'; statusIcon = 'fa-triangle-exclamation'; }
        else if (eq.status === 'Under Repair') { statusBadge = 'badge-repair'; statusIcon = 'fa-wrench'; }

        return `
            <tr>
                <td><span class="code-badge">${eq.id}</span></td>
                <td>
                    <div style="font-weight: 600;">${escapeHtml(eq.name)}</div>
                </td>
                <td>
                    <div style="font-size: 0.85rem;"><i class="fa-solid fa-location-dot" style="color: var(--text-muted); margin-right: 4px;"></i> ${escapeHtml(eq.location)}</div>
                </td>
                <td>
                    <span style="display: inline-block; padding: 3px 8px; border-radius: 4px; background: var(--bg-surface-secondary); border: 1px solid var(--border-color); font-size: 0.78rem;">
                        ${escapeHtml(eq.category)}
                    </span>
                </td>
                <td>
                    <span class="badge ${statusBadge}">
                        <i class="fa-solid ${statusIcon}"></i> ${eq.status}
                    </span>
                </td>
                <td style="font-size: 0.8rem; color: var(--text-secondary); white-space: nowrap;">
                    ${eq.created_at || '-'}
                </td>
                <td style="text-align: right;">
                    <div class="action-cell" style="justify-content: flex-end;">
                        <button class="btn btn-secondary btn-sm" onclick="openEquipmentDetailModal('${eq.id}')" title="ดูประวัติการซ่อม">
                            <i class="fa-solid fa-circle-info"></i>
                            <span>ประวัติ</span>
                        </button>
                        <button class="btn-icon btn-icon-danger" onclick="deleteEquipmentConfirm('${eq.id}')" title="ลบอุปกรณ์">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// 6.3 Render Users (Admin Only)
async function fetchUsers() {
    if (!state.token || !state.currentUser || state.currentUser.role !== 'admin') {
        return;
    }

    try {
        const res = await fetch(`${API_URL}/admin/users`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('ไม่สามารถดึงข้อมูลผู้ใช้งานได้');
        state.users = await res.json();
        renderUsers();
        updateTabBadges();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function renderUsers() {
    const tbody = document.getElementById('userTableBody');
    const emptyState = document.getElementById('userEmptyState');
    if (!tbody) return;

    if (state.users.length === 0) {
        tbody.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';

    tbody.innerHTML = state.users.map(u => {
        const isCurrent = state.currentUser && state.currentUser.id === u.id;
        return `
            <tr>
                <td><span class="code-badge">${u.id}</span></td>
                <td><b>${escapeHtml(u.username)}</b> ${isCurrent ? '<span style="font-size: 0.72rem; color: var(--primary);">(คุณ)</span>' : ''}</td>
                <td>${escapeHtml(u.full_name)}</td>
                <td>
                    <span class="role-badge role-${u.role}">${u.role.toUpperCase()}</span>
                </td>
                <td style="font-size: 0.8rem; color: var(--text-secondary);">${u.created_at}</td>
                <td style="text-align: right;">
                    <div class="action-cell" style="justify-content: flex-end; gap: 8px;">
                        <select class="select-filter" style="padding: 4px 8px; font-size: 0.8rem;" onchange="changeUserRole('${u.id}', this.value)" ${isCurrent ? 'disabled title="ไม่สามารถเปลี่ยนสิทธิ์ของตนเองได้"' : ''}>
                            <option value="user" ${u.role === 'user' ? 'selected' : ''}>User (ผู้ใช้)</option>
                            <option value="technician" ${u.role === 'technician' ? 'selected' : ''}>Technician (ช่าง)</option>
                            <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin (ผู้ดูแล)</option>
                        </select>
                        <button class="btn-icon btn-icon-danger" onclick="deleteUserConfirm('${u.id}', '${escapeHtml(u.username)}')" ${isCurrent ? 'disabled style="opacity: 0.4; cursor: not-allowed;"' : ''} title="ลบผู้ใช้">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

async function changeUserRole(userId, newRole) {
    try {
        const res = await fetch(`${API_URL}/admin/users/${userId}/role`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify({ role: newRole })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'ไม่สามารถปรับเปลี่ยนสิทธิ์ได้');
        }

        showToast(`ปรับสิทธิ์ผู้ใช้เป็น ${newRole.toUpperCase()} สำเร็จ`, 'success');
        fetchUsers();
    } catch (err) {
        showToast(err.message, 'error');
        fetchUsers();
    }
}

async function deleteUserConfirm(userId, username) {
    if (!confirm(`ยืนยันการลบบัญชีผู้ใช้ "${username}" หรือไม่?`)) {
        return;
    }

    try {
        const res = await fetch(`${API_URL}/admin/users/${userId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'ไม่สามารถลบผู้ใช้ได้');
        }

        showToast(`ลบบัญชี "${username}" เรียบร้อยแล้ว`, 'success');
        fetchUsers();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==========================================================================
// 7. Navigation & Tabs
// ==========================================================================

function switchTab(tab) {
    state.activeTab = tab;

    const ticketsBtn = document.getElementById('tabTicketsBtn');
    const eqBtn = document.getElementById('tabEquipmentsBtn');
    const usersBtn = document.getElementById('tabUsersBtn');

    const ticketsSec = document.getElementById('ticketsSection');
    const eqSec = document.getElementById('equipmentsSection');
    const usersSec = document.getElementById('usersSection');

    const ticketCtrl = document.getElementById('ticketControlCard');
    const eqCtrl = document.getElementById('eqControlCard');
    const actionBtn = document.getElementById('tabActionBtn');
    const actionBtnText = document.getElementById('tabActionBtnText');

    // Reset All Tabs
    [ticketsBtn, eqBtn, usersBtn].forEach(b => b && b.classList.remove('active'));
    [ticketsSec, eqSec, usersSec].forEach(s => s && (s.style.display = 'none'));
    if (ticketCtrl) ticketCtrl.style.display = 'none';
    if (eqCtrl) eqCtrl.style.display = 'none';

    if (tab === 'tickets') {
        ticketsBtn.classList.add('active');
        ticketsSec.style.display = 'block';
        if (ticketCtrl) ticketCtrl.style.display = 'flex';
        if (actionBtn) actionBtn.style.display = 'inline-flex';
        if (actionBtnText) actionBtnText.textContent = 'แจ้งซ่อมใหม่';
    } else if (tab === 'equipments') {
        eqBtn.classList.add('active');
        eqSec.style.display = 'block';
        if (eqCtrl) eqCtrl.style.display = 'flex';
        if (actionBtn) actionBtn.style.display = 'inline-flex';
        if (actionBtnText) actionBtnText.textContent = 'เพิ่มอุปกรณ์ใหม่';
    } else if (tab === 'users') {
        if (usersBtn) usersBtn.classList.add('active');
        if (usersSec) usersSec.style.display = 'block';
        if (actionBtn) actionBtn.style.display = 'none';
        fetchUsers();
    }
}

function handlePrimaryAction() {
    if (state.activeTab === 'tickets') {
        openTicketModal();
    } else if (state.activeTab === 'equipments') {
        openEquipmentModal();
    }
}

// ==========================================================================
// 8. Modals & Forms
// ==========================================================================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('active');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
}

// 8.1 Ticket Operations
function openTicketModal(preSelectedEqId = null) {
    const form = document.getElementById('newTicketForm');
    if (form) form.reset();
    populateEquipmentDropdown();

    if (preSelectedEqId) {
        const select = document.getElementById('ticketEquipmentSelect');
        if (select) select.value = preSelectedEqId;
    }

    openModal('ticketModal');
}

async function submitNewTicket(e) {
    e.preventDefault();

    const eqId = document.getElementById('ticketEquipmentSelect').value;
    const title = document.getElementById('ticketTitleInput').value.trim();
    const desc = document.getElementById('ticketDescInput').value.trim();
    const priority = document.getElementById('ticketPrioritySelect').value;

    if (!eqId || !title || !desc) {
        showToast('กรุณากรอกข้อมูลให้ครบทุกช่อง', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_URL}/tickets`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                equipment_id: eqId,
                title: title,
                description: desc,
                priority: priority
            })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'เกิดข้อผิดพลาดในการบันทึกข้อมูล');
        }

        const newTk = await res.json();
        closeModal('ticketModal');
        showToast(`สร้างใบแจ้งซ่อมรหัส "${newTk.id}" สำเร็จแล้ว!`, 'success');
        fetchBoardData();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function openUpdateTicketModal(ticketId) {
    const tk = state.tickets.find(t => t.id === ticketId);
    if (!tk) return;

    document.getElementById('updateTicketIdHidden').value = tk.id;
    document.getElementById('updateTicketIdDisplay').textContent = tk.id;
    document.getElementById('updateTicketStatusSelect').value = tk.status;

    // ถ้าผู้ใช้ล็อกอินเป็นช่าง และยังไม่มีผู้รับผิดชอบ ให้ใส่ชื่อตนเองเป็นค่าเริ่มต้น
    const currentTech = tk.assigned_to || (state.currentUser && state.currentUser.role === 'technician' ? state.currentUser.full_name : '');
    document.getElementById('updateTechnicianInput').value = currentTech;
    document.getElementById('updateNotesInput').value = tk.notes || '';

    openModal('updateTicketModal');
}

async function submitUpdateTicket(e) {
    e.preventDefault();

    const ticketId = document.getElementById('updateTicketIdHidden').value;
    const status = document.getElementById('updateTicketStatusSelect').value;
    const technician = document.getElementById('updateTechnicianInput').value.trim() || null;
    const notes = document.getElementById('updateNotesInput').value.trim() || null;

    try {
        const res = await fetch(`${API_URL}/tickets/${ticketId}`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify({ status, technician, notes })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'ไม่สามารถอัปเดตข้อมูลได้');
        }

        closeModal('updateTicketModal');
        showToast(`อัปเดตสถานะใบแจ้งซ่อม "${ticketId}" สำเร็จ`, 'success');
        fetchBoardData();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteTicketConfirm(ticketId) {
    if (!confirm(`ยืนยันการลบใบแจ้งซ่อมรหัส "${ticketId}" หรือไม่?`)) {
        return;
    }

    try {
        const res = await fetch(`${API_URL}/tickets/${ticketId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!res.ok) throw new Error('ไม่สามารถลบใบแจ้งซ่อมได้');

        showToast(`ลบใบแจ้งซ่อม "${ticketId}" สำเร็จ`, 'success');
        fetchBoardData();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// 8.2 Equipment Operations
function openEquipmentModal() {
    const form = document.getElementById('newEquipmentForm');
    if (form) form.reset();
    openModal('equipmentModal');
}

async function submitNewEquipment(e) {
    e.preventDefault();

    const name = document.getElementById('eqNameInput').value.trim();
    const location = document.getElementById('eqLocationInput').value.trim();
    const category = document.getElementById('eqCategoryInput').value.trim();

    if (!name || !location || !category) {
        showToast('กรุณากรอกข้อมูลอุปกรณ์ให้ครบถ้วน', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_URL}/equipments`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ name, location, category })
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'ไม่สามารถลงทะเบียนอุปกรณ์ได้');
        }

        const newEq = await res.json();
        closeModal('equipmentModal');
        showToast(`ลงทะเบียนอุปกรณ์ "${newEq.id} - ${newEq.name}" สำเร็จ`, 'success');
        fetchBoardData();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function openEquipmentDetailModal(equipmentId) {
    try {
        const res = await fetch(`${API_URL}/equipments/${equipmentId}`);
        if (!res.ok) throw new Error('ไม่สามารถดึงข้อมูลอุปกรณ์ได้');
        const eq = await res.json();

        const content = document.getElementById('eqDetailContent');
        content.innerHTML = `
            <div style="background-color: var(--bg-surface-secondary); padding: 14px 18px; border-radius: var(--radius-md); border: 1px solid var(--border-color); margin-bottom: 16px;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                    <span class="code-badge">${eq.id}</span>
                    <span class="badge ${eq.status === 'Operational' ? 'badge-operational' : (eq.status === 'Needs Maintenance' ? 'badge-maintenance' : 'badge-repair')}">
                        ${eq.status}
                    </span>
                </div>
                <h3 style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">${escapeHtml(eq.name)}</h3>
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 2px;">
                    <i class="fa-solid fa-location-dot" style="color: var(--primary);"></i> <b>สถานที่:</b> ${escapeHtml(eq.location)}
                </div>
                <div style="font-size: 0.85rem; color: var(--text-secondary);">
                    <i class="fa-solid fa-layer-group" style="color: var(--primary);"></i> <b>หมวดหมู่:</b> ${escapeHtml(eq.category)}
                </div>
            </div>
        `;

        const historyContainer = document.getElementById('eqTicketHistoryContainer');
        const tickets = eq.tickets || [];

        if (tickets.length === 0) {
            historyContainer.innerHTML = `
                <div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
                    <i class="fa-solid fa-circle-check" style="color: var(--status-success); font-size: 1.6rem; margin-bottom: 8px; display: block;"></i>
                    อุปกรณ์นี้ไม่เคยมีประวัติการแจ้งซ่อม (สภาพการทำงานสมบูรณ์ 100%)
                </div>
            `;
        } else {
            historyContainer.innerHTML = `
                <div class="history-timeline">
                    ${tickets.map(t => `
                        <div class="history-item">
                            <div class="history-content">
                                <div class="history-header">
                                    <span class="history-title">${escapeHtml(t.title)}</span>
                                    <span class="badge ${t.status === 'Resolved' || t.status === 'Closed' ? 'badge-resolved' : 'badge-open'}">${t.status}</span>
                                </div>
                                <div class="history-body">${escapeHtml(t.description || '-')}</div>
                                <div class="history-date">
                                    <i class="fa-regular fa-clock"></i> ${t.created_at} 
                                    ${t.assigned_to ? ` | <i class="fa-solid fa-user"></i> ช่าง: ${escapeHtml(t.assigned_to)}` : ''}
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        openModal('equipmentDetailModal');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteEquipmentConfirm(equipmentId) {
    if (!state.currentUser || state.currentUser.role !== 'admin') {
        showToast('เฉพาะผู้ดูแลระบบ (Admin) เท่านั้นที่สามารถลบอุปกรณ์ได้', 'error');
        return;
    }

    if (!confirm(`ต้องการลบอุปกรณ์ "${equipmentId}" ใช่หรือไม่? ประวัติการแจ้งซ่อมทั้งหมดของอุปกรณ์นี้จะถูกลบไปด้วย`)) {
        return;
    }

    try {
        const res = await fetch(`${API_URL}/equipments/${equipmentId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!res.ok) throw new Error('ไม่สามารถลบอุปกรณ์ได้');

        showToast(`ลบอุปกรณ์ "${equipmentId}" เรียบร้อยแล้ว`, 'success');
        fetchBoardData();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// 8.3 Reset Demo Data
async function resetDemoData() {
    if (state.currentUser && state.currentUser.role !== 'admin') {
        showToast('เฉพาะผู้ดูแลระบบ (Admin) เท่านั้นที่สามารถรีเซ็ตข้อมูลระบบได้', 'error');
        return;
    }

    if (!confirm('ต้องการรีเซ็ตข้อมูลตัวอย่างทั้งหมดหรือไม่? ข้อมูลเดิมจะถูกแทนที่ด้วยข้อมูลตั้งต้นสำหรับการ Demo')) {
        return;
    }

    try {
        const res = await fetch(`${API_URL}/reset-demo`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('เกิดข้อผิดพลาดในการรีเซ็ตข้อมูล');

        showToast('รีเซ็ตข้อมูลตัวอย่างสำเร็จเรียบร้อย!', 'success');
        fetchBoardData();
        if (state.currentUser && state.currentUser.role === 'admin' && state.activeTab === 'users') {
            fetchUsers();
        }
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Dropdown Populators
function populateEquipmentDropdown() {
    const select = document.getElementById('ticketEquipmentSelect');
    if (!select) return;

    if (state.equipments.length === 0) {
        select.innerHTML = '<option value="">-- ไม่พบรายการอุปกรณ์ (กรุณาเพิ่มอุปกรณ์ก่อน) --</option>';
        return;
    }

    select.innerHTML = '<option value="">-- เลือกอุปกรณ์ที่ต้องการแจ้งซ่อม --</option>' +
        state.equipments.map(eq => `
            <option value="${eq.id}">[${eq.id}] ${eq.name} (${eq.location})</option>
        `).join('');
}

function populateCategoryFilter() {
    const select = document.getElementById('eqCategoryFilter');
    if (!select) return;

    const categories = Array.from(new Set(state.equipments.map(e => e.category).filter(Boolean)));
    const currentVal = state.filters.eqCategory;

    select.innerHTML = '<option value="All">ทุกหมวดหมู่</option>' +
        categories.map(c => `
            <option value="${escapeHtml(c)}" ${c === currentVal ? 'selected' : ''}>${escapeHtml(c)}</option>
        `).join('');
}

// ==========================================================================
// 9. Event Listeners Setup
// ==========================================================================
function setupEventListeners() {
    const headerNewTicketBtn = document.getElementById('headerNewTicketBtn');
    if (headerNewTicketBtn) {
        headerNewTicketBtn.addEventListener('click', () => openTicketModal());
    }

    const resetDemoBtn = document.getElementById('resetDemoBtn');
    if (resetDemoBtn) {
        resetDemoBtn.addEventListener('click', resetDemoData);
    }

    // Ticket Filters
    const ticketSearch = document.getElementById('ticketSearchInput');
    if (ticketSearch) {
        ticketSearch.addEventListener('input', (e) => {
            state.filters.ticketSearch = e.target.value;
            renderTickets();
        });
    }

    const ticketStatus = document.getElementById('ticketStatusFilter');
    if (ticketStatus) {
        ticketStatus.addEventListener('change', (e) => {
            state.filters.ticketStatus = e.target.value;
            renderTickets();
        });
    }

    const ticketPriority = document.getElementById('ticketPriorityFilter');
    if (ticketPriority) {
        ticketPriority.addEventListener('change', (e) => {
            state.filters.ticketPriority = e.target.value;
            renderTickets();
        });
    }

    // Equipment Filters
    const eqSearch = document.getElementById('eqSearchInput');
    if (eqSearch) {
        eqSearch.addEventListener('input', (e) => {
            state.filters.eqSearch = e.target.value;
            renderEquipments();
        });
    }

    const eqCategory = document.getElementById('eqCategoryFilter');
    if (eqCategory) {
        eqCategory.addEventListener('change', (e) => {
            state.filters.eqCategory = e.target.value;
            renderEquipments();
        });
    }

    const eqStatus = document.getElementById('eqStatusFilter');
    if (eqStatus) {
        eqStatus.addEventListener('change', (e) => {
            state.filters.eqStatus = e.target.value;
            renderEquipments();
        });
    }

    // Close modal on click outside
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
        }
    });
}

function resetTicketFilters() {
    state.filters.ticketSearch = '';
    state.filters.ticketStatus = 'All';
    state.filters.ticketPriority = 'All';

    const s = document.getElementById('ticketSearchInput');
    const st = document.getElementById('ticketStatusFilter');
    const p = document.getElementById('ticketPriorityFilter');

    if (s) s.value = '';
    if (st) st.value = 'All';
    if (p) p.value = 'All';

    renderTickets();
}

function resetEqFilters() {
    state.filters.eqSearch = '';
    state.filters.eqCategory = 'All';
    state.filters.eqStatus = 'All';

    const s = document.getElementById('eqSearchInput');
    const c = document.getElementById('eqCategoryFilter');
    const st = document.getElementById('eqStatusFilter');

    if (s) s.value = '';
    if (c) c.value = 'All';
    if (st) st.value = 'All';

    renderEquipments();
}

// ==========================================================================
// 10. Toast Notification System & Utilities
// ==========================================================================
function showToast(message, type = 'success', duration = 3500) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let icon = 'fa-circle-check';
    if (type === 'error') icon = 'fa-circle-xmark';
    else if (type === 'info') icon = 'fa-circle-info';

    toast.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <div style="flex: 1;">${escapeHtml(message)}</div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        setTimeout(() => toast.remove(), 250);
    }, duration);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
