/**
 * QUICK TECH REPAIR - Client Application Logic
 * Supports: Authentication, Admin Passcode Lock, 5 Devices Restriction,
 * Live Tracking 5-Step Stepper, Before/After Photos, Review/Ratings, AI Consultant
 */

const API_URL = (window.location.protocol === 'file:' || !window.location.port) 
    ? 'http://127.0.0.1:8000/api' 
    : '/api';

// --- State Management ---
const state = {
    token: localStorage.getItem('tech_token') || null,
    currentUser: null,
    adminUnlocked: localStorage.getItem('tech_admin_unlocked') === 'true' || false,
    equipments: [],
    tickets: [],
    reviews: [],
    stats: null,
    currentTrackingTicket: null,
    activeAdminTab: 'tickets',
    users: [],
    selectedStarRating: 5
};

// Preset high quality hardware repair photos for testing
const PRESET_BEFORE_IMAGES = {
    "Notebook": "https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?w=600&auto=format&fit=crop&q=80",
    "Computer": "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?w=600&auto=format&fit=crop&q=80",
    "iPhone": "https://images.unsplash.com/photo-1592899677977-9c10ca588bbd?w=600&auto=format&fit=crop&q=80",
    "iPad": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&auto=format&fit=crop&q=80",
    "Mobile": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=600&auto=format&fit=crop&q=80"
};

const PRESET_AFTER_IMAGE = "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=600&auto=format&fit=crop&q=80";

// --- Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    await checkAuthState();
    await fetchInitialData();
});

// --- Theme Management ---
function initTheme() {
    const saved = localStorage.getItem('tech_theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    updateThemeIcon(saved);

    const toggleBtn = document.getElementById('themeToggleBtn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme') || 'light';
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('tech_theme', next);
            updateThemeIcon(next);
        });
    }
}

function updateThemeIcon(theme) {
    const btn = document.getElementById('themeToggleBtn');
    if (!btn) return;
    btn.innerHTML = theme === 'dark' ? '<i class="fa-solid fa-sun" style="color: #fbbf24;"></i>' : '<i class="fa-solid fa-moon"></i>';
}

// --- Auth Headers Helper ---
function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    return headers;
}

// --- Check Auth State ---
async function checkAuthState() {
    if (!state.token) {
        updateAuthUI(null);
        return;
    }

    try {
        const res = await fetch(`${API_URL}/auth/me`, { headers: getAuthHeaders() });
        if (res.ok) {
            state.currentUser = await res.json();
            if (state.currentUser.role === 'admin' || state.currentUser.role === 'technician') {
                state.adminUnlocked = true;
                localStorage.setItem('tech_admin_unlocked', 'true');
            }
            updateAuthUI(state.currentUser);
        } else {
            logout(false);
        }
    } catch {
        updateAuthUI(null);
    }
}

function updateAuthUI(user) {
    const guestGroup = document.getElementById('guestNavGroup');
    const userGroup = document.getElementById('userNavGroup');
    const headerName = document.getElementById('headerUserName');
    const headerRole = document.getElementById('headerUserRole');
    const headerAvatar = document.getElementById('headerUserAvatar');

    if (user) {
        if (guestGroup) guestGroup.style.display = 'none';
        if (userGroup) userGroup.style.display = 'flex';
        if (headerName) headerName.textContent = user.full_name;
        if (headerAvatar) headerAvatar.textContent = (user.full_name || 'U').charAt(0).toUpperCase();
        if (headerRole) {
            headerRole.textContent = user.role.toUpperCase();
            headerRole.className = `role-tag role-${user.role}`;
        }
    } else {
        if (guestGroup) guestGroup.style.display = 'flex';
        if (userGroup) userGroup.style.display = 'none';
    }

    updateAdminLockState();
}

function updateAdminLockState() {
    const lockedView = document.getElementById('adminLockedState');
    const unlockedContent = document.getElementById('adminUnlockedContent');
    const badge = document.getElementById('adminLockBadge');
    const actionBtns = document.getElementById('adminActionButtons');
    const resetBtn = document.getElementById('adminResetDemoBtn');
    const newEqBtn = document.getElementById('adminNewEqBtn');

    const isUnlocked = state.adminUnlocked || (state.currentUser && (state.currentUser.role === 'admin' || state.currentUser.role === 'technician'));

    if (isUnlocked) {
        if (lockedView) lockedView.style.display = 'none';
        if (unlockedContent) unlockedContent.style.display = 'block';
        if (badge) {
            badge.innerHTML = '<i class="fa-solid fa-lock-open"></i> ปลดล็อกแล้ว';
            badge.style.background = '#10b981';
        }
        if (state.currentUser && state.currentUser.role === 'admin') {
            if (resetBtn) resetBtn.style.display = 'inline-flex';
            if (newEqBtn) newEqBtn.style.display = 'inline-flex';
        }
    } else {
        if (lockedView) lockedView.style.display = 'block';
        if (unlockedContent) unlockedContent.style.display = 'none';
        if (badge) {
            badge.innerHTML = '<i class="fa-solid fa-lock"></i> ต้องมีสิทธิ์หรือรหัส';
            badge.style.background = '#ef4444';
        }
    }
}

