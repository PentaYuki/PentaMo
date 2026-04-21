# PentaMo UI & Frontend Architecture

## Tổng Quan Giao Diện

PentaMo có 3 giao diện chính:
1. **Chat Interface** (Web) - Tương tác chính với Agent
2. **Admin Dashboard** - Quản lý hệ thống
3. **Login/Auth Interface** - Xác thực người dùng

```
┌──────────────────────────────────────────┐
│         BROWSER (Client Side)            │
├──────────────────────────────────────────┤
│                                          │
│  ┌─────────────────────────────────┐   │
│  │   Login / Authentication Page    │   │
│  │   (login.html)                   │   │
│  └─────────────────────────────────┘   │
│                  │                       │
│                  ▼ (Authenticated)      │
│  ┌─────────────────────────────────┐   │
│  │   Home / Dashboard Page          │   │
│  │   (index.html)                   │   │
│  │   ┌─────────────────────────┐   │   │
│  │   │ Chat Interface           │   │   │
│  │   │ - Message History        │   │   │
│  │   │ - Input Area             │   │   │
│  │   │ - Quick Actions          │   │   │
│  │   └─────────────────────────┘   │   │
│  │   ┌─────────────────────────┐   │   │
│  │   │ Admin Dashboard          │   │   │
│  │   │ (for admins)             │   │   │
│  │   └─────────────────────────┘   │   │
│  └─────────────────────────────────┘   │
│                                          │
└──────────────────────────────────────────┘
         │ HTTP/REST API
         ▼
┌──────────────────────────────────────────┐
│      BACKEND (FastAPI Server)            │
├──────────────────────────────────────────┤
│   - Authentication & JWT                 │
│   - Message Processing                   │
│   - Data Retrieval                       │
│   - Admin Operations                     │
└──────────────────────────────────────────┘
```

---

## 1. STATIC FILES STRUCTURE

**Thư mục:** `static/` và `assets/`

```
static/
├── css/
│   └── main.css          # Main stylesheet
├── js/
│   ├── api.js            # API client functions
│   └── chat.js           # Chat UI logic
│
assets/
├── css/
│   ├── home.css          # Home page styles
│   ├── pages.css         # Pages styles
│   └── style.css         # Global styles
├── js/
│   ├── home.js           # Home page logic
│   └── main.js           # Main app logic
└── icons/                # SVG & PNG icons
```

---

## 2. PAGE STRUCTURE

### 2.1 Login Page (`login.html`)

**Mục đích:** Xác thực người dùng

```html
<div class="login-container">
  <div class="login-card">
    <h1>PentaMo Chat Agent</h1>
    <form id="loginForm">
      <input type="email" id="email" placeholder="Email" required>
      <input type="password" id="password" placeholder="Mật khẩu" required>
      <button type="submit">Đăng Nhập</button>
    </form>
    <p>Chưa có tài khoản? <a href="/register">Đăng ký</a></p>
  </div>
</div>
```

**Chức Năng:**
- Email/Password validation
- Gửi request tới `/api/auth/login`
- Lưu JWT token vào localStorage
- Redirect tới trang home sau đăng nhập thành công

**Styling:**
- Responsive design
- Dark theme
- Smooth animations

### 2.2 Home Page (`index.html`)

**Mục đích:** Giao diện chat chính

