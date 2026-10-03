/**
 * LazyMail — Internationalization (i18n) Dictionary
 * Supported Languages: 'tr' (Turkish - Default), 'en' (English)
 */

// LazyMail Translations Dictionary
// Attached to window / globalThis for universal browser and runtime availability
const globalScope = typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this);
globalScope.translations = {
  tr: {
    // App & Auth
    app_name: "LazyMail",
    app_tagline: "Güvenli, hızlı ve şifreli e-posta deneyimi",
    setup_title: "LazyMail Kurulumu",
    setup_subtitle: "Gmail kullanıcı adı ön ekinizi ve 16 haneli Uygulama Şifrenizi girin",
    setup_alert: "Gmail kullanıcı adı ön ekinizi (örn. <strong>harrypotter12345</strong>) ve 16 haneli Google Uygulama Şifrenizi girin. Bunlar girişinizi oluşturacak ve Gmail hesap detaylarınızı otomatik dolduracaktır!",
    label_username_prefix: "Gmail Kullanıcı Adı (Ön Ek)",
    placeholder_username_prefix: "örn. harrypotter12345",
    setup_email_preview_label: "Posta kutusu yapılandırması: ",
    label_app_passcode: "16 Haneli Google Uygulama Şifresi",
    placeholder_app_passcode: "örn. abcd efgh ijkl mnop",
    helper_app_passcode: "Google Hesabı > Güvenlik > 2 Adımlı Doğrulama > Uygulama şifreleri",
    label_confirm_passcode: "Uygulama Şifresini Onaylayın",
    placeholder_confirm_passcode: "Şifreyi tekrar girin",
    btn_create_account: "Hesap Oluştur ve Gmail'e Bağlan",

    // Login
    login_title: "Tekrar Hoş Geldiniz",
    login_subtitle: "Gmail kullanıcı adınız ve Uygulama Şifreniz ile giriş yapın",
    label_login_username: "Gmail Kullanıcı Adı",
    placeholder_login_username: "örn. harrypotter12345 veya tam e-posta",
    label_login_passcode: "Uygulama Şifresi",
    placeholder_login_passcode: "16 haneli şifre",
    btn_unlock_mailbox: "Posta Kutusunu Aç",

    // Top Navigation
    status_not_configured: "Yapılandırılmadı",
    status_connected_to: "Gmail'e Bağlandı: ",
    search_placeholder: "Gönderen, konu veya içeriğe göre e-postaları ara...",
    theme_tooltip: "Karanlık/Aydınlık Modu Değiştir",
    logout_tooltip: "Çıkış Yap",

    // Sidebar
    btn_compose: "Yeni E-posta",
    nav_inbox: "Gelen Kutusu (7 Gün)",
    nav_sent: "Gönderilen Mesajlar",
    nav_purge: "Veritabanını Temizle",
    nav_settings: "E-posta Ayarları",
    storage_title: "SQLite Depolama",
    storage_sent: "Gönderilen",
    storage_inbox: "Gelen Kutusu",

    // Mail Views
    folder_inbox: "Gelen Kutusu",
    folder_inbox_meta: "Son 7 gün (maks. 50 e-posta)",
    folder_sent: "Gönderilen Mesajlar",
    folder_sent_meta: "SQLite'ta depolanan (maks. 50)",
    btn_sync_imap: "IMAP Senkronize Et",
    empty_inbox_title: "Gelen kutusu boş",
    empty_inbox_desc: "Son 7 günün e-postalarını çekmek için \"IMAP Senkronize Et\" butonuna tıklayın.",
    empty_sent_title: "Gönderilen mesaj yok",
    empty_sent_desc: "Yazdığınız ve gönderdiğiniz mesajlar burada listelenir (maks. 50).",
    loading_messages: "Mesajlar yükleniyor...",

    // Mail Reader Detail
    select_email_title: "Okumak için bir e-posta seçin",
    select_email_desc: "Detayları, başlıkları ve tam içeriği görüntülemek için listeden bir mesaj seçin.",
    btn_reply: "Yanıtla",
    btn_back: "Geri",
    mobile_menu_label: "Menü",
    view_rendered: "Arındırılmış Görünüm",
    view_plain: "Düz Metin",
    to_me: "Bana",
    no_subject: "(Konusuz)",
    no_plain_text: "(Düz metin sürümü bulunamadı)",

    // Compose Modal
    compose_title: "Yeni Mesaj",
    label_to: "Kime",
    placeholder_to: "alici@ornek.com",
    helper_single_recipient: "Yalnızca tek alıcı (Toplu e-posta gönderimi devre dışıdır)",
    single_recipient_error: "Toplu e-posta devre dışıdır. Lütfen virgül veya noktalı virgül olmadan yalnızca tek bir geçerli e-posta adresi girin.",
    label_subject: "Konu",
    placeholder_subject: "E-posta konusu",
    placeholder_message: "Mesajınızı buraya yazın...",
    btn_discard: "Vazgeç",
    btn_send: "Mesajı Gönder",

    // Settings View
    settings_title: "Gmail IMAP / SMTP Yapılandırması",
    settings_desc: "Gmail bilgilerinizi güvenle yapılandırın. Uygulama Şifreleri SQLite içinde AES-256 (Fernet) ile şifrelenir.",
    banner_title: "Gmail Uygulama Şifresi Kurulumu:",
    banner_step1: "Google Hesabı güvenlik ayarlarınızda <strong>2 Adımlı Doğrulama</strong>yı açın.",
    banner_step2: "Doğrudan <a href=\"https://myaccount.google.com/apppasswords\" target=\"_blank\" rel=\"noopener\" style=\"color: #6366f1; text-decoration: underline;\">Google Uygulama Şifreleri</a> sayfasına gidin veya arama çubuğuna <strong>\"Uygulama şifreleri\"</strong> yazın.",
    banner_step3: "<em>\"LazyMail\"</em> adında yeni bir Uygulama Şifresi oluşturun ve 16 haneli kodu kopyalayın.",
    banner_step4: "16 haneli kodu aşağıdaki <strong>Gmail Uygulama Şifresi</strong> alanına yapıştırın.",
    label_gmail_address: "Gmail Adresi *",
    label_app_password: "Gmail Uygulama Şifresi *",
    placeholder_app_password: "16 haneli uygulama şifresi (değiştirmeyecekseniz boş bırakın)",
    hint_app_password_saved: "Uygulama Şifreniz güvenle saklanmaktadır. Güncellemeyecekseniz boş bırakın.",
    hint_app_password_default: "16 haneli Google Uygulama Şifrenizi girin.",
    label_sender_name: "Görünen Gönderici Adı (İsteğe bağlı)",
    label_imap_host: "IMAP Sunucu Adresi",
    label_imap_port: "IMAP Portu (SSL)",
    label_smtp_host: "SMTP Sunucu Adresi",
    label_smtp_port: "SMTP Portu (SSL)",
    btn_test_connection: "IMAP ve SMTP Bağlantısını Test Et",
    btn_save_settings: "Yapılandırmayı Kaydet",

    // Purge View
    purge_title: "Mesajları Veritabanından Temizle",
    purge_desc: "SQLite'tan saklanan gelen e-postaları, gönderilen e-postaları veya her ikisini temizleyin. Yapılandırma ve kullanıcı bilgileri korunur.",
    stat_cached_inbox: "Önbelleğe Alınan Gelen E-postalar",
    stat_stored_sent: "Depolanan Gönderilen E-postalar (Maks. 50)",
    purge_sent_title: "Gönderilen Mesajları Temizle",
    purge_sent_desc: "SQLite veritabanında depolanan tüm gönderilen e-postaları kalıcı olarak siler.",
    btn_purge_sent: "Gönderilenleri Temizle (Yalnızca)",
    purge_received_title: "Gelen Mesajları Temizle",
    purge_received_desc: "SQLite'ta depolanan 7 günlük gelen kutusu önbelleğini temizler. (Yeni mesajlar Gmail'den istendiğinde yeniden senkronize edilebilir).",
    btn_purge_received: "Gelenleri Temizle (Yalnızca)",
    purge_all_title: "Tüm Mesajları Temizle",
    purge_all_desc: "Tüm gönderilen ve gelen e-posta kayıtlarını siler ve disk alanını geri kazanmak için VACUUM çalıştırır.",
    btn_purge_all: "Tüm Mesajları Temizle",

    // Confirm Dialogs
    confirm_title: "İşlemi Onayla",
    confirm_purge_sent: "SQLite'ta depolanan tüm gönderilen e-postaları kalıcı olarak silmek istediğinizden emin misiniz? (Mevcut sayı: {count})",
    confirm_purge_recv: "SQLite'taki tüm önbelleğe alınan gelen kutusu e-postalarını silmek istediğinizden emin misiniz? (Mevcut sayı: {count}). Gmail'den istediğiniz zaman tekrar senkronize edebilirsiniz.",
    confirm_purge_all: "SQLite'taki {sent} gönderilen ve {recv} gelen e-postanın TÜMÜNÜ kalıcı olarak temizlemek istiyor musunuz?",
    btn_cancel: "Vazgeç",
    btn_confirm_purge: "Onayla ve Temizle",

    // Additional UI & Tooltips
    unknown_sender: "Bilinmeyen Gönderici",
    empty_content: "(Boş)",
    load_emails_failed: "E-postalar yüklenemedi",
    connection_status_title: "Gmail bağlantı durumu",
    search_clear_tooltip: "Aramayı temizle",
    sync_tooltip: "Gmail IMAP'ten e-postaları senkronize et",
    close_tooltip: "Kapat",
    toggle_password_tooltip: "Göster/Gizle",
    placeholder_sender_name: "örn. Ahmet Yılmaz",
    detail_to_prefix: "Kime: ",
    conn_success_title: "Bağlantı Başarılı!",
    conn_fail_title: "Bağlantı Başarısız:",

    // Toasts & Messages
    passcodes_dont_match: "Uygulama şifreleri eşleşmiyor.",
    account_created_toast: "Hesap oluşturuldu ve Gmail otomatik yapılandırıldı: {email}!",
    welcome_back: "Tekrar hoş geldiniz!",
    logged_out: "Çıkış yapıldı.",
    sync_success: "Son 7 günden {count} e-posta senkronize edildi!",
    sync_failed: "IMAP Senkronizasyonu başarısız: ",
    email_sent_success: "E-posta başarıyla gönderildi!",
    email_send_failed: "E-posta gönderilemedi: ",
    settings_saved: "Ayarlar başarıyla kaydedildi!",
    settings_save_failed: "Ayarlar kaydedilemedi: ",
    test_both_success: "Hem IMAP hem de SMTP bağlantısı doğrulandı!",
    purge_success: "Temizleme tamamlandı! {sent} gönderilen ve {recv} gelen kayıt silindi.",
    purge_failed: "Temizleme başarısız: "
  },

  en: {
    // App & Auth
    app_name: "LazyMail",
    app_tagline: "Secure, fast, and encrypted email experience",
    setup_title: "LazyMail Setup",
    setup_subtitle: "Enter your Gmail username prefix & App Passcode",
    setup_alert: "Enter your Gmail username prefix (e.g. <strong>harrypotter12345</strong>) and 16-char Google App Passcode. These will create your login and auto-populate your Gmail account details!",
    label_username_prefix: "Gmail Username (Prefix)",
    placeholder_username_prefix: "e.g. harrypotter12345",
    setup_email_preview_label: "Configures mailbox as: ",
    label_app_passcode: "16-Character Google App Passcode",
    placeholder_app_passcode: "e.g. abcd efgh ijkl mnop",
    helper_app_passcode: "From Google Account > Security > 2-Step Verification > App passwords",
    label_confirm_passcode: "Confirm App Passcode",
    placeholder_confirm_passcode: "Re-enter passcode",
    btn_create_account: "Create Account & Connect Gmail",

    // Login
    login_title: "Welcome Back",
    login_subtitle: "Sign in with your Gmail username & App Passcode",
    label_login_username: "Gmail Username",
    placeholder_login_username: "e.g. harrypotter12345 or full email",
    label_login_passcode: "App Passcode",
    placeholder_login_passcode: "16-character passcode",
    btn_unlock_mailbox: "Unlock Mailbox",

    // Top Navigation
    status_not_configured: "Not Configured",
    status_connected_to: "Connected to Gmail: ",
    search_placeholder: "Search emails by sender, subject or snippet...",
    theme_tooltip: "Toggle Dark/Light Mode",
    logout_tooltip: "Logout",

    // Sidebar
    btn_compose: "Compose",
    nav_inbox: "Inbox (7 Days)",
    nav_sent: "Sent Messages",
    nav_purge: "Purge Database",
    nav_settings: "Email Settings",
    storage_title: "SQLite Storage",
    storage_sent: "Sent",
    storage_inbox: "Inbox",

    // Mail Views
    folder_inbox: "Inbox",
    folder_inbox_meta: "Last 7 days (max 50 emails)",
    folder_sent: "Sent Messages",
    folder_sent_meta: "Stored in SQLite (max 50)",
    btn_sync_imap: "Sync IMAP",
    empty_inbox_title: "Inbox is empty",
    empty_inbox_desc: "Click \"Sync IMAP\" to fetch emails from the last 7 days.",
    empty_sent_title: "No sent messages",
    empty_sent_desc: "Messages you compose and send will appear here (max 50).",
    loading_messages: "Loading messages...",

    // Mail Reader Detail
    select_email_title: "Select an email to read",
    select_email_desc: "Choose any message from the list to preview details, headers, and full body content.",
    btn_reply: "Reply",
    btn_back: "Back",
    mobile_menu_label: "Menu",
    view_rendered: "Sanitized View",
    view_plain: "Plain Text",
    to_me: "Me",
    no_subject: "(No Subject)",
    no_plain_text: "(No plain text version available)",

    // Compose Modal
    compose_title: "New Message",
    label_to: "To",
    placeholder_to: "recipient@example.com",
    helper_single_recipient: "Single recipient only (Bulk sending is disabled)",
    single_recipient_error: "Bulk emailing is disabled. Please enter a single valid email address without commas or semicolons.",
    label_subject: "Subject",
    placeholder_subject: "Email subject",
    placeholder_message: "Write your message here...",
    btn_discard: "Discard",
    btn_send: "Send Message",

    // Settings View
    settings_title: "Gmail IMAP / SMTP Configuration",
    settings_desc: "Configure your Gmail credentials securely. App Passwords are encrypted in SQLite using AES-256 (Fernet).",
    banner_title: "Setting up Gmail App Password:",
    banner_step1: "Enable <strong>2-Step Verification</strong> in your Google Account security settings.",
    banner_step2: "Visit <a href=\"https://myaccount.google.com/apppasswords\" target=\"_blank\" rel=\"noopener\" style=\"color: #6366f1; text-decoration: underline;\">Google App Passwords</a> directly or search for <strong>\"App passwords\"</strong> in Security.",
    banner_step3: "Create a new App Password named <em>\"LazyMail\"</em> and copy the generated 16-character code.",
    banner_step4: "Paste the 16-character code into the <strong>Gmail App Password</strong> field below.",
    label_gmail_address: "Gmail Address *",
    label_app_password: "Gmail App Password *",
    placeholder_app_password: "16-character app password (leave blank to keep current)",
    hint_app_password_saved: "An App Password is saved securely. Leave blank unless updating.",
    hint_app_password_default: "Enter your 16-character Google App Password.",
    label_sender_name: "Display Sender Name (Optional)",
    label_imap_host: "IMAP Server Host",
    label_imap_port: "IMAP Port (SSL)",
    label_smtp_host: "SMTP Server Host",
    label_smtp_port: "SMTP Port (SSL)",
    btn_test_connection: "Test IMAP & SMTP Connection",
    btn_save_settings: "Save Configuration",

    // Purge View
    purge_title: "Purge Messages from Database",
    purge_desc: "Purge stored received messages, sent messages, or both from SQLite. Configuration and user credentials are safe.",
    stat_cached_inbox: "Received Emails Cached",
    stat_stored_sent: "Sent Emails Stored (Max 50)",
    purge_sent_title: "Purge Sent Messages",
    purge_sent_desc: "Permanently delete all sent emails stored in the SQLite database.",
    btn_purge_sent: "Purge Sent (Only)",
    purge_received_title: "Purge Received Messages",
    purge_received_desc: "Clear the 7-day inbox cache stored in SQLite. (New messages can be re-synced anytime from Gmail).",
    btn_purge_received: "Purge Received (Only)",
    purge_all_title: "Purge All Messages",
    purge_all_desc: "Erase all sent and received email records and run VACUUM to reclaim disk space.",
    btn_purge_all: "Purge All Messages",

    // Confirm Dialogs
    confirm_title: "Confirm Action",
    confirm_purge_sent: "Are you sure you want to permanently delete all sent emails stored in SQLite? (Current count: {count})",
    confirm_purge_recv: "Are you sure you want to delete all cached inbox emails in SQLite? (Current count: {count}). You can re-sync from Gmail anytime.",
    confirm_purge_all: "Permanently purge ALL {sent} sent emails and {recv} received emails from SQLite?",
    btn_cancel: "Cancel",
    btn_confirm_purge: "Confirm & Purge",

    // Additional UI & Tooltips
    unknown_sender: "Unknown Sender",
    empty_content: "(Empty)",
    load_emails_failed: "Failed to load emails",
    connection_status_title: "Gmail connection status",
    search_clear_tooltip: "Clear search",
    sync_tooltip: "Sync emails from Gmail IMAP",
    close_tooltip: "Close",
    toggle_password_tooltip: "Show/Hide",
    placeholder_sender_name: "e.g. Harry Potter",
    detail_to_prefix: "To: ",
    conn_success_title: "Connection Succeeded!",
    conn_fail_title: "Connection Failed:",

    // Toasts & Messages
    passcodes_dont_match: "App passcodes do not match.",
    account_created_toast: "Account created & Gmail auto-configured for {email}!",
    welcome_back: "Welcome back!",
    logged_out: "Logged out.",
    sync_success: "Synced {count} email(s) from the last 7 days!",
    sync_failed: "IMAP Sync failed: ",
    email_sent_success: "Email sent successfully!",
    email_send_failed: "Failed to send email: ",
    settings_saved: "Settings saved securely!",
    settings_save_failed: "Failed to save settings: ",
    test_both_success: "Both IMAP and SMTP connections verified!",
    purge_success: "Purge complete! Deleted {sent} sent and {recv} received records.",
    purge_failed: "Purge failed: "
  }
};

var translations = globalScope.translations;
if (typeof module !== 'undefined' && module.exports) {
  module.exports = globalScope.translations;
}