// --- Data Fetching ---
async function fetchInitialData() {
    try {
        const [boardRes, reviewsRes] = await Promise.all([
            fetch(`${API_URL}/board`),
            fetch(`${API_URL}/reviews`)
        ]);

        if (boardRes.ok) {
            const data = await boardRes.json();
            state.equipments = data.equipments || [];
            state.tickets = data.tickets || [];
            state.stats = data.stats || null;
            renderStats();
            renderAdminTickets();
            renderAdminEquipments();
        }

        if (reviewsRes.ok) {
            state.reviews = await reviewsRes.json();
            renderReviews();
        }

        // Show first ticket in Live Tracking
        if (state.tickets.length > 0) {
            // Find resolved case or the first ticket
            const sample = state.tickets.find(t => t.id === 'TK-004') || state.tickets[0];
            renderLiveTracking(sample);
        }
    } catch (err) {
        console.error("Failed to load initial data", err);
        showToast('ไม่สามารถเชื่อมต่อ Backend ได้ กรุณาเปิดผ่านลิงก์ http://127.0.0.1:8000', 'error');
    }
}

// --- Render Stats ---
function renderStats() {
    if (!state.stats) return;
    const s = state.stats;
    const totalEq = document.getElementById('statTotalEquipments');
    const pendingTk = document.getElementById('statPendingTickets');
    const urgentTk = document.getElementById('statUrgentTickets');
    const resolvedTk = document.getElementById('statResolvedTickets');

    if (totalEq) totalEq.textContent = s.total_equipments || 0;
    if (pendingTk) pendingTk.textContent = (s.open_tickets_count || 0) + (s.in_progress_tickets_count || 0);
    if (urgentTk) urgentTk.textContent = s.urgent_tickets_count || 0;
    if (resolvedTk) resolvedTk.textContent = s.resolved_tickets_count || 0;
}