```html
<div class="app-container">
  
  <!-- Header -->
  <header class="app-header">
    <div class="logo">
      <svg class="pentagon-icon">...</svg>
      <span class="title">PentaMo</span>
    </div>
    <div class="header-actions">
      <button id="newChat" class="btn-primary">+ New Chat</button>
      <button id="settings" class="btn-icon">⚙️</button>
      <button id="logout" class="btn-icon">Logout</button>
    </div>
  </header>

  <!-- Main Content -->
  <main class="main-content">
    
    <!-- Sidebar: Conversation List -->
    <aside class="sidebar">
      <div class="conversation-list">
        <div class="conversation-item active">
          <span class="conv-title">Chat 1</span>
          <span class="conv-time">5 minutes ago</span>
        </div>
        <!-- More conversations -->
      </div>
    </aside>

    <!-- Chat Area -->
    <div class="chat-area">
      
      <!-- Messages Container -->
      <div class="messages-container">
        <div class="message user-message">
          <p>Tôi muốn mua Honda Winner</p>
          <span class="timestamp">10:05 AM</span>
        </div>
        <div class="message agent-message">
          <p>Tôi tìm thấy 5 chiếc Honda Winner phù hợp...</p>
          <span class="timestamp">10:05 AM</span>
        </div>
        <!-- More messages -->
      </div>

      <!-- Quick Suggestions -->
      <div class="suggestions-area">
        <div class="suggestion-chip">View Details</div>
        <div class="suggestion-chip">Book Viewing</div>
        <div class="suggestion-chip">Compare Listings</div>
      </div>

      <!-- Input Area -->
      <div class="input-area">
        <textarea id="messageInput" placeholder="Nhập tin nhắn..."></textarea>
        <button id="sendBtn" class="btn-send">Send</button>
      </div>

    </div>

    <!-- Right Panel: Details (collapsible) -->
    <aside class="details-panel">
      <div class="listings-preview">
        <div class="listing-card">
          <img src="..." alt="Honda Winner">
          <h4>Honda Winner X</h4>
          <p class="price">29,999,000 ₫</p>
          <button class="btn-action">Book Viewing</button>
        </div>
        <!-- More listings -->
      </div>
    </aside>

  </main>

  <!-- Loading/Status Indicator -->
  <div id="statusIndicator" class="status inactive">
    Ready
  </div>

</div>
```

**Chức Năng:**
- Hiển thị lịch sử hội thoại
- Gửi tin nhắn tới Agent
- Hiển thị phản hồi Agent
- Hiển thị danh sách xe phù hợp
- Quick actions (Book Viewing, View Details, etc.)

### 2.3 Admin Page (`admin/routes.py`)

**Mục đích:** Quản lý hệ thống và dữ liệu

```python
@app.get("/admin/dashboard")
async def admin_dashboard():
    """Admin dashboard page"""
    return HTMLResponse("""
    <div class="admin-container">
      <h1>Admin Dashboard</h1>
      
      <!-- Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <h3>Active Users</h3>
          <p id="activeUsers">0</p>
        </div>
        <div class="stat-card">
          <h3>Total Conversations</h3>
          <p id="totalConversations">0</p>
        </div>
        <div class="stat-card">
          <h3>Listings</h3>
          <p id="totalListings">0</p>
        </div>
      </div>

      <!-- Listing Management -->
      <section class="listing-management">
        <h2>Manage Listings</h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Brand</th>
              <th>Model</th>
              <th>Price</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="listingTable"></tbody>
        </table>
      </section>

      <!-- User Management -->
      <section class="user-management">
        <h2>Manage Users</h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="userTable"></tbody>
        </table>
      </section>

      <!-- System Logs -->
      <section class="system-logs">
        <h2>System Logs</h2>
        <div id="logViewer" class="log-container"></div>
      </section>
    </div>
    """)
```

---

## 3. STYLING ARCHITECTURE

### 3.1 CSS Hierarchy

```
assets/css/
├── style.css         # Global styles, variables
│   ├── :root { --primary, --secondary, etc. }
│   ├── body, html
│   └── Common classes
├── pages.css         # Page-specific styles
│   ├── .login-container
│   ├── .app-container
│   └── .admin-container
└── home.css          # Home page details
    ├── .header
    ├── .sidebar
    ├── .chat-area
    └── .input-area
```

### 3.2 Color & Theme

```css
:root {
  /* Primary Colors */
  --primary: #667eea;        /* Purple */
  --primary-dark: #5a67d8;
  --primary-light: #7c8ff5;
  
  /* Secondary Colors */
  --secondary: #764ba2;      /* Deep Purple */
  --accent: #f093fb;         /* Pink */
  
  /* Neutral Colors */
  --bg-dark: #1a202c;        /* Dark background */
  --bg-light: #2d3748;       /* Light background */
  --text-primary: #e2e8f0;   /* Light text */
  --text-secondary: #a0aec0; /* Dim text */
  
  /* Status Colors */
  --success: #48bb78;
  --warning: #ed8936;
  --error: #f56565;
  --info: #4299e1;
}
```

