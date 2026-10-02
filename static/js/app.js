/**
 * LazyMail — Reactive Frontend Application
 * Fully Localized: Turkish (Default) & English
 */

const state = {
  currentLang: localStorage.getItem('lazymail_lang') || 'tr', // Default: Turkish
  user: null,
  currentFolder: 'inbox', // 'inbox' | 'sent'
  currentView: 'mail',    // 'mail' | 'settings' | 'purge'
  selectedEmailId: null,
  selectedEmailData: null,
  emails: [],
  searchQuery: '',
  stats: {
    received_count: 0,
    sent_count: 0,
    max_sent_limit: 50,
    max_inbox_limit: 50
  },
  config: null,
  pendingPurgeTarget: null
};

// --- DOM ELEMENTS CACHE ---
const elements = {
  // Auth
  authModal: document.getElementById('auth-modal'),
  authTitle: document.getElementById('auth-title'),
  authSubtitle: document.getElementById('auth-subtitle'),
  setupForm: document.getElementById('setup-form'),
  loginForm: document.getElementById('login-form'),
  setupUsername: document.getElementById('setup-username'),
  setupEmailPreview: document.getElementById('setup-email-preview'),
  setupPassword: document.getElementById('setup-password'),
  setupPasswordConfirm: document.getElementById('setup-password-confirm'),
  btnToggleSetupPassword: document.getElementById('btn-toggle-setup-password'),
  loginUsername: document.getElementById('login-username'),
  loginPassword: document.getElementById('login-password'),
  btnToggleLoginPassword: document.getElementById('btn-toggle-login-password'),
  btnLogout: document.getElementById('btn-logout'),
  currentUsernameDisplay: document.getElementById('current-username-display'),
  userAvatarInitials: document.getElementById('user-avatar-initials'),

  // Mobile Navigation
  btnMobileSidebarToggle: document.getElementById('btn-mobile-sidebar-toggle'),
  btnSidebarClose: document.getElementById('btn-sidebar-close'),
  sidebarBackdrop: document.getElementById('sidebar-backdrop'),
  appSidebar: document.getElementById('app-sidebar'),
  btnDetailBack: document.getElementById('btn-detail-back'),

  // Navigation & Badges
  navInbox: document.getElementById('nav-tab-inbox'),
  navSent: document.getElementById('nav-tab-sent'),
  navPurge: document.getElementById('nav-tab-purge'),
  navSettings: document.getElementById('nav-tab-settings'),
  badgeInbox: document.getElementById('badge-inbox-count'),
  badgeSent: document.getElementById('badge-sent-count'),
  connectionPill: document.getElementById('connection-pill'),
  connectionStatusText: document.getElementById('connection-status-text'),
  storageSentStat: document.getElementById('storage-sent-stat'),
  storageInboxStat: document.getElementById('storage-inbox-stat'),
  storagePercentage: document.getElementById('storage-percentage'),
  storageProgressFill: document.getElementById('storage-progress-fill'),

  // Views
  viewMail: document.getElementById('view-mail'),
  viewSettings: document.getElementById('view-settings'),
  viewPurge: document.getElementById('view-purge'),
  currentFolderTitle: document.getElementById('current-folder-title'),
  folderMetaSub: document.getElementById('folder-meta-sub'),

  // List & Detail
  emailItemsContainer: document.getElementById('email-items-container'),
  emailDetailColumn: document.getElementById('email-detail-column'),
  detailEmptyPlaceholder: document.getElementById('detail-empty-placeholder'),
  detailContent: document.getElementById('detail-content'),
  detailSubject: document.getElementById('detail-subject'),
  detailSender: document.getElementById('detail-sender'),
  detailSenderEmail: document.getElementById('detail-sender-email'),
  detailRecipient: document.getElementById('detail-recipient'),
  detailDate: document.getElementById('detail-date'),
  detailAvatar: document.getElementById('detail-avatar'),
  detailBodyIframe: document.getElementById('detail-body-iframe'),
  detailBodyPlain: document.getElementById('detail-body-plain'),
  detailBodyHtmlWrapper: document.getElementById('detail-body-html-wrapper'),
  btnViewRendered: document.getElementById('btn-view-rendered'),
  btnViewPlain: document.getElementById('btn-view-plain'),
  btnCloseDetail: document.getElementById('btn-close-detail'),
  btnReply: document.getElementById('btn-reply'),

  // Actions & Search
  btnSyncInbox: document.getElementById('btn-sync-inbox'),
  syncIcon: document.getElementById('sync-icon'),
  globalSearchInput: document.getElementById('global-search-input'),
  btnSearchClear: document.getElementById('btn-search-clear'),
  btnThemeToggle: document.getElementById('btn-theme-toggle'),

  // Compose Modal
  composeModal: document.getElementById('compose-modal'),
  btnComposeOpen: document.getElementById('btn-compose-open'),
  btnComposeClose: document.getElementById('btn-compose-close'),
  btnComposeDiscard: document.getElementById('btn-compose-discard'),
  composeForm: document.getElementById('compose-form'),
  composeTo: document.getElementById('compose-to'),
  composeSubject: document.getElementById('compose-subject'),
  composeMessage: document.getElementById('compose-message'),

  // Settings
  settingsForm: document.getElementById('settings-form'),
  cfgEmail: document.getElementById('cfg-email'),
  cfgPassword: document.getElementById('cfg-password'),
  cfgSenderName: document.getElementById('cfg-sender-name'),
  cfgImapHost: document.getElementById('cfg-imap-host'),
  cfgImapPort: document.getElementById('cfg-imap-port'),
  cfgSmtpHost: document.getElementById('cfg-smtp-host'),
  cfgSmtpPort: document.getElementById('cfg-smtp-port'),
  btnTestConnection: document.getElementById('btn-test-connection'),
  testResultBox: document.getElementById('test-connection-result'),
  btnTogglePasswordView: document.getElementById('btn-toggle-password-view'),
  passwordStatusHint: document.getElementById('password-status-hint'),

  // Purge
  purgeCountInbox: document.getElementById('purge-count-inbox'),
  purgeCountSent: document.getElementById('purge-count-sent'),
  btnPurgeSent: document.getElementById('btn-purge-sent'),
  btnPurgeReceived: document.getElementById('btn-purge-received'),
  btnPurgeAll: document.getElementById('btn-purge-all'),

  // Confirm Modal
  confirmModal: document.getElementById('confirm-modal'),
  confirmModalTitle: document.getElementById('confirm-modal-title'),
  confirmModalMessage: document.getElementById('confirm-modal-message'),
  btnConfirmCancel: document.getElementById('btn-confirm-cancel'),
  btnConfirmProceed: document.getElementById('btn-confirm-proceed'),

  // Toast
  toastContainer: document.getElementById('toast-container')
};

