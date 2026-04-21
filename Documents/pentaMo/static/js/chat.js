/**
 * PentaMo Chat UI Manager
 * Quản lý giao diện chat, input/output
 */

class ChatUI {
  constructor() {
    this.messages = [];
    this.conversationId = null;
    this.isLoading = false;
    this.initializeEventListeners();
    this.initializeConversation();
  }

  async initializeConversation() {
    try {
      const response = await api.createConversation('Chat với PentaMo');
      this.conversationId = response.id;
      console.log('✅ Created conversation:', this.conversationId);
    } catch (error) {
      console.error('❌ Failed to create conversation:', error);
      this.showError('Không thể tạo cuộc trò chuyện. Vui lòng tải lại trang.');
    }
  }

  initializeEventListeners() {
    const sendBtn = document.getElementById('send-btn');
    const messageInput = document.getElementById('message-input');

    if (sendBtn) {
      sendBtn.addEventListener('click', () => this.sendMessage());
    }

    if (messageInput) {
      messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
    }
  }

  async sendMessage() {
    const messageInput = document.getElementById('message-input');
    if (!messageInput) return;

    const text = messageInput.value.trim();
    if (!text || this.isLoading) return;

    // Thêm user message vào UI
    this.addMessage({
      role: 'user',
      content: text,
      timestamp: new Date().toISOString()
    });

    messageInput.value = '';
    this.isLoading = true;

    try {
      const response = await api.sendMessage(this.conversationId, text);
      
      if (response.success) {
        // Thêm agent response
        this.addMessage({
          role: 'assistant',
          content: response.response,
          timestamp: response.timestamp,
          metadata: response.metadata
        });
      } else {
        this.showError('⚠️ ' + (response.error || 'Lỗi khi xử lý tin nhắn'));
      }
    } catch (error) {
      console.error('❌ Error sending message:', error);
      this.showError('❌ Kết nối thất bại. Vui lòng thử lại.');
    } finally {
      this.isLoading = false;
    }
  }

  addMessage(message) {
    this.messages.push(message);
    this.renderMessage(message);
    this.scrollToBottom();
  }

  renderMessage(message) {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    const messageEl = document.createElement('div');
    messageEl.className = `message message-${message.role}`;

    let content = message.content;
    
    // Xử lý metadata (listings, appointments, etc.)
    if (message.metadata) {
      content += this.renderMetadata(message.metadata);
    }

    messageEl.innerHTML = `
      <div class="message-bubble">
        ${content}
        <div class="message-time">${new Date(message.timestamp).toLocaleTimeString('vi-VN')}</div>
      </div>
    `;

    container.appendChild(messageEl);
  }

  renderMetadata(metadata) {
    let html = '';

    if (metadata.listings && metadata.listings.length > 0) {
      html += '<div class="listings-container">';
      metadata.listings.forEach(listing => {
        html += `
          <div class="listing-card">
            <div class="listing-brand">${listing.brand} ${listing.model_line}</div>
            <div class="listing-year">${listing.model_year}</div>
            <div class="listing-price">${this.formatPrice(listing.price)}</div>
            <div class="listing-location">${listing.province}</div>
            <button class="btn-detail" onclick="showListingDetail('${listing.id}')">Chi tiết</button>
          </div>
        `;
      });
      html += '</div>';
    }

    return html;
  }

  formatPrice(price) {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(price);
  }

  showError(message) {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    const errorEl = document.createElement('div');
    errorEl.className = 'message message-error';
    errorEl.innerHTML = `<div class="message-bubble">${message}</div>`;
    container.appendChild(errorEl);
    this.scrollToBottom();
  }

  scrollToBottom() {
    const container = document.getElementById('chat-messages');
    if (container) {
      setTimeout(() => {
        container.scrollTop = container.scrollHeight;
      }, 100);
    }
  }

  loading(show = true) {
    this.isLoading = show;
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) {
      sendBtn.disabled = show;
    }
  }
}

// Global instance
const chatUI = new ChatUI();

// ========== Helper Functions ==========
function showListingDetail(listingId) {
  // TODO: Implement modal/detail view
  console.log('Show detail for listing:', listingId);
}