// --- Live Tracking Render [ข้อ 4] ---
function renderLiveTracking(ticket) {
    const container = document.getElementById('trackingDisplayCard');
    if (!container) return;

    if (!ticket) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                <i class="fa-solid fa-clipboard-question" style="font-size: 2.5rem; margin-bottom: 12px; display: block;"></i>
                <h3>ไม่พบข้อมูลใบแจ้งซ่อม</h3>
                <p>กรุณากรอกเลขที่ใบรับซ่อมให้ถูกต้อง เช่น TK-001 หรือเลือกหมวดหมู่อุปกรณ์</p>
            </div>
        `;
        return;
    }

    state.currentTrackingTicket = ticket;

    // Calculate Step Stages (1 to 5)
    let stepIndex = 1;
    if (ticket.status === 'Open') stepIndex = 2; // ได้รับเครื่องและกำลังตรวจเช็ค
    else if (ticket.status === 'In Progress') stepIndex = 3; // อยู่ระหว่างซ่อม
    else if (ticket.status === 'Resolved') stepIndex = 4; // ซ่อมเสร็จสมบูรณ์
    else if (ticket.status === 'Closed') stepIndex = 5; // ส่งมอบแล้ว

    const steps = [
        { num: 1, title: 'รับเครื่องเข้าระบบ', desc: 'ออกใบรับซ่อม', icon: 'fa-inbox' },
        { num: 2, title: 'ตรวจเช็คประเมินราคา', desc: 'วิเคราะห์อาการ', icon: 'fa-microchip' },
        { num: 3, title: 'อยู่ระหว่างซ่อม', desc: 'เปลี่ยนอะไหล่/ซ่อม', icon: 'fa-screwdriver-wrench' },
        { num: 4, title: 'ซ่อมเสร็จสมบูรณ์', desc: 'ทดสอบผ่าน QC', icon: 'fa-circle-check' },
        { num: 5, title: 'ส่งมอบลูกค้า', desc: 'รับประกัน 90 วัน', icon: 'fa-handshake' }
    ];

    const stepperHtml = steps.map(s => {
        let cls = '';
        if (s.num < stepIndex) cls = 'completed';
        else if (s.num === stepIndex) cls = 'active';

        return `
            <div class="stepper-step ${cls}">
                <div class="step-node"><i class="fa-solid ${s.num < stepIndex ? 'fa-check' : s.icon}"></i></div>
                <div class="step-title">${s.title}</div>
                <div class="step-time">${s.desc}</div>
            </div>
        `;
    }).join('');

    // Before & After Photos
    const beforePhotoHtml = ticket.image_before 
        ? `<img src="${ticket.image_before}" alt="สภาพก่อนซ่อม" class="photo-preview-img" onclick="window.open('${ticket.image_before}', '_blank')">`
        : `<div class="photo-placeholder"><i class="fa-regular fa-image"></i><span>ไม่มีรูปภาพก่อนซ่อม</span></div>`;

    const afterPhotoHtml = ticket.image_after
        ? `<img src="${ticket.image_after}" alt="สภาพหลังซ่อมเสร็จ" class="photo-preview-img" onclick="window.open('${ticket.image_after}', '_blank')">`
        : `<div class="photo-placeholder"><i class="fa-regular fa-image"></i><span>อยู่ระหว่างดำเนินการซ่อม</span></div>`;

    // Customer Review Card
    let reviewSectionHtml = '';
    if (ticket.status === 'Resolved' || ticket.status === 'Closed') {
        if (ticket.rating) {
            // Already reviewed
            const stars = Array.from({ length: 5 }, (_, i) => 
                `<i class="fa-${i < ticket.rating ? 'solid' : 'regular'} fa-star"></i>`
            ).join('');

            reviewSectionHtml = `
                <div class="tracking-review-card" style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); color: var(--text-primary);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <h4 style="color: var(--status-success);"><i class="fa-solid fa-circle-check"></i> รีวิวความพึงพอใจของท่าน</h4>
                        <div class="star-rating-display" style="font-size: 1.1rem;">${stars}</div>
                    </div>
                    <p style="font-style: italic; color: var(--text-secondary); margin-bottom: 0;">
                        "${escapeHtml(ticket.review_comment || 'พึงพอใจในบริการอย่างยิ่ง')}"
                    </p>
                </div>
            `;
        } else {
            // Can review now
            reviewSectionHtml = `
                <div class="tracking-review-card">
                    <h4><i class="fa-solid fa-star" style="color: #fbbf24;"></i> ให้คะแนนและรีวิวงานซ่อมเคสนี้</h4>
                    <p>เครื่องซ่อมเสร็จเรียบร้อยแล้ว โปรดให้คะแนนความพึงพอใจเพื่อพัฒนาคุณภาพการบริการ</p>
                    <div class="star-rating-select" id="starRatingBox">
                        <i class="fa-solid fa-star" onclick="setStarRating(1)"></i>
                        <i class="fa-solid fa-star" onclick="setStarRating(2)"></i>
                        <i class="fa-solid fa-star" onclick="setStarRating(3)"></i>
                        <i class="fa-solid fa-star" onclick="setStarRating(4)"></i>
                        <i class="fa-solid fa-star" onclick="setStarRating(5)"></i>
                    </div>
                    <textarea id="trackingReviewInput" class="review-textarea" rows="2" placeholder="เขียนข้อความรีวิวความประทับใจ หรือข้อเสนอแนะ..."></textarea>
                    <button class="btn btn-cyan btn-sm" onclick="submitTicketReview('${ticket.id}')">
                        <i class="fa-solid fa-paper-plane"></i> ส่งรีวิวความพึงพอใจ
                    </button>
                </div>
            `;
        }
    }

    container.innerHTML = `
        <div class="tracking-header">
            <div>
                <div class="tracking-ticket-id">
                    <i class="fa-solid fa-receipt" style="color: var(--brand-cyan);"></i>
                    <span>ใบรับซ่อมเลขที่: ${ticket.id}</span>
                    <span class="tracking-device-tag">${ticket.device_category || 'IT Equipment'}</span>
                </div>
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">
                    รุ่น: <b>${escapeHtml(ticket.device_model || ticket.equipment_name || '-')}</b> | ลูกค้า: <b>${escapeHtml(ticket.customer_name || ticket.created_by || 'ทั่วไป')}</b>
                </div>
            </div>
            <div>
                <span class="badge badge-${ticket.status.toLowerCase().replace(' ', '-')}">
                    <i class="fa-solid fa-circle-dot"></i> สถานะ: ${ticket.status}
                </span>
            </div>
        </div>

        <!-- 5 Steps Stepper -->
        <div class="progress-stepper">
            ${stepperHtml}
        </div>

        <!-- Details Grid -->
        <div class="tracking-details-grid">
            <!-- Left Column: Details -->
            <div class="detail-info-card">
                <h4 style="font-size: 1rem; font-weight: 700; margin-bottom: 14px; color: var(--text-primary);">
                    <i class="fa-solid fa-circle-info" style="color: var(--accent-blue);"></i> ข้อมูลและบันทึกการซ่อม
                </h4>
                <div class="detail-row">
                    <span class="detail-label">หัวข้อปัญหา:</span>
                    <span class="detail-value">${escapeHtml(ticket.title)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">อาการเสีย:</span>
                    <span class="detail-value" style="font-weight: 400; text-align: right; max-width: 340px;">${escapeHtml(ticket.description)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">ช่างผู้รับผิดชอบ:</span>
                    <span class="detail-value">${ticket.assigned_to ? `<i class="fa-solid fa-user-gear"></i> ${escapeHtml(ticket.assigned_to)}` : '<span style="color: var(--text-muted);">- กำลังจัดสรรคิวช่าง -</span>'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">ราคาประเมิน:</span>
                    <span class="detail-value" style="color: #0284c7; font-size: 1.05rem;">฿${(ticket.estimated_cost || 0).toLocaleString()} บาท</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">ระยะเวลาซ่อม:</span>
                    <span class="detail-value">ประมาณ ${ticket.estimated_days || 1} วัน</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">บันทึกผลการซ่อม:</span>
                    <span class="detail-value" style="color: #10b981;">${ticket.notes ? escapeHtml(ticket.notes) : '<span style="color: var(--text-muted);">- ยังไม่มีบันทึก -</span>'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">วันที่ส่งซ่อม:</span>
                    <span class="detail-value">${ticket.created_at || '-'}</span>
                </div>
            </div>

            <!-- Right Column: Before & After Photos -->
            <div>
                <h4 style="font-size: 1rem; font-weight: 700; margin-bottom: 10px; color: var(--text-primary);">
                    <i class="fa-solid fa-camera" style="color: var(--brand-cyan);"></i> ภาพถ่ายเปรียบเทียบก่อน-หลังซ่อม
                </h4>
                <div class="photos-comparison-container">
                    <div class="photo-box">
                        <span class="photo-tag before">ก่อนซ่อม (Before)</span>
                        ${beforePhotoHtml}
                    </div>
                    <div class="photo-box">
                        <span class="photo-tag after">หลังซ่อม (After)</span>
                        ${afterPhotoHtml}
                    </div>
                </div>

                <!-- Review Section Inside Tracking Card -->
                ${reviewSectionHtml}
            </div>
        </div>
    `;
}

// Star rating selection helper
function setStarRating(rating) {
    state.selectedStarRating = rating;
    const box = document.getElementById('starRatingBox');
    if (!box) return;
    const stars = box.querySelectorAll('i');
    stars.forEach((star, index) => {
        if (index < rating) {
            star.className = 'fa-solid fa-star';
        } else {
            star.className = 'fa-regular fa-star';
        }
    });
}

async function submitTicketReview(ticketId) {
    const commentInput = document.getElementById('trackingReviewInput');
    const comment = commentInput ? commentInput.value.trim() : '';

    if (!comment) {
        showToast('กรุณากรอกข้อความรีวิวหรือความประทับใจ', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_URL}/tickets/${ticketId}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                rating: state.selectedStarRating || 5,
                review_comment: comment
            })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'ไม่สามารถบันทึกรีวิวได้');
        }

        const data = await res.json();
        showToast('ขอบพระคุณสำหรับรีวิวและความไว้วางใจ!', 'success');
        
        // Refresh local data
        await fetchInitialData();
        const updated = state.tickets.find(t => t.id === ticketId);
        if (updated) renderLiveTracking(updated);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// --- Header & Hero Tracking Search ---
function searchTicketFromHeader() {
    const query = document.getElementById('headerSearchInput').value.trim();
    if (!query) return;
    trackByQuery(query);
}

function trackTicketFromHero() {
    const query = document.getElementById('heroTrackInput').value.trim();
    if (!query) return;
    trackByQuery(query);
}

function trackByQuery(query) {
    const q = query.toLowerCase();
    const found = state.tickets.find(t => 
        t.id.toLowerCase() === q || 
        (t.customer_phone && t.customer_phone.replace(/\D/g, '').includes(q.replace(/\D/g, '')))
    );

    if (found) {
        renderLiveTracking(found);
        document.getElementById('trackingSection').scrollIntoView({ behavior: 'smooth' });
        showToast(`พบข้อมูลงานซ่อม "${found.id}"`, 'success');
    } else {
        // Try fetching single
        fetch(`${API_URL}/tickets/${query.toUpperCase()}`)
            .then(res => {
                if (res.ok) return res.json();
                throw new Error('ไม่พบข้อมูล');
            })
            .then(tk => {
                renderLiveTracking(tk);
                document.getElementById('trackingSection').scrollIntoView({ behavior: 'smooth' });
                showToast(`พบข้อมูลงานซ่อม "${tk.id}"`, 'success');
            })
            .catch(() => {
                showToast(`ไม่พบใบแจ้งซ่อมรหัสหรือเบอร์โทร "${query}"`, 'error');
            });
    }
}

function showSampleTicket(ticketId) {
    const found = state.tickets.find(t => t.id === ticketId);
    if (found) {
        renderLiveTracking(found);
        document.getElementById('trackingSection').scrollIntoView({ behavior: 'smooth' });
    }
}

// --- 5 Device Categories Interaction [ข้อ 4] ---
function selectDeviceCategory(category) {
    openNewTicketModal(category);
}

function handleCategoryChange(cat) {
    const modelInput = document.getElementById('ticketDeviceModel');
    if (!modelInput) return;

    if (cat === 'iPhone') modelInput.placeholder = 'เช่น iPhone 14 Pro Max 256GB';
    else if (cat === 'iPad') modelInput.placeholder = 'เช่น iPad Air 5 (M1) Wi-Fi';
    else if (cat === 'Notebook') modelInput.placeholder = 'เช่น Asus ROG Strix G15, MacBook Pro M2';
    else if (cat === 'Computer') modelInput.placeholder = 'เช่น PC Core i7-13700KF RTX 4070';
    else if (cat === 'Mobile') modelInput.placeholder = 'เช่น Samsung Galaxy S23 Ultra';
}

function setPresetBeforeImage() {
    const catSelect = document.getElementById('ticketDeviceCategory');
    const cat = catSelect ? catSelect.value : 'Notebook';
    const imgInput = document.getElementById('ticketImageBefore');
    if (imgInput && PRESET_BEFORE_IMAGES[cat]) {
        imgInput.value = PRESET_BEFORE_IMAGES[cat];
        showToast('ใส่รูปภาพตัวอย่างก่อนซ่อมเรียบร้อย', 'info');
    }
}

function setPresetAfterImage() {
    const imgInput = document.getElementById('updateImageAfter');
    if (imgInput) {
        imgInput.value = PRESET_AFTER_IMAGE;
        showToast('ใส่รูปภาพตัวอย่างหลังซ่อมเสร็จเรียบร้อย', 'info');
    }
}

// --- Customer Reviews Showcase ---
function renderReviews() {
    const container = document.getElementById('reviewsContainer');
    if (!container) return;

    if (!state.reviews || state.reviews.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 30px; color: var(--text-muted);">
                <i class="fa-solid fa-comments" style="font-size: 2rem; margin-bottom: 8px;"></i>
                <p>ยังไม่มีรีวิวจากลูกค้า</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.reviews.map(r => {
        const stars = Array.from({ length: 5 }, (_, i) => 
            `<i class="fa-${i < (r.rating || 5) ? 'solid' : 'regular'} fa-star"></i>`
        ).join('');

        const beforeThumb = r.image_before ? `<img src="${r.image_before}" alt="Before" title="ก่อนซ่อม">` : '';
        const afterThumb = r.image_after ? `<img src="${r.image_after}" alt="After" title="หลังซ่อมเสร็จ">` : '';

        return `
            <div class="review-card">
                <div>
                    <div class="review-header">
                        <div>
                            <div class="reviewer-name">${escapeHtml(r.customer_name || 'ลูกค้าผู้ใช้บริการ')}</div>
                            <div class="reviewer-device"><i class="fa-solid fa-microchip"></i> ${escapeHtml(r.device_model || r.device_category || 'IT Equipment')}</div>
                        </div>
                        <div class="star-rating-display">${stars}</div>
                    </div>
                    <p class="review-text">"${escapeHtml(r.review_comment || 'บริการดีเยี่ยม รวดเร็ว ประทับใจมากครับ')}"</p>
                </div>
                ${(beforeThumb || afterThumb) ? `<div class="review-photos-thumb">${beforeThumb}${afterThumb}</div>` : ''}
            </div>
        `;
    }).join('');
}

// --- AI Consultant Interaction [ข้อ 5] ---
function askAIPrompt(text) {
    const input = document.getElementById('aiChatInput');
    if (input) {
        input.value = text;
        submitAIChat();
    }
}

function askAIFill(category) {
    const input = document.getElementById('aiChatInput');
    if (input) {
        input.value = `สอบถามราคาซ่อมและระยะเวลาสำหรับ ${category}`;
        document.getElementById('aiSection').scrollIntoView({ behavior: 'smooth' });
        input.focus();
    }
}

async function submitAIChat(e) {
    if (e) e.preventDefault();

    const input = document.getElementById('aiChatInput');
    const msgContainer = document.getElementById('aiChatMessages');
    if (!input || !msgContainer) return;

    const query = input.value.trim();
    if (!query) return;

    // Append user message
    const userMsg = document.createElement('div');
    userMsg.className = 'chat-bubble user';
    userMsg.textContent = query;
    msgContainer.appendChild(userMsg);
    input.value = '';
    msgContainer.scrollTop = msgContainer.scrollHeight;

    // Append loading bubble
    const loadingBubble = document.createElement('div');
    loadingBubble.className = 'chat-bubble ai';
    loadingBubble.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AI กำลังวิเคราะห์อาการและคำนวณราคา...';
    msgContainer.appendChild(loadingBubble);
    msgContainer.scrollTop = msgContainer.scrollHeight;

    try {
        const res = await fetch(`${API_URL}/ai/consult`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ issue_description: query })
        });

        if (!res.ok) throw new Error('AI ขัดข้องชั่วคราว');

        const data = await res.json();

        loadingBubble.innerHTML = `
            <div style="font-weight: 700; color: #0284c7; margin-bottom: 4px;">
                <i class="fa-solid fa-robot"></i> วิเคราะห์สำหรับ ${data.device_category}:
            </div>
            <div>${escapeHtml(data.diagnosis)}</div>

            <div class="ai-kpi-row">
                <div class="ai-kpi-badge"><i class="fa-solid fa-tags" style="color: #0284c7;"></i> ราคาประเมิน: <b>${data.estimated_cost_range}</b></div>
                <div class="ai-kpi-badge"><i class="fa-solid fa-clock" style="color: #f59e0b;"></i> ระยะเวลา: <b>${data.estimated_days_range}</b></div>
            </div>

            <div class="ai-diag-card">
                <div class="ai-diag-title"><i class="fa-solid fa-screwdriver-wrench"></i> แนวทางแก้ไขโดยช่างชำนาญการ:</div>
                <ul style="padding-left: 18px; font-size: 0.82rem; margin: 0;">
                    ${data.solutions.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                </ul>
            </div>

            <div style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 8px;">
                💡 <b>คำแนะนำ:</b> ${escapeHtml(data.recommendations)}
            </div>
            <div style="font-size: 0.74rem; color: #10b981; margin-top: 6px;">
                🛡️ ${escapeHtml(data.store_info)}
            </div>
        `;
    } catch (err) {
        loadingBubble.innerHTML = '<span style="color: #ef4444;"><i class="fa-solid fa-triangle-exclamation"></i> ไม่สามารถติดต่อ AI ได้ กรุณาลองใหม่อีกครั้ง</span>';
    }

    msgContainer.scrollTop = msgContainer.scrollHeight;
}

// --- Protected Management Actions [ข้อ 1, 2, 3] ---

function requireAuthCheck(actionName) {
    if (!state.currentUser) {
        showToast(`กรุณาเข้าสู่ระบบก่อนดำเนินการ "${actionName}"`, 'error');
        openLoginModal();
        return false;
    }
    return true;
}

function openAdminConsoleModal() {
    if (state.adminUnlocked || (state.currentUser && (state.currentUser.role === 'admin' || state.currentUser.role === 'technician'))) {
        document.getElementById('adminSection').scrollIntoView({ behavior: 'smooth' });
    } else {
        openAdminPasscodeModal();
    }
}

function openAdminPasscodeModal() {
    openModal('adminPasscodeModal');
}

async function submitAdminPasscode(e) {
    e.preventDefault();
    const input = document.getElementById('adminPasscodeInput');
    const passcode = input ? input.value.trim() : '';

    try {
        const res = await fetch(`${API_URL}/admin/verify-passcode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ passcode })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'รหัสความปลอดภัยไม่ถูกต้อง');
        }

        state.adminUnlocked = true;
        localStorage.setItem('tech_admin_unlocked', 'true');
        closeModal('adminPasscodeModal');
        updateAdminLockState();
        showToast('ยืนยันสิทธิ์สำเร็จ ปลดล็อกหน้าควบคุมแล้ว', 'success');
        document.getElementById('adminSection').scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// [ข้อ 3] Management click: requires login and tech/admin role
function openUpdateTicketModal(ticketId) {
    // ต้องเข้าสู่ระบบก่อน
    if (!state.currentUser) {
        showToast('กรุณาเข้าสู่ระบบก่อนจึงจะสามารถแก้ไขการจัดการได้', 'error');
        openLoginModal();
        return;
    }

    // ต้องเป็นช่างหรือแอดมินเท่านั้น
    if (state.currentUser.role !== 'admin' && state.currentUser.role !== 'technician') {
        showToast('เฉพาะช่างเทคนิค (Technician) หรือแอดมิน (Admin) เท่านั้นที่แก้ไขงานซ่อมได้', 'error');
        return;
    }

    const tk = state.tickets.find(t => t.id === ticketId);
    if (!tk) return;

    document.getElementById('updateTicketIdHidden').value = tk.id;
    document.getElementById('updateTicketIdDisplay').textContent = tk.id;
    document.getElementById('updateTicketStatusSelect').value = tk.status;
    document.getElementById('updateTechnicianInput').value = tk.assigned_to || state.currentUser.full_name;
    document.getElementById('updateImageAfter').value = tk.image_after || '';
    document.getElementById('updateCostInput').value = tk.estimated_cost || '';
    document.getElementById('updateDaysInput').value = tk.estimated_days || 1;
    document.getElementById('updateNotesInput').value = tk.notes || '';

    openModal('updateTicketModal');
}

async function submitUpdateTicket(e) {
    e.preventDefault();

    if (!requireAuthCheck('บันทึกการจัดการ')) return;

    const ticketId = document.getElementById('updateTicketIdHidden').value;
    const status = document.getElementById('updateTicketStatusSelect').value;
    const technician = document.getElementById('updateTechnicianInput').value.trim() || null;
    const image_after = document.getElementById('updateImageAfter').value.trim() || null;
    const estimated_cost = parseFloat(document.getElementById('updateCostInput').value) || null;
    const estimated_days = parseInt(document.getElementById('updateDaysInput').value) || null;
    const notes = document.getElementById('updateNotesInput').value.trim() || null;

    try {
        const res = await fetch(`${API_URL}/tickets/${ticketId}`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                status,
                technician,
                notes,
                image_after,
                estimated_cost,
                estimated_days
            })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'ไม่สามารถอัปเดตได้');
        }

        closeModal('updateTicketModal');
        showToast(`อัปเดตงานซ่อม "${ticketId}" สำเร็จ`, 'success');
        await fetchInitialData();

        // Update tracking card if viewing this ticket
        const updated = state.tickets.find(t => t.id === ticketId);
        if (updated) renderLiveTracking(updated);
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteTicketConfirm(ticketId) {
    if (!requireAuthCheck('ลบใบแจ้งซ่อม')) return;

    if (!confirm(`ยืนยันการลบใบแจ้งซ่อม "${ticketId}" หรือไม่?`)) return;

    try {
        const res = await fetch(`${API_URL}/tickets/${ticketId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'ไม่สามารถลบใบแจ้งซ่อมได้');
        }

        showToast(`ลบใบแจ้งซ่อม "${ticketId}" เรียบร้อยแล้ว`, 'success');
        await fetchInitialData();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// --- Admin Tables Rendering ---
function renderAdminTickets() {
    const tbody = document.getElementById('adminTicketTableBody');
    if (!tbody) return;

    tbody.innerHTML = state.tickets.map(tk => {
        let statusBadgeCls = 'badge-open';
        if (tk.status === 'In Progress') statusBadgeCls = 'badge-in-progress';
        else if (tk.status === 'Resolved') statusBadgeCls = 'badge-resolved';
        else if (tk.status === 'Closed') statusBadgeCls = 'badge-closed';

        const beforeThumb = tk.image_before ? `<a href="${tk.image_before}" target="_blank" style="color: var(--accent-blue);">ก่อน</a>` : '-';
        const afterThumb = tk.image_after ? `<a href="${tk.image_after}" target="_blank" style="color: var(--status-success);">หลัง</a>` : '-';

        return `
            <tr>
                <td><span class="code-badge">${tk.id}</span></td>
                <td>
                    <div style="font-weight: 700;">${escapeHtml(tk.device_category || '-')}</div>
                    <div style="font-size: 0.75rem; color: var(--text-secondary);">${escapeHtml(tk.device_model || tk.equipment_name || '-')}</div>
                </td>
                <td>
                    <div style="font-weight: 600;">${escapeHtml(tk.title)}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); max-width: 250px; overflow: hidden; text-overflow: ellipsis;">
                        ${escapeHtml(tk.description)}
                    </div>
                </td>
                <td><span class="badge priority-${(tk.priority || 'medium').toLowerCase()}">${tk.priority}</span></td>
                <td>${tk.assigned_to ? escapeHtml(tk.assigned_to) : '<span style="color: var(--text-muted);">-</span>'}</td>
                <td><span class="badge ${statusBadgeCls}">${tk.status}</span></td>
                <td>${beforeThumb} / ${afterThumb}</td>
                <td style="color: #0284c7; font-weight: 700;">฿${(tk.estimated_cost || 0).toLocaleString()}</td>
                <td style="text-align: right;">
                    <button class="btn btn-secondary btn-sm" onclick="openUpdateTicketModal('${tk.id}')" title="จัดการ/อัปเดต">
                        <i class="fa-solid fa-pen-to-square"></i> จัดการ
                    </button>
                    <button class="btn-icon btn-icon-danger" onclick="deleteTicketConfirm('${tk.id}')" title="ลบ">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function filterAdminTickets() {
    const search = (document.getElementById('adminTicketSearch')?.value || '').toLowerCase().trim();
    const status = document.getElementById('adminStatusFilter')?.value || 'All';
    const cat = document.getElementById('adminCategoryFilter')?.value || 'All';

    const rows = document.querySelectorAll('#adminTicketTableBody tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const matchesSearch = !search || text.includes(search);
        const matchesStatus = status === 'All' || text.includes(status.toLowerCase());
        const matchesCat = cat === 'All' || text.includes(cat.toLowerCase());

        row.style.display = (matchesSearch && matchesStatus && matchesCat) ? '' : 'none';
    });
}

function renderAdminEquipments() {
    const tbody = document.getElementById('adminEqTableBody');
    if (!tbody) return;

    tbody.innerHTML = state.equipments.map(eq => `
        <tr>
            <td><span class="code-badge">${eq.id}</span></td>
            <td><b>${escapeHtml(eq.name)}</b></td>
            <td><span class="badge" style="background: var(--bg-surface-secondary);">${escapeHtml(eq.category)}</span></td>
            <td>${escapeHtml(eq.location)}</td>
            <td><span class="badge ${eq.status === 'Operational' ? 'badge-resolved' : 'badge-open'}">${eq.status}</span></td>
            <td>${eq.created_at || '-'}</td>
        </tr>
    `).join('');
}

function switchAdminTab(tab) {
    state.activeAdminTab = tab;
    ['tickets', 'equipments', 'users'].forEach(t => {
        const btn = document.getElementById(`adminTab${t.charAt(0).toUpperCase() + t.slice(1)}Btn`);
        const view = document.getElementById(`admin${t.charAt(0).toUpperCase() + t.slice(1)}View`);
        if (btn) btn.classList.toggle('active', t === tab);
        if (view) view.style.display = t === tab ? 'block' : 'none';
    });

    if (tab === 'users') {
        fetchAdminUsers();
    }
}

async function fetchAdminUsers() {
    if (!state.currentUser || state.currentUser.role !== 'admin') {
        const tbody = document.getElementById('adminUserTableBody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #ef4444; padding: 20px;">เฉพาะผู้ดูแลระบบ (Admin) เท่านั้นที่สามารถดูรายชื่อผู้ใช้ได้</td></tr>`;
        }
        return;
    }

    try {
        const res = await fetch(`${API_URL}/admin/users`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error('ไม่สามารถดึงรายชื่อผู้ใช้ได้');
        state.users = await res.json();
        renderAdminUsers();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function renderAdminUsers() {
    const tbody = document.getElementById('adminUserTableBody');
    if (!tbody) return;

    tbody.innerHTML = state.users.map(u => `
        <tr>
            <td><span class="code-badge">${u.id}</span></td>
            <td><b>${escapeHtml(u.username)}</b></td>
            <td>${escapeHtml(u.full_name)}</td>
            <td><span class="role-tag role-${u.role}">${u.role.toUpperCase()}</span></td>
            <td>${u.created_at}</td>
            <td style="text-align: right;">
                <select class="form-control" style="width: auto; display: inline-block; padding: 4px 8px; font-size: 0.78rem;" onchange="updateUserRole('${u.id}', this.value)">
                    <option value="user" ${u.role === 'user' ? 'selected' : ''}>User</option>
                    <option value="technician" ${u.role === 'technician' ? 'selected' : ''}>Technician</option>
                    <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
                </select>
                <button class="btn-icon btn-icon-danger" onclick="deleteUser('${u.id}')" title="ลบผู้ใช้"><i class="fa-solid fa-trash"></i></button>
            </td>
        </tr>
    `).join('');
}

async function updateUserRole(userId, newRole) {
    try {
        const res = await fetch(`${API_URL}/admin/users/${userId}/role`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify({ role: newRole })
        });
        if (!res.ok) throw new Error('ไม่สามารถเปลี่ยนสิทธิ์ได้');
        showToast(`เปลี่ยนสิทธิ์ผู้ใช้เป็น ${newRole} สำเร็จ`, 'success');
        fetchAdminUsers();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteUser(userId) {
    if (!confirm('ยืนยันการลบผู้ใช้งานนี้หรือไม่?')) return;
    try {
        const res = await fetch(`${API_URL}/admin/users/${userId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('ไม่สามารถลบผู้ใช้ได้');
        showToast('ลบผู้ใช้เรียบร้อยแล้ว', 'success');
        fetchAdminUsers();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function resetDemoPrompt() {
    if (!confirm('ยืนยันการรีเซ็ตข้อมูลตัวอย่างสำหรับอุปกรณ์ 5 ชนิดหรือไม่? ข้อมูลงานซ่อมปัจจุบันจะถูกรีเซ็ต')) return;
    try {
        const res = await fetch(`${API_URL}/reset-demo`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('เฉพาะ Admin เท่านั้นที่รีเซ็ต Demo ได้');
        showToast('รีเซ็ตข้อมูลตัวอย่างสำเร็จเรียบร้อย', 'success');
        await fetchInitialData();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// --- Modals Management ---
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('active');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('active');
}

function openNewTicketModal(deviceCategory) {
    const catSelect = document.getElementById('ticketDeviceCategory');
    if (catSelect && deviceCategory) {
        catSelect.value = deviceCategory;
        handleCategoryChange(deviceCategory);
    }
    openModal('ticketModal');
}

function openEquipmentModal() {
    openModal('equipmentModal');
}

function openLoginModal() {
    closeModal('registerModal');
    openModal('loginModal');
}

function openRegisterModal() {
    closeModal('loginModal');
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

function handleRegRoleChange(role) {
    const adminGroup = document.getElementById('regAdminCodeGroup');
    if (adminGroup) {
        adminGroup.style.display = (role === 'admin' || role === 'technician') ? 'block' : 'none';
    }
}

// --- Submit Forms ---

async function submitNewTicket(e) {
    e.preventDefault();

    const device_category = document.getElementById('ticketDeviceCategory').value;
    const device_model = document.getElementById('ticketDeviceModel').value.trim();
    const title = document.getElementById('ticketTitleInput').value.trim();
    const description = document.getElementById('ticketDescInput').value.trim();
    const priority = document.getElementById('ticketPrioritySelect').value;
    const image_before = document.getElementById('ticketImageBefore').value.trim() || null;
    const customer_name = document.getElementById('ticketCustomerName').value.trim() || null;
    const customer_phone = document.getElementById('ticketCustomerPhone').value.trim() || null;

    try {
        const res = await fetch(`${API_URL}/tickets`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                device_category,
                device_model,
                title,
                description,
                priority,
                image_before,
                customer_name,
                customer_phone
            })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'ไม่สามารถเปิดใบแจ้งซ่อมได้');
        }

        const newTk = await res.json();
        closeModal('ticketModal');
        showToast(`เปิดใบแจ้งซ่อม "${newTk.id}" สำเร็จเรียบร้อย`, 'success');
        
        await fetchInitialData();
        renderLiveTracking(newTk);
        document.getElementById('trackingSection').scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function submitNewEquipment(e) {
    e.preventDefault();
    const category = document.getElementById('eqCategoryInput').value;
    const name = document.getElementById('eqNameInput').value.trim();
    const location = document.getElementById('eqLocationInput').value.trim();
    const image_url = document.getElementById('eqImageUrl').value.trim() || null;

    try {
        const res = await fetch(`${API_URL}/equipments`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ category, name, location, image_url })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'ไม่สามารถเพิ่มอุปกรณ์ได้');
        }
        closeModal('equipmentModal');
        showToast('เพิ่มอุปกรณ์ใหม่เข้าระบบสำเร็จ', 'success');
        await fetchInitialData();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// --- Auth Submit ---
async function submitLogin(e) {
    e.preventDefault();
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;

    try {
        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง');
        }

        const data = await res.json();
        state.token = data.token;
        state.currentUser = data.user;
        localStorage.setItem('tech_token', data.token);

        if (data.user.role === 'admin' || data.user.role === 'technician') {
            state.adminUnlocked = true;
            localStorage.setItem('tech_admin_unlocked', 'true');
        }

        updateAuthUI(data.user);
        closeModal('loginModal');
        showToast(`ยินดีต้อนรับคุณ ${data.user.full_name} (${data.user.role.toUpperCase()})`, 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function quickLogin(role) {
    const creds = {
        admin: { u: 'admin', p: 'admin123' },
        technician: { u: 'technician', p: 'tech123' },
        user: { u: 'user', p: 'user123' }
    };
    const c = creds[role];
    if (!c) return;
    document.getElementById('loginUsername').value = c.u;
    document.getElementById('loginPassword').value = c.p;
    submitLogin(new Event('submit'));
}

async function submitRegister(e) {
    e.preventDefault();
    const username = document.getElementById('regUsername').value.trim();
    const full_name = document.getElementById('regFullName').value.trim();
    const password = document.getElementById('regPassword').value;
    const role = document.getElementById('regRole').value;
    const admin_code = document.getElementById('regAdminCode')?.value.trim() || null;

    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, full_name, password, role, admin_code })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'การสมัครสมาชิกไม่สำเร็จ');
        }

        const data = await res.json();
        state.token = data.token;
        state.currentUser = data.user;
        localStorage.setItem('tech_token', data.token);

        if (data.user.role === 'admin' || data.user.role === 'technician') {
            state.adminUnlocked = true;
            localStorage.setItem('tech_admin_unlocked', 'true');
        }

        updateAuthUI(data.user);
        closeModal('registerModal');
        showToast(`สมัครสมาชิกสำเร็จ ยินดีต้อนรับคุณ ${data.user.full_name}`, 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

function logout(notify = true) {
    state.token = null;
    state.currentUser = null;
    state.adminUnlocked = false;
    localStorage.removeItem('tech_token');
    localStorage.removeItem('tech_admin_unlocked');
    updateAuthUI(null);
    if (notify) showToast('ออกจากระบบเรียบร้อยแล้ว', 'info');
}

// --- Utilities ---
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let icon = 'fa-circle-info';
    if (type === 'success') icon = 'fa-circle-check';
    else if (type === 'error') icon = 'fa-triangle-exclamation';

    toast.innerHTML = `<i class="fa-solid ${icon}"></i><span>${escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
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
