/**
 * PentaMo API Client
 * Kết nối với FastAPI Backend
 */

class PentaMoAPI {
  constructor(baseURL = '/api') {
    this.baseURL = baseURL;
    this.token = localStorage.getItem('pentamo_token');
    this.refreshToken = localStorage.getItem('pentamo_refresh');
  }

  // ========== Auth ==========
  async login(username, password) {
    const response = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (response.ok) {
      const data = await response.json();
      this.token = data.access_token;
      this.refreshToken = data.refresh_token;
      localStorage.setItem('pentamo_token', this.token);
      localStorage.setItem('pentamo_refresh', this.refreshToken);
      return data;
    }
    throw new Error(`Login failed: ${response.statusText}`);
  }

  async refreshAccessToken() {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }
    
    try {
      const response = await fetch(`${this.baseURL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken })
      });
      
      if (response.ok) {
        const data = await response.json();
        this.token = data.access_token;
        localStorage.setItem('pentamo_token', this.token);
        return data;
      } else if (response.status === 401) {
        this.logout();
        throw new Error('Refresh token expired - please login again');
      }
    } catch (error) {
      this.logout();
      throw error;
    }
  }

  async logout() {
    localStorage.removeItem('pentamo_token');
    localStorage.removeItem('pentamo_refresh');
    this.token = null;
    this.refreshToken = null;
  }

  // ========== Conversations & Chat ==========
  async createConversation(title = 'New Chat') {
    const response = await this._fetchWithAuth(`${this.baseURL}/conversations`, {
      method: 'POST',
      body: JSON.stringify({ title })
    });
    return response.json();
  }

  async getConversation(conversationId) {
    const response = await this._fetchWithAuth(`${this.baseURL}/conversations/${conversationId}`, {
      method: 'GET'
    });
    return response.json();
  }

  async sendMessage(conversationId, text) {
    const response = await this._fetchWithAuth(`${this.baseURL}/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content: text })
    });
    return response.json();
  }

  // ========== Search Listings ==========
  async searchListings(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const response = await this._fetchWithAuth(`${this.baseURL}/search?${queryString}`, {
      method: 'GET'
    });
    return response.json();
  }

  async getListingDetail(listingId) {
    const response = await this._fetchWithAuth(`${this.baseURL}/listings/${listingId}`, {
      method: 'GET'
    });
    return response.json();
  }

  // ========== Appointments ==========
  async bookAppointment(listingId, preferredDate, location) {
    const response = await this._fetchWithAuth(`${this.baseURL}/appointments`, {
      method: 'POST',
      body: JSON.stringify({
        listing_id: listingId,
        preferred_date: preferredDate,
        location: location
      })
    });
    return response.json();
  }

  // ========== Health ==========
  async healthCheck() {
    const response = await fetch(`${this.baseURL}/../health`);
    return response.json();
  }

  // ========== Helper ==========
  _headers() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async _fetchWithAuth(url, options = {}) {
    // Add auth headers if not already present
    if (!options.headers) {
      options.headers = {};
    }
    
    const headers = this._headers();
    options.headers = { ...headers, ...options.headers };
    
    let response = await fetch(url, options);
    
    // If 401, try to refresh token and retry once
    if (response.status === 401 && this.refreshToken) {
      try {
        await this.refreshAccessToken();
        // Retry the request with new token
        options.headers['Authorization'] = `Bearer ${this.token}`;
        response = await fetch(url, options);
      } catch (error) {
        console.error('Token refresh failed:', error);
        // Return the original 401 response
        return response;
      }
    }
    
    return response;
  }
}

// Global instance
const api = new PentaMoAPI();
