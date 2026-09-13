/**
 * CleanRoute AI — Conversational Assistant Controller
 * 
 * ARCHITECTURAL FLOW:
 * Chat UI -> chat.js -> api.js -> Django REST API (/api/chat/) -> Local ChromaDB RAG
 * 
 * Features:
 * - Real-time conversational interface with typing simulation
 * - Active route context detection from sessionStorage
 * - Dynamic citation rendering for retrieved knowledge base sources (Markdown files)
 * - Responsible AI non-medical disclosure compliance
 */

const CleanRouteChat = (() => {
  'use strict';

  const messagesContainerId = 'chat-messages-pane';
  const inputFieldId = 'chat-input';
  const chatFormId = 'chat-form';
  const typingIndicatorId = 'chat-typing-indicator';
  const contextIndicatorId = 'chat-context-indicator';
  const contextTextId = 'chat-context-text';

  let activeRouteContext = null;

  /**
   * Load active search context if the user came from an active route search
   */
  function loadActiveRouteContext() {
    try {
      const stored = sessionStorage.getItem('cleanroute_last_search');
      if (stored) {
        activeRouteContext = JSON.parse(stored);
        displayRouteContextBanner(activeRouteContext);
      }
    } catch (e) {
      console.warn("Could not parse active route context from sessionStorage:", e);
    }
  }

  /**
   * Render route context banner above suggested queries
   */
  function displayRouteContextBanner(ctx) {
    const banner = document.getElementById(contextIndicatorId);
    const textElem = document.getElementById(contextTextId);
    if (!banner || !textElem || !ctx) return;

    const origin = ctx.origin_name || (ctx.origin && ctx.origin.name) || "Origin";
    const dest = ctx.destination_name || (ctx.destination && ctx.destination.name) || "Destination";
    const mode = ctx.travel_mode || ctx.mode || "Cycling";
    const pref = ctx.route_preference || ctx.priority_preference || ctx.preference || "Balanced";

    textElem.textContent = `Active Trip: ${origin} → ${dest} (${mode.charAt(0).toUpperCase() + mode.slice(1)} • ${pref})`;
    banner.style.display = 'flex';
  }

  /**
   * Append a message bubble to the chat thread
   */
  function appendMessage(sender, text, timestamp, sources = [], disclaimer = null, isDemo = false) {
    const container = document.getElementById(messagesContainerId);
    if (!container) return;

    const time = timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const isUser = sender === 'user';

    const row = document.createElement('div');
    row.className = `message-row ${isUser ? 'user-message' : 'bot-message'}`;

    const avatarHtml = isUser
      ? `<div class="message-avatar user-avatar-icon" title="You">
           <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
         </div>`
      : `<div class="message-avatar bot-avatar-icon" title="CleanRoute AI">
           <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
         </div>`;

    // Render source chips if bot message has citations
    let sourcesHtml = '';
    if (!isUser && Array.isArray(sources) && sources.length > 0) {
      const tags = sources.map(s => `<span class="chat-source-tag">${escapeHtml(s)}</span>`).join('');
      sourcesHtml = `
        <div class="chat-sources">
          <span class="chat-sources-label">Sources:</span>
          ${tags}
        </div>
      `;
    }

    // Render disclaimer if bot message has one
    let disclaimerHtml = '';
    if (!isUser && disclaimer) {
      disclaimerHtml = `
        <div class="chat-disclaimer-note">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0; margin-top:2px;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <span>${escapeHtml(disclaimer)}</span>
        </div>
      `;
    }

    const badgeHtml = !isUser
      ? (isDemo
          ? '<span class="badge-demo" style="font-size: 0.6rem; padding: 0.1rem 0.35rem; margin-left: 0.25rem;">Demo</span>'
          : '<span class="badge-rag" style="font-size: 0.6rem; padding: 0.1rem 0.35rem; margin-left: 0.25rem;">Local RAG</span>')
      : '';

    row.innerHTML = `
      ${avatarHtml}
      <div style="max-width: 100%;">
        <div class="message-bubble ${isUser ? 'user-bubble' : 'bot-bubble'}">
          ${formatBotMessage(text)}
          ${sourcesHtml}
          ${disclaimerHtml}
        </div>
        <div class="message-timestamp">
          <span>${time}</span>
          ${badgeHtml}
        </div>
      </div>
    `;

    container.appendChild(row);
    scrollToBottom();
  }

  /**
   * Escape HTML to prevent injection
   */
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /**
   * Simple formatter for line breaks in bot messages
   */
  function formatBotMessage(text) {
    if (!text) return '';
    return text
      .split('\n\n')
      .map(p => `<p style="margin-bottom: 0.5rem; margin-top: 0;">${escapeHtml(p).replace(/\n/g, '<br>')}</p>`)
      .join('');
  }

  /**
   * Show/hide typing indicator
   */
  function setTyping(isTyping) {
    const indicator = document.getElementById(typingIndicatorId);
    if (!indicator) return;

    indicator.style.display = isTyping ? 'flex' : 'none';
    if (isTyping) scrollToBottom();
  }

  /**
   * Scroll thread to latest message
   */
  function scrollToBottom() {
    const container = document.getElementById(messagesContainerId);
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }

  /**
   * Send a query through the assistant pipeline
   */
  async function handleSendQuery(userText) {
    const text = userText.trim();
    if (!text) return;

    // 1. Append User Message
    appendMessage('user', text);

    // 2. Clear input
    const input = document.getElementById(inputFieldId);
    if (input) input.value = '';

    // 3. Show typing indicator
    setTyping(true);

    try {
      // 4. Send to API service with active route context
      const response = await window.CleanRouteAPI.sendChatMessage(text, activeRouteContext);
      setTyping(false);
      appendMessage(
        'bot',
        response.reply,
        response.timestamp,
        response.sources,
        response.disclaimer,
        response.isDemo
      );
    } catch (err) {
      setTyping(false);
      appendMessage(
        'bot',
        "I am currently having trouble processing that request through the local RAG pipeline. Please verify the backend server is running and try again.",
        null,
        [],
        "CleanRoute AI provides informational estimates and does not offer medical advice.",
        false
      );
    }
  }

  /**
   * Bind event listeners for chat interface
   */
  function init() {
    loadActiveRouteContext();

    const form = document.getElementById(chatFormId);
    const input = document.getElementById(inputFieldId);

    if (form && input) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        handleSendQuery(input.value);
      });
    }

    // Bind suggestion chips
    const chips = document.querySelectorAll('.chat-suggestion-chip');
    chips.forEach((chip) => {
      chip.addEventListener('click', () => {
        const queryText = chip.getAttribute('data-query') || chip.textContent.trim();
        handleSendQuery(queryText);
      });
    });
  }

  return {
    init,
    handleSendQuery,
    loadActiveRouteContext
  };
})();

// Auto-run if on chat.html
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('chat-form')) {
    CleanRouteChat.init();
  }
});
