// 個人課表維護系統 - JavaScript

document.addEventListener('DOMContentLoaded', function() {
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

    // 自動隱藏訊息提示
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.remove();
            }, 500);
        }, 5000);
    });
    
    // 表單驗證
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.hasAttribute('data-no-disable')) {
                submitBtn.disabled = true;
                submitBtn.textContent = '處理中...';
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

    // 確認對話框樣式增強
    const confirmButtons = document.querySelectorAll('[onclick*="confirm"]');
    confirmButtons.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            // 原生 confirm 已在 onclick 中處理
        });
    });
});

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
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.innerHTML = `
        ${message}
        <button class="alert-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    messagesContainer.appendChild(alertDiv);
    
    setTimeout(function() {
        alertDiv.style.transition = 'opacity 0.5s';
        alertDiv.style.opacity = '0';
        setTimeout(function() {
            alertDiv.remove();
        }, 500);
    }, 5000);
}