// --- INTERNATIONALIZATION (i18n) HELPERS ---
function t(key, params = {}) {
  const lang = state.currentLang || 'tr';
  const allTranslations = (typeof window !== 'undefined' && window.translations) 
    ? window.translations 
    : (typeof translations !== 'undefined' ? translations : null);

  const dict = (allTranslations && allTranslations[lang]) 
    ? allTranslations[lang] 
    : (allTranslations && allTranslations['tr'] ? allTranslations['tr'] : {});
  
  let text = dict[key] || (allTranslations && allTranslations['en'] ? allTranslations['en'][key] : key) || key;
  for (const [p, val] of Object.entries(params)) {
    text = text.replace(new RegExp(`\\{${p}\\}`, 'g'), val);
  }
  return text;
}

function applyLanguage(lang) {
  state.currentLang = lang;
  localStorage.setItem('lazymail_lang', lang);
  document.documentElement.lang = lang;

  // Update all language switcher buttons active states
  document.querySelectorAll('.lang-btn').forEach(btn => {
    if (btn.getAttribute('data-lang') === lang) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Translate static text elements
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (key) el.innerText = t(key);
  });

  // Translate HTML elements
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const key = el.getAttribute('data-i18n-html');
    if (key) el.innerHTML = t(key);
  });

  // Translate placeholders
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (key) el.placeholder = t(key);
  });

  // Translate titles / tooltips
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    if (key) el.title = t(key);
  });

  // Update dynamic navigation folder headers
  if (state.currentFolder === 'inbox') {
    elements.currentFolderTitle.innerText = t('folder_inbox');
    elements.folderMetaSub.innerText = t('folder_inbox_meta');
  } else if (state.currentFolder === 'sent') {
    elements.currentFolderTitle.innerText = t('folder_sent');
    elements.folderMetaSub.innerText = t('folder_sent_meta');
  }

  // Update connection pill
  if (!state.config || !state.config.is_configured) {
    elements.connectionStatusText.innerText = t('status_not_configured');
  }

  // Refresh storage labels
  renderStats();

  // Re-render email list for date localization & empty states
  renderEmailList();

  // Re-render detail view if active
  if (state.selectedEmailData) {
    renderDetailView(state.selectedEmailData);
  }
}

