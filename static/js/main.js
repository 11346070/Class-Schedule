// 個人課表維護系統 - JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('個人課表維護系統已載入');
    
    // 導覽選單切換（行動版）
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            this.classList.toggle('active');
        });
        
        // 點擊選單項目後關閉選單
        const navLinks = navMenu.querySelectorAll('a');
        navLinks.forEach(function(link) {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    navMenu.classList.remove('active');
                    navToggle.classList.remove('active');
                }
            });
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
    
    // 確認對話框樣式增強
    const confirmButtons = document.querySelectorAll('[onclick*="confirm"]');
    confirmButtons.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            // 原生 confirm 已在 onclick 中處理
        });
    });
});

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