### 3.3 Responsive Design

```css
/* Desktop */
@media (min-width: 1024px) {
  .app-container {
    display: grid;
    grid-template-columns: 250px 1fr 350px;
  }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1023px) {
  .app-container {
    display: grid;
    grid-template-columns: 200px 1fr;
  }
  .details-panel {
    display: none;
  }
}

/* Mobile */
@media (max-width: 767px) {
  .app-container {
    display: flex;
    flex-direction: column;
  }
  .sidebar {
    display: none;
  }
  .details-panel {
    display: none;
  }
}
```

---

## 4. JAVASCRIPT ARCHITECTURE

### 4.1 API Client (`static/js/api.js`)

```javascript
class APIClient {
  constructor(baseURL = '/api') {
    this.baseURL = baseURL;
    this.token = localStorage.getItem('authToken');
  }

  async _request(method, endpoint, data = null) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.token}`
    };

    const options = {
      method,
      headers,
      ...(data && { body: JSON.stringify(data) })
    };

    const response = await fetch(url, options);
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    return await response.json();
  }

  // Authentication
  async login(email, password) {
    const data = await this._request('POST', '/auth/login', {
      email,
      password
    });
    this.token = data.access_token;
    localStorage.setItem('authToken', this.token);
    return data;
  }

  async logout() {
    localStorage.removeItem('authToken');
    this.token = null;
  }

  // Conversations
  async createConversation() {
    return this._request('POST', '/conversations');
  }

  async getConversation(id) {
    return this._request('GET', `/conversations/${id}`);
  }

  async getConversations() {
    return this._request('GET', '/conversations');
  }

  // Messages
  async sendMessage(conversationId, content) {
    return this._request('POST', 
      `/conversations/${conversationId}/messages`,
      { content }
    );
  }

  // Listings
  async searchListings(query) {
    return this._request('POST', '/listings/search', query);
  }

  async getListingDetails(id) {
    return this._request('GET', `/listings/${id}`);
  }
}

// Global instance
window.api = new APIClient();
```

### 4.2 Chat UI Logic (`static/js/chat.js`)

```javascript
class ChatUI {
  constructor(containerSelector) {
    this.container = document.querySelector(containerSelector);
    this.messagesContainer = this.container.querySelector('.messages-container');
    this.inputField = this.container.querySelector('#messageInput');
    this.sendBtn = this.container.querySelector('#sendBtn');
    this.currentConversationId = null;
    
    this.initEventListeners();
  }

  initEventListeners() {
    this.sendBtn.addEventListener('click', () => this.handleSendMessage());
    this.inputField.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSendMessage();
      }
    });
  }

  async handleSendMessage() {
    const content = this.inputField.value.trim();
    if (!content) return;

    // Add user message to UI
    this.addMessage(content, 'user');
    this.inputField.value = '';
    this.setStatusLoading();

    try {
      // Send to backend
      const response = await window.api.sendMessage(
        this.currentConversationId,
        content
      );

      // Add agent response
      this.addMessage(response.content, 'agent');

      // Update suggestions if provided
      if (response.suggestions) {
        this.updateSuggestions(response.suggestions);
      }

      // Update listings if provided
      if (response.listings) {
        this.updateListings(response.listings);
      }

      this.setStatusReady();
    } catch (error) {
      this.addMessage('Có lỗi xảy ra. Vui lòng thử lại.', 'error');
      this.setStatusError();
    }
  }

  addMessage(content, role = 'user') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    
    const text = document.createElement('p');
    text.textContent = content;
    
    const timestamp = document.createElement('span');
    timestamp.className = 'timestamp';
    timestamp.textContent = new Date().toLocaleTimeString('vi-VN');
    
    messageDiv.appendChild(text);
    messageDiv.appendChild(timestamp);
    this.messagesContainer.appendChild(messageDiv);
    
    // Auto-scroll to bottom
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  updateSuggestions(suggestions) {
    const area = this.container.querySelector('.suggestions-area');
    area.innerHTML = suggestions.map(s => 
      `<div class="suggestion-chip">${s}</div>`
    ).join('');
  }

  updateListings(listings) {
    const panel = this.container.querySelector('.details-panel');
    panel.innerHTML = listings.map(l => `
      <div class="listing-card">
        <img src="${l.image}" alt="${l.brand}">
        <h4>${l.brand} ${l.model}</h4>
        <p class="price">${l.price.toLocaleString('vi-VN')} ₫</p>
        <button onclick="bookViewing('${l.id}')" class="btn-action">
          Book Viewing
        </button>
      </div>
    `).join('');
  }

  setStatusLoading() {
    document.getElementById('statusIndicator').textContent = 'Loading...';
    document.getElementById('statusIndicator').className = 'status loading';
  }

  setStatusReady() {
    document.getElementById('statusIndicator').textContent = 'Ready';
    document.getElementById('statusIndicator').className = 'status ready';
  }

  setStatusError() {
    document.getElementById('statusIndicator').textContent = 'Error';
    document.getElementById('statusIndicator').className = 'status error';
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  window.chatUI = new ChatUI('.chat-area');
  window.chatUI.currentConversationId = getConversationIdFromURL();
});
```

### 4.3 Main App Logic (`static/js/main.js`)

```javascript
class PentaMoApp {
  constructor() {
    this.currentUser = null;
    this.currentConversation = null;
    this.conversationList = [];
    
    this.init();
  }

