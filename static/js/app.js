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
const elements = {};

const ELEMENT_ID_MAP = {
  // Auth
  authModal: 'auth-modal',
  authTitle: 'auth-title',
  authSubtitle: 'auth-subtitle',
  setupForm: 'setup-form',
  loginForm: 'login-form',
  setupUsername: 'setup-username',
  setupEmailPreview: 'setup-email-preview',
  setupPassword: 'setup-password',
  setupPasswordConfirm: 'setup-password-confirm',
  btnToggleSetupPassword: 'btn-toggle-setup-password',
  loginUsername: 'login-username',
  loginPassword: 'login-password',
  btnToggleLoginPassword: 'btn-toggle-login-password',
  btnLogout: 'btn-logout',
  currentUsernameDisplay: 'current-username-display',
  userAvatarInitials: 'user-avatar-initials',

  // Mobile Navigation
  btnMobileSidebarToggle: 'btn-mobile-sidebar-toggle',
  btnSidebarClose: 'btn-sidebar-close',
  sidebarBackdrop: 'sidebar-backdrop',
  appSidebar: 'app-sidebar',
  btnDetailBack: 'btn-detail-back',

  // Navigation & Badges
  navInbox: 'nav-tab-inbox',
  navSent: 'nav-tab-sent',
  navPurge: 'nav-tab-purge',
  navSettings: 'nav-tab-settings',
  badgeInbox: 'badge-inbox-count',
  badgeSent: 'badge-sent-count',
  connectionPill: 'connection-pill',
  connectionStatusText: 'connection-status-text',
  storageSentStat: 'storage-sent-stat',
  storageInboxStat: 'storage-inbox-stat',
  storagePercentage: 'storage-percentage',
  storageProgressFill: 'storage-progress-fill',

  // Views
  viewMail: 'view-mail',
  viewSettings: 'view-settings',
  viewPurge: 'view-purge',
  currentFolderTitle: 'current-folder-title',
  folderMetaSub: 'folder-meta-sub',

  // List & Detail
  emailItemsContainer: 'email-items-container',
  emailDetailColumn: 'email-detail-column',
  detailEmptyPlaceholder: 'detail-empty-placeholder',
  detailContent: 'detail-content',
  detailSubject: 'detail-subject',
  detailSender: 'detail-sender',
  detailSenderEmail: 'detail-sender-email',
  detailRecipient: 'detail-recipient',
  detailDate: 'detail-date',
  detailAvatar: 'detail-avatar',
  detailBodyIframe: 'detail-body-iframe',
  detailBodyPlain: 'detail-body-plain',
  detailBodyHtmlWrapper: 'detail-body-html-wrapper',
  btnViewRendered: 'btn-view-rendered',
  btnViewPlain: 'btn-view-plain',
  btnCloseDetail: 'btn-close-detail',
  btnReply: 'btn-reply',

  // Actions & Search
  btnSyncInbox: 'btn-sync-inbox',
  syncIcon: 'sync-icon',
  globalSearchInput: 'global-search-input',
  btnSearchClear: 'btn-search-clear',
  btnThemeToggle: 'btn-theme-toggle',

  // Compose Modal
  composeModal: 'compose-modal',
  btnComposeOpen: 'btn-compose-open',
  btnComposeClose: 'btn-compose-close',
  btnComposeDiscard: 'btn-compose-discard',
  composeForm: 'compose-form',
  composeTo: 'compose-to',
  composeSubject: 'compose-subject',
  composeMessage: 'compose-message',

  // Settings
  settingsForm: 'settings-form',
  cfgEmail: 'cfg-email',
  cfgPassword: 'cfg-password',
  cfgSenderName: 'cfg-sender-name',
  cfgImapHost: 'cfg-imap-host',
  cfgImapPort: 'cfg-imap-port',
  cfgSmtpHost: 'cfg-smtp-host',
  cfgSmtpPort: 'cfg-smtp-port',
  btnTestConnection: 'btn-test-connection',
  testResultBox: 'test-connection-result',
  btnTogglePasswordView: 'btn-toggle-password-view',
  passwordStatusHint: 'password-status-hint',

  // Purge
  purgeCountInbox: 'purge-count-inbox',
  purgeCountSent: 'purge-count-sent',
  btnPurgeSent: 'btn-purge-sent',
  btnPurgeReceived: 'btn-purge-received',
  btnPurgeAll: 'btn-purge-all',

  // Confirm Modal
  confirmModal: 'confirm-modal',
  confirmModalTitle: 'confirm-modal-title',
  confirmModalMessage: 'confirm-modal-message',
  btnConfirmCancel: 'btn-confirm-cancel',
  btnConfirmProceed: 'btn-confirm-proceed',

  // Toast
  toastContainer: 'toast-container'
};

