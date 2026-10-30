// 個人課表維護系統 - JavaScript

function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("schedule-theme", theme); } catch (e) {}
    document.querySelectorAll(".js-theme").forEach(function (button) {
        button.textContent = theme === "dark" ? "淺色模式" : "深色模式";
    });
}

document.addEventListener('DOMContentLoaded', function() {
    applyTheme(document.documentElement.getAttribute("data-theme") || "light");
    document.querySelectorAll(".js-theme").forEach(function (button) {
        button.addEventListener("click", function () {
            var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
            applyTheme(next);
        });
    });

    console.log('個人課表維護系統已載入');
    
    // 導覽選單切換（行動版）
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        // 切換選單
        function toggleNav(event) {
            event.preventDefault();
            event.stopPropagation();
            const isExpanded = navMenu.classList.toggle('active');
            navToggle.classList.toggle('active', isExpanded);
            navToggle.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
        }

        navToggle.addEventListener('click', toggleNav);
        
        // 點擊選單項目後關閉選單
        const navLinks = navMenu.querySelectorAll('a');
        navLinks.forEach(function(link) {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    navMenu.classList.remove('active');
                    navToggle.classList.remove('active');
                    navToggle.setAttribute('aria-expanded', 'false');
                }
            });
        });
        
        // Escape 鍵關閉選單
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && navMenu.classList.contains('active')) {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
                navToggle.setAttribute('aria-expanded', 'false');
                navToggle.focus();
            }
        });
        
        // 視窗大小改變時重置選單狀態
        window.addEventListener('resize', function() {
            if (window.innerWidth > 768) {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
                navToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }
    
    const account = document.getElementById("account-menu");
    const accountBtn = document.getElementById("account-btn");
    if (account && accountBtn) {
        accountBtn.addEventListener("click", function (event) {
            event.stopPropagation();
            const open = account.classList.toggle("is-open");
            accountBtn.setAttribute("aria-expanded", open ? "true" : "false");
        });
        document.addEventListener("click", function (event) {
            if (!account.contains(event.target)) {
                account.classList.remove("is-open");
                accountBtn.setAttribute("aria-expanded", "false");
            }
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                account.classList.remove("is-open");
                accountBtn.setAttribute("aria-expanded", "false");
            }
        });
    }

    document.querySelectorAll('.messages-container .alert').forEach(function (alert) {
        const close = alert.querySelector('.alert-close');
        if (close) close.addEventListener('click', function () { dismissAlert(alert); });
        setTimeout(function () { dismissAlert(alert); }, 5000);
    });

    const forms = document.querySelectorAll('form');
    forms.forEach(function (form) {
        form.addEventListener('submit', function (event) {
            const submitter = event.submitter || form.querySelector('button[type="submit"]');
            const message = (submitter && submitter.getAttribute('data-confirm')) || form.getAttribute('data-confirm');
            if (message && form.dataset.confirmed !== '1') {
                event.preventDefault();
                openDialog(message).then(function (accepted) {
                    if (!accepted) return;
                    form.dataset.confirmed = '1';
                    if (typeof form.requestSubmit === 'function') form.requestSubmit(submitter);
                    else form.submit();
                });
                return;
            }
            if (submitter && !submitter.hasAttribute('data-no-disable')) {
                submitter.disabled = true;
                submitter.textContent = '處理中...';
            }
        });
    });
    
    document.querySelectorAll("[data-password-rules]").forEach(function (input) {
        const list = document.getElementById(input.getAttribute("data-password-rules"));
        if (!list) return;
        const lengthItem = list.querySelector('[data-rule="length"]');
        const numericItem = list.querySelector('[data-rule="numeric"]');
        input.addEventListener("input", function () {
            const value = input.value;
            const started = value.length > 0;
            setPasswordRule(lengthItem, started, value.length >= 8);
            setPasswordRule(numericItem, started, !/^\d+$/.test(value));
        });
    });

    document.querySelectorAll(".js-reveal").forEach(function (button) {
        button.addEventListener("click", function () {
            const field = document.getElementById(button.getAttribute("data-target"));
            if (!field) return;
            const show = field.type === "password";
            field.type = show ? "text" : "password";
            button.textContent = show ? "隱藏" : "顯示";
        });
    });

});