// --- TOAST NOTIFICATIONS ---
function showToast(message, type = 'info', duration = 4000) {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${escapeHtml(message)}</span>`;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.innerText = str;
  return div.innerHTML;
}

// --- API CLIENT ---
async function apiRequest(endpoint, options = {}) {
  const defaults = {
    headers: {
      'Content-Type': 'application/json'
    }
  };
  const config = { ...defaults, ...options };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  try {
    const res = await fetch(endpoint, config);
    if (res.status === 401 && !endpoint.includes('/api/auth/')) {
      showAuthModal(false);
      throw new Error('Session expired. Please log in.');
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = data.detail || data.message || `Request failed with status ${res.status}`;
      throw new Error(err);
    }
    return data;
  } catch (err) {
    throw err;
  }
}

// --- AUTH & INITIALIZATION ---
async function checkAuthStatus() {
  try {
    const status = await apiRequest('/api/auth/status');
    if (status.setup_required) {
      showAuthModal(true);
    } else if (!status.logged_in) {
      showAuthModal(false);
    } else {
      hideAuthModal();
      setLoggedInUser(status.username);
      updateConnectionStatus(status.has_email_config, status.configured_email);
      await loadInitialData();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function showAuthModal(isSetup = false) {
  elements.authModal.classList.add('active');
  if (isSetup) {
    elements.authTitle.innerText = t('setup_title');
    elements.authSubtitle.innerText = t('setup_subtitle');
    elements.setupForm.classList.remove('hidden');
    elements.loginForm.classList.add('hidden');
  } else {
    elements.authTitle.innerText = t('login_title');
    elements.authSubtitle.innerText = t('login_subtitle');
    elements.setupForm.classList.add('hidden');
    elements.loginForm.classList.remove('hidden');
  }
}

function hideAuthModal() {
  elements.authModal.classList.remove('active');
}

function setLoggedInUser(username) {
  state.user = username;
  elements.currentUsernameDisplay.innerText = username || 'Admin';
  elements.userAvatarInitials.innerText = (username || 'A').charAt(0).toUpperCase();
}

function updateConnectionStatus(isConfigured, email) {
  if (isConfigured && email) {
    elements.connectionPill.className = 'status-pill status-connected';
    elements.connectionStatusText.innerText = email;
    elements.connectionPill.title = `${t('status_connected_to')}${email}`;
  } else {
    elements.connectionPill.className = 'status-pill status-disconnected';
    elements.connectionStatusText.innerText = t('status_not_configured');
    elements.connectionPill.title = t('status_not_configured');
  }
}

// --- DATA FETCHING ---
async function loadInitialData() {
  await Promise.all([
    fetchStats(),
    loadEmailConfig(),
    loadEmails(state.currentFolder)
  ]);
}

async function fetchStats() {
  try {
    const stats = await apiRequest('/api/stats');
    state.stats = stats;
    renderStats();
  } catch (err) {
    console.error('Failed to fetch stats:', err);
  }
}

function renderStats() {
  const { received_count, sent_count, max_sent_limit, max_inbox_limit } = state.stats;
  elements.badgeInbox.innerText = received_count;
  elements.badgeSent.innerText = `${sent_count}/${max_sent_limit}`;
  elements.storageSentStat.innerText = `${sent_count}/${max_sent_limit} ${t('storage_sent')}`;
  elements.storageInboxStat.innerText = `${received_count}/${max_inbox_limit} ${t('storage_inbox')}`;
  elements.purgeCountInbox.innerText = received_count;
  elements.purgeCountSent.innerText = `${sent_count} / ${max_sent_limit}`;

  const totalMax = max_sent_limit + max_inbox_limit;
  const currentTotal = received_count + sent_count;
  const pct = Math.min(100, Math.round((currentTotal / totalMax) * 100));
  elements.storagePercentage.innerText = `${pct}%`;
  elements.storageProgressFill.style.width = `${pct}%`;
}

async function loadEmails(folder = 'inbox', query = '') {
  const endpoint = folder === 'inbox'
    ? `/api/emails/inbox${query ? `?q=${encodeURIComponent(query)}` : ''}`
    : `/api/emails/sent${query ? `?q=${encodeURIComponent(query)}` : ''}`;

  elements.emailItemsContainer.innerHTML = `
    <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
      <span class="btn-spinner" style="display:inline-block; margin-bottom: 0.5rem;"></span>
      <p>${t('loading_messages')}</p>
    </div>
  `;

  try {
    const res = await apiRequest(endpoint);
    state.emails = res.emails || [];
    renderEmailList();
    fetchStats();
  } catch (err) {
    elements.emailItemsContainer.innerHTML = `
      <div style="text-align: center; padding: 2rem; color: var(--danger);">
        <p>${t('load_emails_failed')}: ${escapeHtml(err.message)}</p>
      </div>
    `;
  }
}

// --- RENDER EMAIL LIST ---
function renderEmailList() {
  elements.emailItemsContainer.innerHTML = '';
  if (!state.emails.length) {
    const isSent = state.currentFolder === 'sent';
    elements.emailItemsContainer.innerHTML = `
      <div style="text-align: center; padding: 3rem 1.5rem; color: var(--text-muted);">
        <p style="font-weight: 600; font-size: 0.95rem; margin-bottom: 0.25rem;">
          ${isSent ? t('empty_sent_title') : t('empty_inbox_title')}
        </p>
        <p style="font-size: 0.8rem;">
          ${isSent ? t('empty_sent_desc') : t('empty_inbox_desc')}
        </p>
      </div>
    `;
    clearDetailView();
    return;
  }

  // Strictly sort by date & time descending so latest message is always at the very top
  state.emails.sort((a, b) => {
    const rawA = a.received_at || a.sent_at || '';
    const rawB = b.received_at || b.sent_at || '';
    const timeA = new Date(rawA.includes('T') ? rawA : rawA.replace(' ', 'T') + 'Z').getTime() || 0;
    const timeB = new Date(rawB.includes('T') ? rawB : rawB.replace(' ', 'T') + 'Z').getTime() || 0;
    if (timeB !== timeA) return timeB - timeA;
    return (b.id || 0) - (a.id || 0);
  });

  state.emails.forEach(item => {
    const card = document.createElement('div');
    const isSelected = state.selectedEmailId === item.id;
    const isUnread = state.currentFolder === 'inbox' && !item.is_read;

    card.className = `email-card ${isSelected ? 'selected' : ''} ${isUnread ? 'unread' : ''}`;
    card.id = `email-item-${item.id}`;

    const dateStr = formatDate(item.received_at || item.sent_at);
    const senderDisplay = state.currentFolder === 'inbox' 
      ? (item.sender || item.sender_email || t('unknown_sender')) 
      : `${t('label_to')}: ${item.recipient}`;
    const subjectDisplay = item.subject || t('no_subject');
    const snippetDisplay = item.snippet || item.body || t('empty_content');

    card.innerHTML = `
      <div class="card-top">
        <span class="card-sender">${escapeHtml(senderDisplay)}</span>
        <span class="card-date">${dateStr}</span>
      </div>
      <div class="card-subject">${escapeHtml(subjectDisplay)}</div>
      <div class="card-snippet">${escapeHtml(snippetDisplay)}</div>
    `;

    card.addEventListener('click', () => selectEmail(item.id));
    elements.emailItemsContainer.appendChild(card);
  });
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  try {
    const normalized = isoStr.includes('T') ? isoStr : isoStr.replace(' ', 'T') + 'Z';
    const d = new Date(normalized);
    if (isNaN(d.getTime())) return isoStr;

    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const locale = state.currentLang === 'tr' ? 'tr-TR' : 'en-US';
    const timeStr = d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });

    if (isToday) {
      const todayStr = state.currentLang === 'tr' ? 'Bugün' : 'Today';
      return `${timeStr} (${todayStr})`;
    }
    const isThisYear = d.getFullYear() === now.getFullYear();
    const dateStr = d.toLocaleDateString(locale, { 
      month: 'short', 
      day: 'numeric',
      ...(isThisYear ? {} : { year: '2-digit' })
    });
    return `${dateStr} ${timeStr}`;
  } catch {
    return isoStr;
  }
}

// --- SELECT & VIEW EMAIL ---
async function selectEmail(id) {
  state.selectedEmailId = id;

  // Highlight card
  document.querySelectorAll('.email-card').forEach(c => c.classList.remove('selected'));
  const card = document.getElementById(`email-item-${id}`);
  if (card) {
    card.classList.add('selected');
    card.classList.remove('unread');
  }

  const endpoint = state.currentFolder === 'inbox'
    ? `/api/emails/inbox/${id}`
    : `/api/emails/sent/${id}`;

  try {
    const email = await apiRequest(endpoint);
    state.selectedEmailData = email;
    renderDetailView(email);
  } catch (err) {
    showToast('Failed to load email details: ' + err.message, 'error');
  }
}

function renderDetailView(email) {
  elements.detailEmptyPlaceholder.classList.add('hidden');
  elements.detailContent.classList.remove('hidden');
  elements.emailDetailColumn.classList.add('active-mobile');

  const isInbox = state.currentFolder === 'inbox';
  elements.detailSubject.innerText = email.subject || t('no_subject');
  
  if (isInbox) {
    elements.detailSender.innerText = email.sender || t('unknown_sender');
    elements.detailSenderEmail.innerText = email.sender_email ? `<${email.sender_email}>` : '';
    elements.detailRecipient.innerText = email.recipient || t('to_me');
    elements.detailAvatar.innerText = (email.sender || 'U').charAt(0).toUpperCase();
    elements.btnReply.classList.remove('hidden');
  } else {
    elements.detailSender.innerText = t('to_me');
    elements.detailSenderEmail.innerText = '';
    elements.detailRecipient.innerText = email.recipient || '';
    elements.detailAvatar.innerText = 'M';
    elements.btnReply.classList.add('hidden');
  }

  const rawDate = email.received_at || email.sent_at || '';
  if (rawDate) {
    try {
      const normalized = rawDate.includes('T') ? rawDate : rawDate.replace(' ', 'T') + 'Z';
      const d = new Date(normalized);
      const locale = state.currentLang === 'tr' ? 'tr-TR' : 'en-US';
      elements.detailDate.innerText = !isNaN(d.getTime())
        ? d.toLocaleString(locale, { dateStyle: 'medium', timeStyle: 'short' })
        : rawDate;
    } catch {
      elements.detailDate.innerText = rawDate;
    }
  } else {
    elements.detailDate.innerText = '';
  }

  // Render Body
  const htmlContent = email.body_html || '';
  const plainText = email.body_plain || email.body || '';

  // Populate plain text preview
  elements.detailBodyPlain.innerText = plainText || t('no_plain_text');

  // Populate iframe securely using srcdoc
  const iframe = elements.detailBodyIframe;
  const sanitizedHtml = buildSanitizedEmailHtml(htmlContent, plainText);
  iframe.srcdoc = sanitizedHtml;

  // Reset view pills to Rendered View
  elements.btnViewRendered.classList.add('active');
  elements.btnViewPlain.classList.remove('active');
  elements.detailBodyHtmlWrapper.classList.remove('hidden');
  elements.detailBodyPlain.classList.add('hidden');
}

function buildSanitizedEmailHtml(htmlContent, plainText) {
  let content = (htmlContent || '').trim();

  // If there's no HTML content, render clean plain text with auto-links
  if (!content) {
    const escaped = escapeHtml(plainText || t('no_plain_text'));
    const linkified = escaped.replace(
      /(https?:\/\/[^\s<]+)/g,
      '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <base target="_blank">
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 14px;
      line-height: 1.65;
      color: #1e293b;
      background: #ffffff;
      padding: 20px;
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
    }
    a { color: #6366f1; text-decoration: underline; }
  </style>
</head>
<body>${linkified}</body>
</html>`;
  }

  // Pre-process HTML: strip harmful script tags
  content = content.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');

  const resetStyles = `
    <base target="_blank">
    <style>
      html, body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #1e293b;
        background-color: #ffffff;
        word-break: break-word;
        box-sizing: border-box;
        margin: 0;
        padding: 16px;
      }
      img {
        max-width: 100% !important;
        height: auto !important;
      }
      a {
        color: #6366f1;
      }
      table {
        max-width: 100% !important;
      }
      blockquote {
        border-left: 3px solid #cbd5e1;
        margin: 0.5em 0;
        padding-left: 12px;
        color: #64748b;
      }
    </style>
  `;

  // If content already has a <head> tag, inject our reset style and base target inside <head>
  if (/<head\b[^>]*>/i.test(content)) {
    return content.replace(/<head\b[^>]*>/i, `$&${resetStyles}`);
  }

  // If content has <html> tag without <head>, inject head right after <html>
  if (/<html\b[^>]*>/i.test(content)) {
    return content.replace(/<html\b[^>]*>/i, `$&<head>${resetStyles}</head>`);
  }

  // If content is an HTML fragment (no <html> or <head>), wrap in a clean full document
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  ${resetStyles}
</head>
<body>
  ${content}