function initElements() {
  for (const [key, id] of Object.entries(ELEMENT_ID_MAP)) {
    elements[key] = document.getElementById(id);
  }
}
initElements();

function on(el, event, handler) {
  if (el && typeof el.addEventListener === 'function') {
    el.addEventListener(event, handler);
  }
}

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
    // Handle error parameters passed from Google OAuth callback redirects
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('error')) {
      const errCode = urlParams.get('error');
      let msg = 'Google Giriş Hatası: ' + errCode;
      if (errCode === 'oauth_not_configured') {
        msg = 'Google OAuth istemci bilgileri henüz girilmedi. Lütfen Client ID ve Secret girin.';
        setTimeout(() => openOAuthModal(), 400);
      } else if (errCode === 'access_denied') {
        msg = 'Google ile giriş işlemi kullanıcı tarafından iptal edildi.';
      }
      showToast(msg, 'error', 6000);
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    const status = await apiRequest('/api/auth/status');
    state.authStatus = status;

    if (status.setup_required) {
      showAuthModal(true);
    } else if (!status.logged_in) {
      showAuthModal(false);
    } else {
      hideAuthModal();
      setLoggedInUser(status.display_name || status.username, status.avatar_url);
      updateConnectionStatus(status.has_email_config, status.configured_email);
      await loadInitialData();
    }
    updateOAuthSettingsUI(status);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function updateOAuthSettingsUI(status) {
  const googleCard = document.getElementById('google-connected-card');
  const appPwBanner = document.getElementById('settings-app-password-banner');
  const oauthAvatar = document.getElementById('oauth-user-avatar');
  const oauthName = document.getElementById('oauth-user-name');
  const oauthEmail = document.getElementById('oauth-user-email');

  if (status && status.is_google_authenticated) {
    if (googleCard) googleCard.classList.remove('hidden');
    if (appPwBanner) appPwBanner.classList.add('hidden');
    if (oauthName) oauthName.innerText = status.display_name || status.username || 'Google User';
    if (oauthEmail) oauthEmail.innerText = status.configured_email || '';
    if (oauthAvatar) {
      if (status.avatar_url) {
        oauthAvatar.src = status.avatar_url;
        oauthAvatar.style.display = 'block';
      } else {
        oauthAvatar.style.display = 'none';
      }
    }
    if (elements.cfgPassword) {
      elements.cfgPassword.placeholder = '(Google OAuth 2.0 Aktif / Şifre Gerekmez)';
      elements.cfgPassword.disabled = true;
    }
  } else {
    if (googleCard) googleCard.classList.add('hidden');
    if (appPwBanner) appPwBanner.classList.remove('hidden');
    if (elements.cfgPassword) {
      elements.cfgPassword.placeholder = '•••• •••• •••• ••••';
      elements.cfgPassword.disabled = false;
    }
  }
}

function openOAuthModal() {
  const modal = document.getElementById('modal-oauth-config');
  if (modal) {
    modal.classList.add('active');
    loadOAuthClientConfig();
  }
}

function closeOAuthModal() {
  const modal = document.getElementById('modal-oauth-config');
  if (modal) {
    modal.classList.remove('active');
  }
}

async function loadOAuthClientConfig() {
  try {
    const cfg = await apiRequest('/api/auth/google/config');
    const clientIdInput = document.getElementById('oauth-client-id');
    if (clientIdInput && cfg.client_id) {
      clientIdInput.value = cfg.client_id;
    }
  } catch (err) {
    console.error('Failed to load OAuth config:', err);
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

function setLoggedInUser(username, avatarUrl) {
  state.user = username;
  elements.currentUsernameDisplay.innerText = username || 'Admin';
  if (avatarUrl) {
    elements.userAvatarInitials.innerHTML = `<img src="${avatarUrl}" style="width: 100%; height: 100%; border-radius: 50%; object-fit: cover;">`;
  } else {
    elements.userAvatarInitials.innerText = (username || 'A').charAt(0).toUpperCase();
  }
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
  const toEl = elements.composeTo || document.getElementById('compose-to');
  const subjEl = elements.composeSubject || document.getElementById('compose-subject');
  const msgEl = elements.composeMessage || document.getElementById('compose-message');

  const recipient = toEl ? toEl.value.trim() : '';
  const subject = subjEl ? subjEl.value.trim() : '';
  const message = msgEl ? msgEl.value.trim() : '';

  if (!recipient) {
    showToast(t('recipient_required') || 'Alıcı adresi gereklidir.', 'error');
    if (toEl) toEl.focus();
    return;
  }

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
  if (savedTheme === 'light' && elements.btnThemeToggle) {
    const moon = elements.btnThemeToggle.querySelector('.icon-moon');
    const sun = elements.btnThemeToggle.querySelector('.icon-sun');
    if (moon) moon.classList.add('hidden');
    if (sun) sun.classList.remove('hidden');
  }

  // Language Switcher Buttons (Handles both navbar and auth modal switchers)
  document.querySelectorAll('.lang-btn').forEach(btn => {
    on(btn, 'click', (e) => {
      const targetLang = e.currentTarget.getAttribute('data-lang');
      if (targetLang && targetLang !== state.currentLang) {
        applyLanguage(targetLang);
      }
    });
  });

  // Live Gmail Address Preview
  if (elements.setupUsername && elements.setupEmailPreview) {
    on(elements.setupUsername, 'input', (e) => {
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
    on(elements.btnToggleSetupPassword, 'click', () => {
      const isPass = elements.setupPassword.type === 'password';
      elements.setupPassword.type = isPass ? 'text' : 'password';
    });
  }

  if (elements.btnToggleLoginPassword) {
    on(elements.btnToggleLoginPassword, 'click', () => {
      const isPass = elements.loginPassword.type === 'password';
      elements.loginPassword.type = isPass ? 'text' : 'password';
    });
  }

  // Auth Forms
  on(elements.setupForm, 'submit', async (e) => {
    e.preventDefault();
    const username = elements.setupUsername ? elements.setupUsername.value.trim() : '';
    const p1 = elements.setupPassword ? elements.setupPassword.value.trim() : '';
    const p2 = elements.setupPasswordConfirm ? elements.setupPasswordConfirm.value.trim() : '';

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

  on(elements.loginForm, 'submit', async (e) => {
    e.preventDefault();
    const username = elements.loginUsername ? elements.loginUsername.value.trim() : '';
    const password = elements.loginPassword ? elements.loginPassword.value : '';

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

  on(elements.btnLogout, 'click', async () => {
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
  on(elements.navInbox, 'click', () => switchView('inbox'));
  on(elements.navSent, 'click', () => switchView('sent'));
  on(elements.navPurge, 'click', () => switchView('purge'));
  on(elements.navSettings, 'click', () => switchView('settings'));

  // Sync Button
  on(elements.btnSyncInbox, 'click', handleSyncInbox);

  // Compose
  on(elements.btnComposeOpen, 'click', () => openCompose());
  on(elements.btnComposeClose, 'click', closeCompose);
  on(elements.btnComposeDiscard, 'click', closeCompose);
  on(elements.composeForm, 'submit', handleSendEmail);

  // Detail View Controls
  on(elements.btnViewRendered, 'click', () => {
    if (elements.btnViewRendered) elements.btnViewRendered.classList.add('active');
    if (elements.btnViewPlain) elements.btnViewPlain.classList.remove('active');
    if (elements.detailBodyHtmlWrapper) elements.detailBodyHtmlWrapper.classList.remove('hidden');
    if (elements.detailBodyPlain) elements.detailBodyPlain.classList.add('hidden');
  });

  on(elements.btnViewPlain, 'click', () => {
    if (elements.btnViewPlain) elements.btnViewPlain.classList.add('active');
    if (elements.btnViewRendered) elements.btnViewRendered.classList.remove('active');
    if (elements.detailBodyPlain) elements.detailBodyPlain.classList.remove('hidden');
    if (elements.detailBodyHtmlWrapper) elements.detailBodyHtmlWrapper.classList.add('hidden');
  });

  on(elements.btnCloseDetail, 'click', clearDetailView);
  on(elements.btnDetailBack, 'click', clearDetailView);

  // Mobile Drawer Toggle
  on(elements.btnMobileSidebarToggle, 'click', openMobileSidebar);
  on(elements.btnSidebarClose, 'click', closeMobileSidebar);
  on(elements.sidebarBackdrop, 'click', closeMobileSidebar);

  on(elements.btnReply, 'click', () => {
    if (!state.selectedEmailData) return;
    const { sender_email, subject, body_plain } = state.selectedEmailData;
    const replySubject = subject.startsWith('Re:') ? subject : `Re: ${subject}`;
    const quotedBody = `\n\n--- On ${state.selectedEmailData.received_at}, ${state.selectedEmailData.sender} wrote ---\n> ${body_plain ? body_plain.replace(/\n/g, '\n> ') : ''}`;
    openCompose(sender_email, replySubject, quotedBody);
  });

  // Search
  let searchDebounce = null;
  if (elements.globalSearchInput) {
    on(elements.globalSearchInput, 'input', (e) => {
      const val = e.target.value;
      if (elements.btnSearchClear) {
        if (val) {
          elements.btnSearchClear.classList.remove('hidden');
        } else {
          elements.btnSearchClear.classList.add('hidden');
        }
      }

      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        loadEmails(state.currentFolder, val);
      }, 300);
    });
  }

  on(elements.btnSearchClear, 'click', () => {
    if (elements.globalSearchInput) elements.globalSearchInput.value = '';
    if (elements.btnSearchClear) elements.btnSearchClear.classList.add('hidden');
    loadEmails(state.currentFolder, '');
  });

  // Settings
  on(elements.settingsForm, 'submit', handleSaveSettings);
  on(elements.btnTestConnection, 'click', handleTestConnection);
  on(elements.btnTogglePasswordView, 'click', () => {
    if (elements.cfgPassword) {
      const isPassword = elements.cfgPassword.type === 'password';
      elements.cfgPassword.type = isPassword ? 'text' : 'password';
    }
  });

  // Purge buttons
  on(elements.btnPurgeSent, 'click', () => promptPurge('sent'));
  on(elements.btnPurgeReceived, 'click', () => promptPurge('received'));
  on(elements.btnPurgeAll, 'click', () => promptPurge('all'));

  on(elements.btnConfirmCancel, 'click', () => {
    if (elements.confirmModal) elements.confirmModal.classList.remove('active');
    state.pendingPurgeTarget = null;
  });
  on(elements.btnConfirmProceed, 'click', executePurge);

  // Google OAuth UI & Modal Events
  const btnOpenOAuth = document.getElementById('btn-open-oauth-modal');
  on(btnOpenOAuth, 'click', openOAuthModal);

  const btnCloseOAuth = document.getElementById('btn-close-oauth-modal');
  on(btnCloseOAuth, 'click', closeOAuthModal);

  const btnCancelOAuth = document.getElementById('btn-cancel-oauth-modal');
  on(btnCancelOAuth, 'click', closeOAuthModal);

  const formOAuth = document.getElementById('form-oauth-config');
  if (formOAuth) {
    on(formOAuth, 'submit', async (e) => {
      e.preventDefault();
      const clientIdEl = document.getElementById('oauth-client-id');
      const clientSecretEl = document.getElementById('oauth-client-secret');
      const clientId = clientIdEl ? clientIdEl.value.trim() : '';
      const clientSecret = clientSecretEl ? clientSecretEl.value.trim() : '';
      try {
        await apiRequest('/api/auth/google/config', {
          method: 'POST',
          body: JSON.stringify({ client_id: clientId, client_secret: clientSecret })
        });
        showToast(t('oauth_config_saved') || 'Google OAuth ayarları başarıyla kaydedildi!', 'success');
        closeOAuthModal();
        checkAuthStatus();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  const btnDisconnectGoogle = document.getElementById('btn-disconnect-google');
  if (btnDisconnectGoogle) {
    on(btnDisconnectGoogle, 'click', async () => {
      if (!confirm(t('confirm_disconnect_google') || 'Google hesabının bağlantısını kesmek istediğinize emin misiniz?')) return;
      try {
        await apiRequest('/api/auth/google/disconnect', { method: 'POST' });
        showToast(t('google_disconnected') || 'Google hesabı bağlantısı kesildi.', 'info');
        checkAuthStatus();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }
}

// --- BOOTSTRAP ---
document.addEventListener('DOMContentLoaded', () => {
  initElements();
  try {
    initEventListeners();
  } catch (err) {
    console.error('Error during initEventListeners:', err);
  }
  applyLanguage(state.currentLang); // Default: Turkish ('tr') or saved user preference
  checkAuthStatus();
});
