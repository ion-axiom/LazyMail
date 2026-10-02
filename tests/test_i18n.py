"""
Verification of Internationalization (i18n) for LazyMail:
Checks that:
1. Both Turkish ('tr') and English ('en') translation dictionaries exist.
2. All keys in Turkish exist in English and vice-versa.
3. Every data-i18n, data-i18n-html, data-i18n-placeholder, and data-i18n-title
   attribute used in templates/index.html exists in both languages.
4. Default language is Turkish ('tr') in index.html and app.js.
5. Language switcher buttons exist for both 'tr' and 'en'.
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def test_i18n_default_language():
    index_html = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    app_js = (BASE_DIR / "static" / "js" / "app.js").read_text(encoding="utf-8")
    
    # 1. HTML root tag specifies lang="tr"
    assert '<html lang="tr"' in index_html
    
    # 2. app.js state defaults to 'tr'
    assert "currentLang: localStorage.getItem('lazymail_lang') || 'tr'" in app_js
    
    # 3. Default language button is active for 'tr'
    assert 'class="lang-btn active" data-lang="tr"' in index_html
    assert 'data-lang="en"' in index_html

def test_i18n_translation_keys_parity():
    trans_file = (BASE_DIR / "static" / "js" / "translations.js").read_text(encoding="utf-8")
    
    # Parse tr and en blocks
    tr_match = re.search(r'tr:\s*\{(.*?)\n\s*\},', trans_file, re.DOTALL)
    en_match = re.search(r'en:\s*\{(.*?)\n\s*\}\n\};', trans_file, re.DOTALL)
    
    assert tr_match is not None, "Could not find tr dictionary"
    assert en_match is not None, "Could not find en dictionary"
    
    tr_text = tr_match.group(1)
    en_text = en_match.group(1)
    
    tr_keys = set(re.findall(r'^\s*([a-zA-Z0-9_]+)\s*:', tr_text, re.MULTILINE))
    en_keys = set(re.findall(r'^\s*([a-zA-Z0-9_]+)\s*:', en_text, re.MULTILINE))
    
    diff_tr_en = tr_keys - en_keys
    diff_en_tr = en_keys - tr_keys
    
    assert not diff_tr_en, f"Keys in 'tr' missing from 'en': {diff_tr_en}"
    assert not diff_en_tr, f"Keys in 'en' missing from 'tr': {diff_en_tr}"
    assert len(tr_keys) >= 60, f"Expected at least 60 translated strings, found {len(tr_keys)}"

def test_index_html_keys_exist_in_translations():
    index_html = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    trans_file = (BASE_DIR / "static" / "js" / "translations.js").read_text(encoding="utf-8")
    
    tr_match = re.search(r'tr:\s*\{(.*?)\n\s*\},', trans_file, re.DOTALL)
    tr_keys = set(re.findall(r'^\s*([a-zA-Z0-9_]+)\s*:', tr_match.group(1), re.MULTILINE))
    
    # Extract all data-i18n* keys from index.html
    i18n_keys = set(re.findall(r'data-i18n="([^"]+)"', index_html))
    i18n_html_keys = set(re.findall(r'data-i18n-html="([^"]+)"', index_html))
    i18n_placeholder_keys = set(re.findall(r'data-i18n-placeholder="([^"]+)"', index_html))
    i18n_title_keys = set(re.findall(r'data-i18n-title="([^"]+)"', index_html))
    
    all_html_keys = i18n_keys | i18n_html_keys | i18n_placeholder_keys | i18n_title_keys
    
    missing_in_translations = all_html_keys - tr_keys
    assert not missing_in_translations, f"HTML references untranslated keys: {missing_in_translations}"

def test_language_switchers_present_in_both_views():
    index_html = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    
    # Check that language switcher pill exists in the top navbar
    assert 'id="nav-lang-switcher"' in index_html
    # Check that language switcher pill exists in the auth/setup modal
    assert 'class="auth-lang-row"' in index_html
    # Total of 2 switchers with 'tr' and 'en' buttons
    tr_btns = re.findall(r'data-lang="tr"', index_html)
    en_btns = re.findall(r'data-lang="en"', index_html)
    assert len(tr_btns) >= 2, "Expected TR button in both modal and navbar"
    assert len(en_btns) >= 2, "Expected EN button in both modal and navbar"

def test_mobile_responsive_elements_present():
    index_html = (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")
    app_css = (BASE_DIR / "static" / "css" / "app.css").read_text(encoding="utf-8")
    app_js = (BASE_DIR / "static" / "js" / "app.js").read_text(encoding="utf-8")

    # 1. Viewport tag configured with viewport-fit=cover
    assert 'name="viewport"' in index_html
    assert 'viewport-fit=cover' in index_html

    # 2. Mobile hamburger menu button present
    assert 'id="btn-mobile-sidebar-toggle"' in index_html

    # 3. Mobile sidebar drawer & backdrop present
    assert 'id="sidebar-backdrop"' in index_html
    assert 'id="btn-sidebar-close"' in index_html

    # 4. Mobile reader back button present
    assert 'id="btn-detail-back"' in index_html

    # 5. CSS breakpoints exist for tablet (900px), smartphone (768px), and small phone (480px)
    assert '@media (max-width: 900px)' in app_css
    assert '@media (max-width: 768px)' in app_css
    assert '@media (max-width: 480px)' in app_css

    # 6. iOS input zoom prevention rule (16px) exists
    assert 'font-size: 16px !important;' in app_css

    # 7. JS handles mobile drawer and mobile detail transitions
    assert 'openMobileSidebar' in app_js
    assert 'active-mobile' in app_js