  async init() {
    // Check authentication
    const token = localStorage.getItem('authToken');
    if (!token) {
      window.location.href = '/login.html';
      return;
    }

    // Load user data
    await this.loadCurrentUser();
    
    // Load conversations
    await this.loadConversations();
    
    // Initialize UI
    this.initializeUI();
  }

  async loadCurrentUser() {
    try {
      this.currentUser = await window.api._request('GET', '/users/me');
      this.updateUserDisplay();
    } catch (error) {
      console.error('Failed to load user:', error);
      this.logout();
    }
  }

  async loadConversations() {
    try {
      this.conversationList = await window.api.getConversations();
      this.renderConversationList();
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }

  renderConversationList() {
    const list = document.querySelector('.conversation-list');
    list.innerHTML = this.conversationList.map(conv => `
      <div class="conversation-item" data-id="${conv.id}">
        <span class="conv-title">${conv.title || 'Untitled'}</span>
        <span class="conv-time">${this.formatTime(conv.created_at)}</span>
      </div>
    `).join('');

    // Add click handlers
    list.querySelectorAll('.conversation-item').forEach(item => {
      item.addEventListener('click', () => {
        this.selectConversation(item.dataset.id);
      });
    });
  }

  async selectConversation(id) {
    this.currentConversation = await window.api.getConversation(id);
    window.chatUI.currentConversationId = id;
    this.loadConversationMessages();
  }

  async createNewConversation() {
    const conv = await window.api.createConversation();
    this.conversationList.unshift(conv);
    this.renderConversationList();
    this.selectConversation(conv.id);
  }

  loadConversationMessages() {
    const messagesContainer = document.querySelector('.messages-container');
    messagesContainer.innerHTML = '';
    
    this.currentConversation.messages.forEach(msg => {
      window.chatUI.addMessage(msg.content, msg.role);
    });
  }

  updateUserDisplay() {
    const nameElement = document.querySelector('.user-name');
    if (nameElement) {
      nameElement.textContent = this.currentUser.email;
    }
  }

  async logout() {
    await window.api.logout();
    window.location.href = '/login.html';
  }

  initializeUI() {
    // New Chat Button
    document.getElementById('newChat').addEventListener('click', () => {
      this.createNewConversation();
    });

    // Logout Button
    document.getElementById('logout').addEventListener('click', () => {
      this.logout();
    });

    // Settings Button
    document.getElementById('settings').addEventListener('click', () => {
      this.openSettings();
    });
  }

  formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString('vi-VN');
  }

  openSettings() {
    // TODO: Implement settings modal
    alert('Settings coming soon!');
  }
}