</body>
</html>`;
}

function clearDetailView() {
  state.selectedEmailId = null;
  state.selectedEmailData = null;
  elements.detailEmptyPlaceholder.classList.remove('hidden');
  elements.detailContent.classList.add('hidden');
  elements.emailDetailColumn.classList.remove('active-mobile');
  document.querySelectorAll('.email-card').forEach(c => c.classList.remove('selected'));
}

// --- MOBILE SIDEBAR DRAWER ---
function openMobileSidebar() {
  if (elements.appSidebar) elements.appSidebar.classList.add('open');
  if (elements.sidebarBackdrop) elements.sidebarBackdrop.classList.add('active');
}

function closeMobileSidebar() {
  if (elements.appSidebar) elements.appSidebar.classList.remove('open');
  if (elements.sidebarBackdrop) elements.sidebarBackdrop.classList.remove('active');
}

// --- SYNC IMAP ---
async function handleSyncInbox() {
  elements.syncIcon.classList.add('spinning');
  elements.btnSyncInbox.disabled = true;

  try {
    const res = await apiRequest('/api/emails/sync', { method: 'POST' });
    showToast(t('sync_success', { count: res.fetched_count }), 'success');
    await loadEmails('inbox');
  } catch (err) {
    showToast(t('sync_failed') + err.message, 'error', 6000);
  } finally {
    elements.syncIcon.classList.remove('spinning');
    elements.btnSyncInbox.disabled = false;
  }
}

// --- COMPOSE & SEND EMAIL ---
function openCompose(to = '', subject = '', body = '') {
  closeMobileSidebar();
  elements.composeTo.value = to;
  elements.composeSubject.value = subject;
  elements.composeMessage.value = body;
  elements.composeModal.classList.add('active');
  if (!to) {
    elements.composeTo.focus();
  } else {
    elements.composeMessage.focus();
  }
}

function closeCompose() {
  elements.composeModal.classList.remove('active');
  elements.composeForm.reset();
}

async function handleSendEmail(e) {
  e.preventDefault();
  const recipient = elements.composeTo.value.trim();
  const subject = elements.composeSubject.value.trim();
  const message = elements.composeMessage.value.trim();

  // Anti-bulk protection: Enforce single recipient on client side
  if (recipient.includes(',') || recipient.includes(';') || recipient.includes(' ') || recipient.includes('\n')) {
    showToast(t('single_recipient_error'), 'error');
    return;
  }

  const sendBtn = document.getElementById('btn-compose-send');
  const spinner = sendBtn.querySelector('.btn-spinner');
  const btnText = sendBtn.querySelector('.btn-text');

  sendBtn.disabled = true;
  spinner.classList.remove('hidden');
  btnText.classList.add('hidden');

  try {
    await apiRequest('/api/emails/send', {
      method: 'POST',
      body: { recipient, subject, message }
    });
    showToast(t('email_sent_success'), 'success');
    closeCompose();
    await fetchStats();
    if (state.currentFolder === 'sent') {
      await loadEmails('sent');
    }
  } catch (err) {
    showToast(t('email_send_failed') + err.message, 'error', 6000);
  } finally {
    sendBtn.disabled = false;
    spinner.classList.add('hidden');
    btnText.classList.remove('hidden');
  }
}

// --- SETTINGS ---
async function loadEmailConfig() {
  try {
    const config = await apiRequest('/api/config');
    state.config = config;
    if (config.is_configured) {
      elements.cfgEmail.value = config.email_address || '';
      elements.cfgSenderName.value = config.sender_name || '';
      elements.cfgImapHost.value = config.imap_host || 'imap.gmail.com';
      elements.cfgImapPort.value = config.imap_port || 993;
      elements.cfgSmtpHost.value = config.smtp_host || 'smtp.gmail.com';
      elements.cfgSmtpPort.value = config.smtp_port || 465;

      if (config.has_password) {
        elements.passwordStatusHint.innerText = t('hint_app_password_saved');
      } else {
        elements.passwordStatusHint.innerText = t('hint_app_password_default');
      }
      updateConnectionStatus(true, config.email_address);
    }
  } catch (err) {
    console.error('Failed to load email config:', err);
  }
}

async function handleSaveSettings(e) {
  e.preventDefault();
  const btn = document.getElementById('btn-save-settings');
  const spinner = btn.querySelector('.btn-spinner');
  const btnText = btn.querySelector('.btn-text');

  btn.disabled = true;
  spinner.classList.remove('hidden');
  btnText.classList.add('hidden');

  const payload = {
    email_address: elements.cfgEmail.value.trim(),
    password: elements.cfgPassword.value.trim() || null,
    sender_name: elements.cfgSenderName.value.trim(),
    imap_host: elements.cfgImapHost.value.trim(),
    imap_port: parseInt(elements.cfgImapPort.value) || 993,
    imap_use_ssl: true,
    smtp_host: elements.cfgSmtpHost.value.trim(),
    smtp_port: parseInt(elements.cfgSmtpPort.value) || 465,
    smtp_use_ssl: true
  };

  try {
    await apiRequest('/api/config', {
      method: 'POST',
      body: payload
    });
    showToast(t('settings_saved'), 'success');
    elements.cfgPassword.value = '';
    await loadEmailConfig();
  } catch (err) {
    showToast(t('settings_save_failed') + err.message, 'error');
  } finally {
    btn.disabled = false;
    spinner.classList.add('hidden');
    btnText.classList.remove('hidden');
  }
}

async function handleTestConnection() {
  const btn = elements.btnTestConnection;
  const spinner = btn.querySelector('.btn-spinner');
  const btnText = btn.querySelector('.btn-text');

  btn.disabled = true;
  spinner.classList.remove('hidden');
  btnText.classList.add('hidden');

  elements.testResultBox.className = 'test-result-box hidden';

  const payload = {
    email_address: elements.cfgEmail.value.trim() || null,
    password: elements.cfgPassword.value.trim() || null,
    imap_host: elements.cfgImapHost.value.trim(),
    imap_port: parseInt(elements.cfgImapPort.value) || 993,
    imap_use_ssl: true,
    smtp_host: elements.cfgSmtpHost.value.trim(),
    smtp_port: parseInt(elements.cfgSmtpPort.value) || 465,
    smtp_use_ssl: true
  };

  try {
    const res = await apiRequest('/api/config/test', {
      method: 'POST',
      body: payload
    });

    elements.testResultBox.classList.remove('hidden');
    if (res.success) {
      elements.testResultBox.className = 'test-result-box success';
      elements.testResultBox.innerHTML = `
        <strong>${t('conn_success_title')}</strong><br>
        ✓ IMAP: ${escapeHtml(res.imap_message)}<br>
        ✓ SMTP: ${escapeHtml(res.smtp_message)}
      `;
      showToast(t('test_both_success'), 'success');
    } else {
      elements.testResultBox.className = 'test-result-box error';
      elements.testResultBox.innerHTML = `
        <strong>${t('conn_fail_title')}</strong><br>
        • IMAP: ${escapeHtml(res.imap_message)}<br>
        • SMTP: ${escapeHtml(res.smtp_message)}
      `;
    }
  } catch (err) {
    elements.testResultBox.classList.remove('hidden');
    elements.testResultBox.className = 'test-result-box error';
    elements.testResultBox.innerHTML = `<strong>Error:</strong> ${escapeHtml(err.message)}`;
  } finally {
    btn.disabled = false;
    spinner.classList.add('hidden');
    btnText.classList.remove('hidden');
  }
}

// --- PURGE FACILITY ---
function promptPurge(target) {
  state.pendingPurgeTarget = target;
  let title = t('purge_title');
  let msg = '...';

  if (target === 'sent') {
    title = t('purge_sent_title');
    msg = t('confirm_purge_sent', { count: state.stats.sent_count });
  } else if (target === 'received') {
    title = t('purge_received_title');
    msg = t('confirm_purge_recv', { count: state.stats.received_count });
  } else if (target === 'all') {
    title = t('purge_all_title');
    msg = t('confirm_purge_all', { sent: state.stats.sent_count, recv: state.stats.received_count });
  }

  elements.confirmModalTitle.innerText = title;
  elements.confirmModalMessage.innerText = msg;
  elements.confirmModal.classList.add('active');
}

async function executePurge() {
  const target = state.pendingPurgeTarget;
  if (!target) return;

  try {
    const res = await apiRequest('/api/emails/purge', {
      method: 'POST',
      body: { target }
    });
    showToast(t('purge_success', { sent: res.purged_sent, recv: res.purged_received }), 'success');
    elements.confirmModal.classList.remove('active');
    await fetchStats();
    await loadEmails(state.currentFolder);
  } catch (err) {
    showToast(t('purge_failed') + err.message, 'error');
  }
}

// --- NAVIGATION & VIEWS SWITCHER ---
function switchView(viewName) {
  closeMobileSidebar();
  clearDetailView();
  state.currentView = viewName;

  // Nav buttons active state
  [elements.navInbox, elements.navSent, elements.navPurge, elements.navSettings].forEach(btn => btn.classList.remove('active'));
  
  elements.viewMail.classList.add('hidden');
  elements.viewSettings.classList.add('hidden');
  elements.viewPurge.classList.add('hidden');

  if (viewName === 'inbox') {
    elements.navInbox.classList.add('active');
    elements.viewMail.classList.remove('hidden');
    state.currentFolder = 'inbox';
    elements.currentFolderTitle.innerText = t('folder_inbox');
    elements.folderMetaSub.innerText = t('folder_inbox_meta');
    elements.btnSyncInbox.classList.remove('hidden');
    loadEmails('inbox');
  } else if (viewName === 'sent') {
    elements.navSent.classList.add('active');
    elements.viewMail.classList.remove('hidden');
    state.currentFolder = 'sent';
    elements.currentFolderTitle.innerText = t('folder_sent');
    elements.folderMetaSub.innerText = t('folder_sent_meta');
    elements.btnSyncInbox.classList.add('hidden');
    loadEmails('sent');
  } else if (viewName === 'settings') {
    elements.navSettings.classList.add('active');
    elements.viewSettings.classList.remove('hidden');
    loadEmailConfig();
  } else if (viewName === 'purge') {
    elements.navPurge.classList.add('active');
    elements.viewPurge.classList.remove('hidden');
    fetchStats();
  }
}

// --- SETUP EVENT LISTENERS ---
function initEventListeners() {
  // Theme Toggle
  elements.btnThemeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('lazymail_theme', newTheme);
    
    const iconMoon = elements.btnThemeToggle.querySelector('.icon-moon');
    const iconSun = elements.btnThemeToggle.querySelector('.icon-sun');
    if (newTheme === 'light') {
      iconMoon.classList.add('hidden');
      iconSun.classList.remove('hidden');
    } else {
      iconMoon.classList.remove('hidden');
      iconSun.classList.add('hidden');
    }
  });

  // Restore saved theme
  const savedTheme = localStorage.getItem('lazymail_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  if (savedTheme === 'light') {
    elements.btnThemeToggle.querySelector('.icon-moon').classList.add('hidden');
    elements.btnThemeToggle.querySelector('.icon-sun').classList.remove('hidden');
  }

  // Language Switcher Buttons (Handles both navbar and auth modal switchers)
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const targetLang = e.currentTarget.getAttribute('data-lang');
      if (targetLang && targetLang !== state.currentLang) {
        applyLanguage(targetLang);
      }
    });
  });

  // Live Gmail Address Preview
  if (elements.setupUsername && elements.setupEmailPreview) {
    elements.setupUsername.addEventListener('input', (e) => {
      const val = e.target.value.trim().toLowerCase();
      if (!val) {
        elements.setupEmailPreview.innerText = 'yourname@gmail.com';
      } else if (val.includes('@')) {
        elements.setupEmailPreview.innerText = val;
      } else {
        elements.setupEmailPreview.innerText = `${val}@gmail.com`;
      }
    });
  }

  // Password Toggles in Auth Modals
  if (elements.btnToggleSetupPassword) {
    elements.btnToggleSetupPassword.addEventListener('click', () => {
      const isPass = elements.setupPassword.type === 'password';
      elements.setupPassword.type = isPass ? 'text' : 'password';
    });
  }

  if (elements.btnToggleLoginPassword) {
    elements.btnToggleLoginPassword.addEventListener('click', () => {
      const isPass = elements.loginPassword.type === 'password';
      elements.loginPassword.type = isPass ? 'text' : 'password';
    });
  }

  // Auth Forms
  elements.setupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = elements.setupUsername.value.trim();
    const p1 = elements.setupPassword.value.trim();
    const p2 = elements.setupPasswordConfirm.value.trim();

    if (p1 !== p2) {
      showToast(t('passcodes_dont_match'), 'error');
      return;
    }
    try {
      const res = await apiRequest('/api/auth/setup', {
        method: 'POST',
        body: { username, password: p1 }
      });
      showToast(t('account_created_toast', { email: res.email_address }), 'success', 5000);
      hideAuthModal();
      setLoggedInUser(res.username);
      updateConnectionStatus(true, res.email_address);
      await loadInitialData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  elements.loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = elements.loginUsername.value.trim();
    const password = elements.loginPassword.value;

    try {
      await apiRequest('/api/auth/login', {
        method: 'POST',
        body: { username, password }
      });
      showToast(t('welcome_back'), 'success');
      hideAuthModal();
      setLoggedInUser(username);
      await loadInitialData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  elements.btnLogout.addEventListener('click', async () => {
    try {
      await apiRequest('/api/auth/logout', { method: 'POST' });
      state.user = null;
      showToast(t('logged_out'), 'info');
      showAuthModal(false);
    } catch (err) {
      showToast(err.message, 'error');
    }
  });

  // Navigation
  elements.navInbox.addEventListener('click', () => switchView('inbox'));
  elements.navSent.addEventListener('click', () => switchView('sent'));
  elements.navPurge.addEventListener('click', () => switchView('purge'));
  elements.navSettings.addEventListener('click', () => switchView('settings'));

  // Sync Button
  elements.btnSyncInbox.addEventListener('click', handleSyncInbox);

  // Compose
  elements.btnComposeOpen.addEventListener('click', () => openCompose());
  elements.btnComposeClose.addEventListener('click', closeCompose);
  elements.btnComposeDiscard.addEventListener('click', closeCompose);
  elements.composeForm.addEventListener('submit', handleSendEmail);

  // Detail View Controls
  elements.btnViewRendered.addEventListener('click', () => {
    elements.btnViewRendered.classList.add('active');
    elements.btnViewPlain.classList.remove('active');
    elements.detailBodyHtmlWrapper.classList.remove('hidden');
    elements.detailBodyPlain.classList.add('hidden');
  });

  elements.btnViewPlain.addEventListener('click', () => {
    elements.btnViewPlain.classList.add('active');
    elements.btnViewRendered.classList.remove('active');
    elements.detailBodyPlain.classList.remove('hidden');
    elements.detailBodyHtmlWrapper.classList.add('hidden');
  });

  elements.btnCloseDetail.addEventListener('click', clearDetailView);
  if (elements.btnDetailBack) {
    elements.btnDetailBack.addEventListener('click', clearDetailView);
  }

  // Mobile Drawer Toggle
  if (elements.btnMobileSidebarToggle) {
    elements.btnMobileSidebarToggle.addEventListener('click', openMobileSidebar);
  }
  if (elements.btnSidebarClose) {
    elements.btnSidebarClose.addEventListener('click', closeMobileSidebar);
  }
  if (elements.sidebarBackdrop) {
    elements.sidebarBackdrop.addEventListener('click', closeMobileSidebar);
  }

  elements.btnReply.addEventListener('click', () => {
    if (!state.selectedEmailData) return;
    const { sender_email, subject, body_plain } = state.selectedEmailData;
    const replySubject = subject.startsWith('Re:') ? subject : `Re: ${subject}`;
    const quotedBody = `\n\n--- On ${state.selectedEmailData.received_at}, ${state.selectedEmailData.sender} wrote ---\n> ${body_plain ? body_plain.replace(/\n/g, '\n> ') : ''}`;
    openCompose(sender_email, replySubject, quotedBody);
  });

  // Search
  let searchDebounce = null;
  elements.globalSearchInput.addEventListener('input', (e) => {
    const val = e.target.value;
    if (val) {
      elements.btnSearchClear.classList.remove('hidden');
    } else {
      elements.btnSearchClear.classList.add('hidden');
    }

    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      loadEmails(state.currentFolder, val);
    }, 300);
  });

  elements.btnSearchClear.addEventListener('click', () => {
    elements.globalSearchInput.value = '';
    elements.btnSearchClear.classList.add('hidden');
    loadEmails(state.currentFolder, '');
  });

  // Settings
  elements.settingsForm.addEventListener('submit', handleSaveSettings);
  elements.btnTestConnection.addEventListener('click', handleTestConnection);
  elements.btnTogglePasswordView.addEventListener('click', () => {
    const isPassword = elements.cfgPassword.type === 'password';
    elements.cfgPassword.type = isPassword ? 'text' : 'password';
  });

  // Purge buttons
  elements.btnPurgeSent.addEventListener('click', () => promptPurge('sent'));
  elements.btnPurgeReceived.addEventListener('click', () => promptPurge('received'));
  elements.btnPurgeAll.addEventListener('click', () => promptPurge('all'));

  elements.btnConfirmCancel.addEventListener('click', () => {
    elements.confirmModal.classList.remove('active');
    state.pendingPurgeTarget = null;
  });
  elements.btnConfirmProceed.addEventListener('click', executePurge);
}

// --- BOOTSTRAP ---
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  applyLanguage(state.currentLang); // Default: Turkish ('tr') or saved user preference
  checkAuthStatus();
});