function dismissAlert(alert) {
    if (!alert || !alert.isConnected || alert.classList.contains('is-leaving')) return;
    alert.classList.add('is-leaving');
    const holder = alert.closest('.messages-container');
    alert.style.boxSizing = 'border-box';
    alert.style.height = alert.offsetHeight + 'px';
    alert.style.overflow = 'hidden';
    alert.offsetHeight;
    alert.style.transition = 'height 0.18s ease, margin-bottom 0.18s ease, padding 0.18s ease, opacity 0.18s ease';
    alert.style.height = '0px';
    alert.style.marginBottom = '0px';
    alert.style.paddingTop = '0px';
    alert.style.paddingBottom = '0px';
    alert.style.opacity = '0';
    setTimeout(function () {
        if (alert.parentNode) alert.remove();
        if (holder && holder.isConnected && !holder.querySelector('.alert')) holder.remove();
    }, 190);
}

function openDialog(message) {
    const backdrop = document.getElementById('app-dialog');
    const body = document.getElementById('app-dialog-body');
    const ok = document.getElementById('app-dialog-ok');
    const cancel = document.getElementById('app-dialog-cancel');
    if (!backdrop || !body || !ok || !cancel) return Promise.resolve(window.confirm(message));
    body.textContent = message;
    backdrop.hidden = false;
    cancel.focus();
    return new Promise(function (resolve) {
        function finish(accepted) {
            backdrop.hidden = true;
            ok.removeEventListener('click', onOk);
            cancel.removeEventListener('click', onCancel);
            backdrop.removeEventListener('click', onBackdrop);
            document.removeEventListener('keydown', onKey);
            resolve(accepted);
        }
        function onOk() { finish(true); }
        function onCancel() { finish(false); }
        function onBackdrop(event) { if (event.target === backdrop) finish(false); }
        function onKey(event) { if (event.key === 'Escape') finish(false); }
        ok.addEventListener('click', onOk);
        cancel.addEventListener('click', onCancel);
        backdrop.addEventListener('click', onBackdrop);
        document.addEventListener('keydown', onKey);
    });
}

function setPasswordRule(item, started, ok) {
    if (!item) return;
    item.classList.toggle("is-met", started && ok);
    item.classList.toggle("is-unmet", started && !ok);
}

// 工具函數：格式化時間
function formatTime(weekday, startPeriod, endPeriod) {
    const weekdayNames = ['', '週一', '週二', '週三', '週四', '週五', '週六', '週日'];
    return `${weekdayNames[weekday]} 第${startPeriod}-${endPeriod}節`;
}

// 工具函數：顯示訊息
function showMessage(message, type = 'success') {
    const messagesContainer = document.querySelector('.messages-container .container');
    if (!messagesContainer) return;
    
    const titles = { success: '完成', error: '無法完成', danger: '無法完成', warning: '請注意' };
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.setAttribute('role', 'status');
    const mark = document.createElement('span');
    mark.className = 'alert-mark';
    mark.setAttribute('aria-hidden', 'true');
    const copy = document.createElement('div');
    copy.className = 'alert-copy';
    const title = document.createElement('strong');
    title.textContent = titles[type] || '提示';
    const text = document.createElement('span');
    text.textContent = message;
    copy.append(title, text);
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'alert-close';
    close.setAttribute('aria-label', '關閉');
    close.textContent = '×';
    close.addEventListener('click', function () { dismissAlert(alertDiv); });
    alertDiv.append(mark, copy, close);
    messagesContainer.appendChild(alertDiv);
    setTimeout(function () { dismissAlert(alertDiv); }, 5000);
}