// Initialize app on page load
document.addEventListener('DOMContentLoaded', () => {
  window.app = new PentaMoApp();
});
```

---

## 5. USER FLOW DIAGRAMS

### 5.1 Chat User Flow

```
┌─────────────┐
│   Login     │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Home/Dashboard │
└──────┬──────────┘
       │
       ├─> New Chat ──> Create Conversation
       │
       ├─> Select Chat ──> Load Messages
       │
       ▼
┌─────────────────┐
│  Send Message   │
└──────┬──────────┘
       │
       ▼
┌─────────────────────────────┐
│  Wait for Agent Response    │
│  (Orchestrator processing)  │
└──────┬──────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  Display:                    │
│  - Agent Message             │
│  - Listings (if search)      │
│  - Quick Actions             │
│  - Suggestions               │
└──────┬───────────────────────┘
       │
       ├─> Book Viewing ──> Schedule
       │
       ├─> View Details ──> Show Listing
       │
       ├─> Compare ──> Show Comparison
       │
       └─> Continue Chat ──> Back to Send Message
```

### 5.2 Admin Flow

```
┌──────────────┐
│  Admin Login │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│  Admin Dashboard     │
└──────┬───────────────┘
       │
       ├─> View Statistics
       │   ├─> Active Users
       │   ├─> Total Conversations
       │   └─> System Health
       │
       ├─> Manage Listings
       │   ├─> View All
       │   ├─> Edit
       │   ├─> Delete
       │   └─> Add New
       │
       ├─> Manage Users
       │   ├─> View All
       │   ├─> Ban/Unban
       │   ├─> Change Role
       │   └─> View Profile
       │
       └─> View System Logs
           ├─> Filter by Date
           ├─> Search by Keyword
           └─> Export Logs
```

---

## 6. RESPONSIVE DESIGN

### 6.1 Breakpoints

```css
/* Mobile: < 768px */
.sidebar { display: none; }
.details-panel { display: none; }

/* Tablet: 768px - 1024px */
.sidebar { width: 200px; }
.details-panel { display: none; }

/* Desktop: > 1024px */
.sidebar { width: 250px; }
.details-panel { width: 350px; }
```

### 6.2 Mobile Optimization

- Touch-friendly buttons (min 44x44px)
- Vertical layout for mobile
- Hamburger menu for navigation
- Bottom input area for easier typing
- Full-width chat messages

---

## 7. ACCESSIBILITY

- Semantic HTML (`<header>`, `<main>`, `<aside>`)
- ARIA labels for interactive elements
- Keyboard navigation support
- High contrast color scheme
- Readable font sizes
- Form labels associated with inputs

```html
<button aria-label="Send message" id="sendBtn">
  <span aria-hidden="true">→</span>
</button>

<input 
  id="messageInput"
  aria-label="Chat message input"
  placeholder="Nhập tin nhắn..."
/>
```

---

## 8. PERFORMANCE OPTIMIZATION

### 8.1 Frontend

- Lazy loading for images
- CSS minification
- JavaScript bundling
- Debouncing for resize/scroll events
- Local caching of conversations
- Virtual scrolling for long message lists

### 8.2 Network

- WebSocket for real-time updates (future)
- Message compression
- Request batching
- Conditional requests (ETag, Last-Modified)

---

## 9. SECURITY

- JWT tokens in localStorage
- CSRF protection (tokens)
- Input validation & sanitization
- XSS prevention (escaping)
- Rate limiting on API calls
- HTTPS only in production

---

## File Structure Summary

```
pentaMo/
├── static/
│   ├── css/
│   │   └── main.css
│   └── js/
│       ├── api.js          # API client
│       └── chat.js         # Chat UI logic
├── assets/
│   ├── css/
│   │   ├── home.css        # Home styles
│   │   ├── pages.css       # Page styles
│   │   └── style.css       # Global styles
│   ├── js/
│   │   ├── home.js         # Home logic
│   │   └── main.js         # Main app
│   └── icons/
├── admin/
│   ├── __init__.py
│   └── routes.py           # Admin endpoints
├── index.html              # Home page
├── login.html              # Login page
└── ...
```

---

**Cập nhật:** Tháng 4, 2026
**Version:** 2.0.0
